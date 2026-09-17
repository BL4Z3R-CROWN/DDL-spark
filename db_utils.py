"""
Database utilities: connect to DB, run DESCRIBE / inspector, return schema.
Uses SQLAlchemy for generic support.
"""
from typing import Dict, List, Optional
import re
from converter import columns_from_inspector, generate_pyspark_code, generate_json_schema

try:
    from sqlalchemy import create_engine, inspect, text as sql_text
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False


SUPPORTED_DB_TYPES = {
    "mysql": {"default_port": 3306, "driver": "pymysql"},
    "postgresql": {"default_port": 5432, "driver": "psycopg2"},
    "postgres": {"default_port": 5432, "driver": "psycopg2"},
    "sqlite": {"default_port": None, "driver": None},
    "mssql": {"default_port": 1433, "driver": "pymssql"},
    "sqlserver": {"default_port": 1433, "driver": "pymssql"},
    "oracle": {"default_port": 1521, "driver": "cx_oracle"},
    "duckdb": {"default_port": None, "driver": "duckdb_engine"},
}


def build_connection_string(db_type: str, host: str, port: Optional[str], user: str, password: str, database: str, extra: str = "") -> str:
    db_type = db_type.lower().strip()
    if db_type == "sqlite":
        # database is file path or :memory:
        if not database or database == ":memory:":
            return "sqlite:///:memory:"
        return f"sqlite:///{database}"

    if db_type in ("mysql",):
        port = port or "3306"
        # Use pymysql driver
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}{extra}"

    if db_type in ("postgresql", "postgres"):
        port = port or "5432"
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}{extra}"

    if db_type in ("mssql", "sqlserver"):
        port = port or "1433"
        # Use pymssql or pyodbc fallback
        return f"mssql+pymssql://{user}:{password}@{host}:{port}/{database}{extra}"

    if db_type == "oracle":
        port = port or "1521"
        return f"oracle+cx_oracle://{user}:{password}@{host}:{port}/?service_name={database}{extra}"

    if db_type == "duckdb":
        return f"duckdb:///{database}" if database else "duckdb:///:memory:"

    # Generic fallback
    port_part = f":{port}" if port else ""
    return f"{db_type}://{user}:{password}@{host}{port_part}/{database}{extra}"


def fetch_schema_via_inspector(conn_str: str, table: str, schema: Optional[str] = None) -> Dict:
    """
    Connect via SQLAlchemy, inspect table, return columns + pyspark code.
    """
    if not SQLALCHEMY_AVAILABLE:
        raise RuntimeError("SQLAlchemy is not installed. Please install with pip install SQLAlchemy")

    engine = create_engine(conn_str)
    inspector = inspect(engine)
    # Handle schema-qualified table name
    if "." in table and schema is None:
        parts = table.split(".")
        if len(parts) == 2:
            schema, table = parts[0], parts[1]

    # Try to list tables to give better error
    try:
        columns_info = inspector.get_columns(table, schema=schema)
    except Exception as e:
        # Try without schema
        try:
            columns_info = inspector.get_columns(table)
        except Exception as e2:
            raise RuntimeError(f"Failed to inspect table '{table}': {e} / {e2}")

    if not columns_info:
        raise RuntimeError(f"No columns found for table '{table}'. Check table name and schema.")

    cols = columns_from_inspector(columns_info)
    # Determine table name for code gen
    table_clean = re.sub(r'[`"\[\]]', '', table).split('.')[-1]
    code, imports_str, imports = generate_pyspark_code(cols, table_name=table_clean)
    json_schema = generate_json_schema(cols)
    return {
        "table": table_clean,
        "columns": json_schema,
        "code": code,
        "imports": imports_str,
        "engine_url": conn_str.split("@")[-1]  # hide credentials
    }


def fetch_schema_via_describe(conn_str: str, table: str) -> Dict:
    """
    Alternative: run DESCRIBE / information_schema query directly.
    Useful for MySQL.
    """
    if not SQLALCHEMY_AVAILABLE:
        raise RuntimeError("SQLAlchemy not available")

    engine = create_engine(conn_str)
    table_clean = re.sub(r'[`"\[\]]', '', table).split('.')[-1]
    # Try DESCRIBE for MySQL, \d for Postgres not needed, use information_schema
    query_candidates = [
        f"DESCRIBE {table}",
        f"DESCRIBE TABLE {table}",
        f"SELECT column_name, data_type, is_nullable, numeric_precision, numeric_scale, character_maximum_length FROM information_schema.columns WHERE table_name = '{table_clean}' ORDER BY ordinal_position",
    ]
    last_err = None
    with engine.connect() as conn:
        for q in query_candidates:
            try:
                result = conn.execute(sql_text(q))
                rows = result.fetchall()
                cols = []
                # Try to infer structure
                keys = list(result.keys())
                # Map keys lower
                keys_lower = [k.lower() for k in keys]
                # Determine indices
                # Case 1: DESCRIBE (Field, Type, Null ...)
                if "field" in keys_lower:
                    fi = keys_lower.index("field")
                    ti = keys_lower.index("type")
                    ni = keys_lower.index("null") if "null" in keys_lower else None
                    for r in rows:
                        nullable = True
                        if ni is not None:
                            nullable = str(r[ni]).upper() == "YES"
                        cols.append({"name": str(r[fi]), "sql_type": str(r[ti]), "nullable": nullable, "raw": str(r)})
                # Case 2: information_schema
                elif "column_name" in keys_lower:
                    ci = keys_lower.index("column_name")
                    ti = keys_lower.index("data_type")
                    ni = keys_lower.index("is_nullable") if "is_nullable" in keys_lower else None
                    for r in rows:
                        nullable = True
                        if ni is not None:
                            nullable = str(r[ni]).upper() == "YES"
                        # Try to enrich type with precision/scale/length
                        sql_type = str(r[ti])
                        # Check for character_maximum_length, numeric_precision, etc
                        try:
                            if "character_maximum_length" in keys_lower:
                                idx = keys_lower.index("character_maximum_length")
                                val = r[idx]
                                if val and sql_type.upper() in ("VARCHAR", "CHARACTER VARYING", "CHAR"):
                                    sql_type = f"{sql_type}({val})"
                            if "numeric_precision" in keys_lower and "numeric_scale" in keys_lower:
                                pi = keys_lower.index("numeric_precision")
                                si = keys_lower.index("numeric_scale")
                                if r[pi] and sql_type.upper() in ("NUMERIC", "DECIMAL", "NUMBER"):
                                    sql_type = f"{sql_type}({r[pi]},{r[si] or 0})"
                        except:
                            pass
                        cols.append({"name": str(r[ci]), "sql_type": sql_type, "nullable": nullable, "raw": str(r)})
                else:
                    # Generic fallback: assume first col name, second type
                    for r in rows:
                        cols.append({"name": str(r[0]), "sql_type": str(r[1]), "nullable": True, "raw": str(r)})
                if cols:
                    code, imports_str, _ = generate_pyspark_code(cols, table_name=table_clean)
                    json_schema = generate_json_schema(cols)
                    return {"table": table_clean, "columns": json_schema, "code": code, "imports": imports_str}
            except Exception as e:
                last_err = e
                continue
    raise RuntimeError(f"All DESCRIBE queries failed. Last error: {last_err}")


def test_connection(conn_str: str) -> bool:
    if not SQLALCHEMY_AVAILABLE:
        return False
    try:
        engine = create_engine(conn_str)
        with engine.connect() as conn:
            conn.execute(sql_text("SELECT 1"))
        return True
    except:
        return False
