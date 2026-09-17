"""
DDL to PySpark Schema Converter - Core Engine
Handles SQL DDL parsing, DESCRIBE output parsing, and PySpark code generation.
"""
import re
from typing import List, Dict, Tuple, Optional

# ---------------- Type Mapping ---------------- #

# Map normalized SQL type -> PySpark Type
# Returns tuple: (spark_type_name, import_name, params)
TYPE_MAPPING = {
    # Integer family
    "INT": ("IntegerType", "IntegerType", None),
    "INTEGER": ("IntegerType", "IntegerType", None),
    "INT4": ("IntegerType", "IntegerType", None),
    "MEDIUMINT": ("IntegerType", "IntegerType", None),
    "SMALLINT": ("ShortType", "ShortType", None),
    "INT2": ("ShortType", "ShortType", None),
    "SMALLSERIAL": ("ShortType", "ShortType", None),
    "TINYINT": ("ByteType", "ByteType", None),
    "INT1": ("ByteType", "ByteType", None),
    "BYTEINT": ("ByteType", "ByteType", None),
    "BIGINT": ("LongType", "LongType", None),
    "INT8": ("LongType", "LongType", None),
    "BIGSERIAL": ("LongType", "LongType", None),
    "SERIAL": ("IntegerType", "IntegerType", None),
    # Float
    "FLOAT": ("FloatType", "FloatType", None),
    "FLOAT4": ("FloatType", "FloatType", None),
    "REAL": ("FloatType", "FloatType", None),
    "DOUBLE": ("DoubleType", "DoubleType", None),
    "DOUBLE PRECISION": ("DoubleType", "DoubleType", None),
    "FLOAT8": ("DoubleType", "DoubleType", None),
    # Decimal
    "DECIMAL": ("DecimalType", "DecimalType", "decimal"),
    "NUMERIC": ("DecimalType", "DecimalType", "decimal"),
    "NUMBER": ("DecimalType", "DecimalType", "decimal"),
    "DEC": ("DecimalType", "DecimalType", "decimal"),
    "MONEY": ("DecimalType", "DecimalType", "decimal"),
    # String
    "CHAR": ("StringType", "StringType", None),
    "NCHAR": ("StringType", "StringType", None),
    "VARCHAR": ("StringType", "StringType", None),
    "VARCHAR2": ("StringType", "StringType", None),
    "NVARCHAR": ("StringType", "StringType", None),
    "NVARCHAR2": ("StringType", "StringType", None),
    "TEXT": ("StringType", "StringType", None),
    "TINYTEXT": ("StringType", "StringType", None),
    "MEDIUMTEXT": ("StringType", "StringType", None),
    "LONGTEXT": ("StringType", "StringType", None),
    "CLOB": ("StringType", "StringType", None),
    "STRING": ("StringType", "StringType", None),
    "JSON": ("StringType", "StringType", None),
    "JSONB": ("StringType", "StringType", None),
    "UUID": ("StringType", "StringType", None),
    "ENUM": ("StringType", "StringType", None),
    "SET": ("StringType", "StringType", None),
    "XML": ("StringType", "StringType", None),
    "INET": ("StringType", "StringType", None),
    # Binary
    "BINARY": ("BinaryType", "BinaryType", None),
    "VARBINARY": ("BinaryType", "BinaryType", None),
    "BLOB": ("BinaryType", "BinaryType", None),
    "TINYBLOB": ("BinaryType", "BinaryType", None),
    "MEDIUMBLOB": ("BinaryType", "BinaryType", None),
    "LONGBLOB": ("BinaryType", "BinaryType", None),
    "BYTEA": ("BinaryType", "BinaryType", None),
    "BYTES": ("BinaryType", "BinaryType", None),
    "IMAGE": ("BinaryType", "BinaryType", None),
    # Boolean
    "BOOLEAN": ("BooleanType", "BooleanType", None),
    "BOOL": ("BooleanType", "BooleanType", None),
    # Date/Time
    "DATE": ("DateType", "DateType", None),
    "TIME": ("StringType", "StringType", None),  # Spark has no TimeType
    "TIMESTAMP": ("TimestampType", "TimestampType", None),
    "TIMESTAMP_NTZ": ("TimestampType", "TimestampType", None),
    "TIMESTAMP_LTZ": ("TimestampType", "TimestampType", None),
    "TIMESTAMP_TZ": ("TimestampType", "TimestampType", None),
    "TIMESTAMPTZ": ("TimestampType", "TimestampType", None),
    "TIMESTAMPTZ_NTZ": ("TimestampType", "TimestampType", None),
    "DATETIME": ("TimestampType", "TimestampType", None),
    "DATETIME2": ("TimestampType", "TimestampType", None),
    "SMALLDATETIME": ("TimestampType", "TimestampType", None),
    # Special handling cases
    "BIT": ("BooleanType", "BooleanType", None),  # BIT(1) -> boolean else binary handled separately
}

# Additional spark imports needed
SPARK_TYPE_IMPORTS = {
    "IntegerType": "IntegerType",
    "LongType": "LongType",
    "ShortType": "ShortType",
    "ByteType": "ByteType",
    "FloatType": "FloatType",
    "DoubleType": "DoubleType",
    "DecimalType": "DecimalType",
    "StringType": "StringType",
    "BinaryType": "BinaryType",
    "BooleanType": "BooleanType",
    "DateType": "DateType",
    "TimestampType": "TimestampType",
    "ArrayType": "ArrayType",
    "MapType": "MapType",
    "StructType": "StructType",
    "StructField": "StructField",
}


def normalize_sql_type(raw_type: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Normalize raw SQL type string.
    Returns (base_type, length_params, extra)
    e.g., "VARCHAR(255)" -> ("VARCHAR", "255", None)
          "DECIMAL(10,2)" -> ("DECIMAL", "10,2", None)
          "DOUBLE PRECISION" -> ("DOUBLE PRECISION", None, None)
    """
    raw = raw_type.strip().upper()
    # Remove UNSIGNED, ZEROFILL etc
    raw = re.sub(r'\bUNSIGNED\b', '', raw)
    raw = re.sub(r'\bZEROFILL\b', '', raw)
    raw = re.sub(r'\s+', ' ', raw).strip()

    # Handle complex types with angle brackets first (Hive)
    if raw.startswith("ARRAY") or raw.startswith("MAP") or raw.startswith("STRUCT"):
        return raw, None, None

    # Try to match base + params where params are (...) 
    # Use greedy but stop at first '('
    m = re.match(r'^([A-Z ]+?)\s*\(\s*([^)]+)\s*\)\s*(.*)$', raw)
    if m:
        base = m.group(1).strip()
        params = m.group(2).strip()
        extra = m.group(3).strip() if m.group(3) else None
        # Clean base: should be a known type, but might have extra words before paren? Keep as is
        return base, params, extra

    # No parentheses: try to find longest known type prefix
    # Sorted longest first to prefer DOUBLE PRECISION over DOUBLE
    known_bases = sorted(TYPE_MAPPING.keys(), key=len, reverse=True)
    for kb in known_bases:
        if raw == kb or raw.startswith(kb + " ") or raw.startswith(kb + "("):
            remainder = raw[len(kb):].strip()
            # remainder is extra (e.g., "WITH TIME ZONE" or "VARYING")
            # But for types like VARCHAR without params, we already handled paren case, so remainder is extra
            return kb, None, remainder if remainder else None

    # Heuristic: handle CHARACTER VARYING, etc.
    if raw.startswith("CHARACTER VARYING") or raw.startswith("CHAR VARYING"):
        # Extract possible length
        m2 = re.match(r'^(?:CHARACTER\s+VARYING|CHAR\s+VARYING)\s*(?:\(([^)]+)\))?\s*(.*)$', raw)
        if m2:
            return "VARCHAR", m2.group(1), m2.group(2) if m2.group(2) else None
        return "VARCHAR", None, None
    if raw.startswith("CHARACTER") or raw.startswith("CHAR"):
        m2 = re.match(r'^(?:CHARACTER|CHAR)\s*(?:\(([^)]+)\))?\s*(.*)$', raw)
        if m2:
            return "CHAR", m2.group(1), m2.group(2) if m2.group(2) else None

    # Fallback: first word is base
    parts = raw.split()
    if parts:
        # If first word contains '(' already? shouldn't happen because we handled paren case
        return parts[0], None, " ".join(parts[1:]) if len(parts) > 1 else None
    return raw, None, None


def map_sql_to_spark(sql_type_raw: str) -> Tuple[str, str, Optional[str]]:
    """
    Map a SQL type string to PySpark type.
    Returns (spark_type_expr, import_name, params_info)
    e.g., "VARCHAR(255)" -> ("StringType()", "StringType", None)
          "DECIMAL(10,2)" -> ("DecimalType(10,2)", "DecimalType", "10,2")
    """
    base, params, extra = normalize_sql_type(sql_type_raw)
    
    # Handle BIT special case
    if base == "BIT":
        if params and params.strip() == "1":
            return "BooleanType()", "BooleanType", None
        else:
            return "BinaryType()", "BinaryType", None

    # Handle TINYINT(1) -> Boolean (MySQL convention)
    if base == "TINYINT" and params and params.strip() == "1":
        return "BooleanType()", "BooleanType", None

    # Handle ARRAY, MAP, STRUCT complex types (Hive/Spark SQL)
    if base.startswith("ARRAY"):
        # e.g., ARRAY<STRING> or ARRAY
        inner = None
        m = re.search(r'ARRAY\s*<\s*(.+)\s*>', sql_type_raw, re.IGNORECASE)
        if m:
            inner_raw = m.group(1).strip()
            inner_expr, inner_import, _ = map_sql_to_spark(inner_raw)
            # inner_expr is like StringType() -> need to pass without ()
            # We'll create ArrayType(StringType())
            return f"ArrayType({inner_expr})", "ArrayType", None
        return "ArrayType(StringType())", "ArrayType", None

    if base.startswith("MAP"):
        m = re.search(r'MAP\s*<\s*(.+?)\s*,\s*(.+)\s*>', sql_type_raw, re.IGNORECASE)
        if m:
            k_raw, v_raw = m.group(1).strip(), m.group(2).strip()
            k_expr, _, _ = map_sql_to_spark(k_raw)
            v_expr, _, _ = map_sql_to_spark(v_raw)
            return f"MapType({k_expr}, {v_expr})", "MapType", None
        return "MapType(StringType(), StringType())", "MapType", None

    # Handle interval, etc fallback
    if base not in TYPE_MAPPING:
        # Try to find partial match (e.g., "CHARACTER VARYING" -> VARCHAR)
        if "VARCHAR" in base or "CHAR" in base:
            return "StringType()", "StringType", None
        if "TIMESTAMP" in base:
            return "TimestampType()", "TimestampType", None
        if "INT" in base:
            return "IntegerType()", "IntegerType", None
        # Default to StringType for unknown
        return "StringType()", "StringType", None

    spark_name, import_name, kind = TYPE_MAPPING[base]

    if kind == "decimal":
        if params:
            # params like "10,2" or "10"
            parts = [p.strip() for p in params.split(",")]
            if len(parts) == 2:
                return f"DecimalType({parts[0]},{parts[1]})", "DecimalType", params
            elif len(parts) == 1:
                return f"DecimalType({parts[0]},0)", "DecimalType", params
        return "DecimalType(10,0)", "DecimalType", None

    return f"{spark_name}()", import_name, None


def split_columns(block: str) -> List[str]:
    """
    Split column definition block by commas not inside parentheses/brackets.
    """
    cols = []
    current = []
    depth_paren = 0
    depth_angle = 0
    depth_bracket = 0
    in_single = False
    in_double = False
    in_backtick = False
    for i, ch in enumerate(block):
        if ch == "'" and not in_double and not in_backtick:
            # handle escaped ''
            if in_single and i+1 < len(block) and block[i+1] == "'":
                current.append(ch)
                continue
            in_single = not in_single
        elif ch == '"' and not in_single and not in_backtick:
            in_double = not in_double
        elif ch == "`" and not in_single and not in_double:
            in_backtick = not in_backtick

        if not in_single and not in_double and not in_backtick:
            if ch == '(':
                depth_paren += 1
            elif ch == ')':
                depth_paren -= 1
            elif ch == '<':
                depth_angle += 1
            elif ch == '>':
                depth_angle -= 1
            elif ch == '[':
                depth_bracket += 1
            elif ch == ']':
                depth_bracket -= 1
            elif ch == ',' and depth_paren == 0 and depth_angle == 0 and depth_bracket == 0:
                cols.append(''.join(current).strip())
                current = []
                continue
        current.append(ch)
    if current:
        cols.append(''.join(current).strip())
    return [c for c in cols if c]


def clean_ddl(ddl: str) -> str:
    """Remove comments and normalize."""
    # Remove /* */ block comments
    ddl = re.sub(r'/\*.*?\*/', '', ddl, flags=re.DOTALL)
    # Remove -- line comments
    ddl = re.sub(r'--.*?(\n|$)', r'\n', ddl)
    # Remove # comments (MySQL)
    ddl = re.sub(r'#.*?(\n|$)', r'\n', ddl)
    return ddl.strip()


def parse_ddl(ddl: str) -> List[Dict]:
    """
    Parse CREATE TABLE DDL and return list of tables with columns.
    Each table: {"table": str, "columns": [{"name": str, "sql_type": str, "nullable": bool, "raw": str}]}
    """
    ddl_clean = clean_ddl(ddl)
    tables = []

    # Find all CREATE TABLE blocks
    # This regex finds CREATE TABLE ... ( ... ) optionally with ; 
    # We need to handle nested parens correctly, so we scan manually
    pattern = re.compile(r'CREATE\s+(?:OR\s+REPLACE\s+)?(?:TEMPORARY\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<name>(?:`[^`]+`|\[[^\]]+\]|"[^"]+"|\w+(?:\.\w+)*))\s*\(', re.IGNORECASE)

    pos = 0
    while True:
        m = pattern.search(ddl_clean, pos)
        if not m:
            break
        table_name_raw = m.group('name')
        # Clean table name: remove quotes, brackets, backticks, handle schema.table
        table_name = re.sub(r'[`"\[\]]', '', table_name_raw).split('.')[-1].strip()
        start = m.end() - 1  # position of '('
        # Find matching closing )
        depth = 0
        end = -1
        in_single = False
        in_double = False
        in_backtick = False
        for i in range(start, len(ddl_clean)):
            ch = ddl_clean[i]
            if ch == "'" and not in_double and not in_backtick:
                in_single = not in_single
            elif ch == '"' and not in_single and not in_backtick:
                in_double = not in_double
            elif ch == "`" and not in_single and not in_double:
                in_backtick = not in_backtick
            if not in_single and not in_double and not in_backtick:
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0:
                        end = i
                        break
        if end == -1:
            break
        block = ddl_clean[start+1:end]
        # Now split block into column/constraint definitions
        defs = split_columns(block)
        columns = []
        for d in defs:
            d_stripped = d.strip()
            if not d_stripped:
                continue
            upper = d_stripped.upper()
            # Skip constraints
            if upper.startswith("PRIMARY KEY") or upper.startswith("FOREIGN KEY") or upper.startswith("UNIQUE") or upper.startswith("CHECK") or upper.startswith("CONSTRAINT") or upper.startswith("KEY ") or upper.startswith("INDEX") or upper.startswith("EXCLUDE") or upper.startswith("PARTITION") or upper.startswith("CLUSTERED") or upper.startswith("NONCLUSTERED"):
                continue
            # Skip table options that somehow got inside (should not)
            # Parse column: name type ...
            # Column name may be quoted
            col_match = re.match(r'^\s*(?:`([^`]+)`|\[([^\]]+)\]|"([^"]+)"|(\w+))\s+(.*)$', d_stripped, re.DOTALL)
            if not col_match:
                continue
            col_name = col_match.group(1) or col_match.group(2) or col_match.group(3) or col_match.group(4)
            remainder = col_match.group(5).strip()
            # Remainder starts with type; we need to separate type from constraints
            # Known constraint keywords
            constraint_keywords = [
                "NOT NULL", "NULL", "PRIMARY KEY", "UNIQUE", "DEFAULT", "CHECK", "REFERENCES", "COLLATE",
                "AUTO_INCREMENT", "AUTOINCREMENT", "IDENTITY", "GENERATED", "COMMENT", "VISIBLE", "INVISIBLE",
                "ON UPDATE", "CONSTRAINT", "KEY", "ENABLE", "DISABLE", "WITH TIME ZONE", "WITHOUT TIME ZONE"
            ]
            # Extract sql_type: take tokens until we hit a constraint keyword
            # Approach: walk through remainder and detect keywords
            # We'll use regex to find where constraints start
            # Build pattern for constraint start
            # Simpler: split remainder by spaces but respect parentheses/brackets
            # Find earliest occurrence of constraint keyword
            # Use case-insensitive search
            type_end = len(remainder)
            earliest = len(remainder)
            # Create regex for each keyword as word boundary
            for kw in constraint_keywords:
                # For multi-word like "NOT NULL", search exactly
                # Use regex with IGNORECASE
                pat = r'\b' + re.escape(kw) + r'\b'
                # But for NOT NULL we must ensure we match correctly
                # Search
                mm = re.search(pat, remainder, re.IGNORECASE)
                if mm:
                    # Need to ensure we are not inside parentheses/angle brackets
                    # Quick check: count parens before match
                    prefix = remainder[:mm.start()]
                    # If prefix has unclosed paren, then keyword inside type? Not for these keywords except maybe?
                    # For our types, params are only parentheses immediately after type, so after that any keyword is outside
                    # So we can just take earliest
                    # Verify prefix paren depth zero for safety? Compute depth
                    depth_p = prefix.count('(') - prefix.count(')')
                    depth_a = prefix.count('<') - prefix.count('>')
                    if depth_p == 0 and depth_a == 0:
                        if mm.start() < earliest:
                            earliest = mm.start()
            if earliest != len(remainder):
                sql_type_raw = remainder[:earliest].strip().rstrip(',').strip()
                constraint_part = remainder[earliest:].strip()
            else:
                sql_type_raw = remainder.strip().rstrip(',').strip()
                constraint_part = ""

            # Determine nullable: if "NOT NULL" in constraint_part (case insensitive) then False else True
            # Also if PRIMARY KEY implies NOT NULL
            nullable = True
            if re.search(r'\bNOT\s+NULL\b', constraint_part, re.IGNORECASE) or re.search(r'\bPRIMARY\s+KEY\b', constraint_part, re.IGNORECASE):
                nullable = False
            # If explicit NULL without NOT, remains True
            # Handle edge: some DDLs have explicit "NULL" as nullable
            # Default is True unless NOT NULL

            # Clean sql_type_raw: remove trailing constraint-like words that might have been missed due to complex constraints
            # e.g., sql_type_raw might still contain "UNSIGNED" etc which we handle in mapping, keep it
            # But ensure it doesn't contain stray commas

            columns.append({
                "name": col_name,
                "sql_type": sql_type_raw,
                "nullable": nullable,
                "raw": d_stripped
            })

        if columns:
            tables.append({"table": table_name, "columns": columns})
        pos = end + 1

    # If no CREATE TABLE found, try to parse as simple column list (e.g., just columns without CREATE)
    if not tables and ddl_clean.strip():
        # Check if input looks like column definitions (contains type keywords)
        # Try to parse as single table
        maybe_cols = split_columns(ddl_clean)
        columns = []
        for d in maybe_cols:
            d = d.strip().rstrip(',').rstrip(';')
            if not d:
                continue
            upper = d.upper()
            if upper.startswith("PRIMARY") or upper.startswith("CONSTRAINT"):
                continue
            col_match = re.match(r'^\s*(?:`([^`]+)`|\[([^\]]+)\]|"([^"]+)"|(\w+))\s+(.*)$', d, re.DOTALL)
            if not col_match:
                continue
            col_name = col_match.group(1) or col_match.group(2) or col_match.group(3) or col_match.group(4)
            remainder = col_match.group(5).strip()
            # Simple heuristic: first token(s) are type
            # For now take remainder up to constraint
            constraint_keywords = ["NOT NULL", "NULL", "PRIMARY KEY", "DEFAULT"]
            earliest = len(remainder)
            for kw in constraint_keywords:
                mm = re.search(r'\b' + re.escape(kw) + r'\b', remainder, re.IGNORECASE)
                if mm and mm.start() < earliest:
                    # check paren depth
                    prefix = remainder[:mm.start()]
                    if prefix.count('(') == prefix.count(')'):
                        earliest = mm.start()
            if earliest != len(remainder):
                sql_type_raw = remainder[:earliest].strip()
                constraint_part = remainder[earliest:]
            else:
                sql_type_raw = remainder.strip()
                constraint_part = ""
            nullable = not bool(re.search(r'\bNOT\s+NULL\b', constraint_part, re.IGNORECASE))
            columns.append({"name": col_name, "sql_type": sql_type_raw, "nullable": nullable, "raw": d})
        if columns:
            tables.append({"table": "my_table", "columns": columns})

    return tables


def parse_describe_output(text: str) -> List[Dict]:
    """
    Parse DESCRIBE / information_schema pasted output.
    Supports:
    - MySQL DESCRIBE pipe/table format: Field | Type | Null | Key | Default | Extra
    - Markdown table
    - CSV / TSV
    - Postgres: column_name | data_type | is_nullable
    - Generic: tries to detect columns by header names
    Returns list of column dicts
    """
    text = text.strip()
    if not text:
        return []

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # Remove separator lines like +---+ or |---|
    filtered = []
    for l in lines:
        if re.match(r'^[\+\-\|=\s]+$', l) and not re.search(r'[a-zA-Z0-9]', l):
            continue
        if re.match(r'^[\-\s\|]+$', l) and '|' in l and not re.search(r'[a-zA-Z]', l):
            # might be markdown separator |---|---| 
            if re.match(r'^\|?[\s\-\|:]+\|?$', l):
                continue
        filtered.append(l)
    lines = filtered
    if not lines:
        return []

    # Detect delimiter and parse header
    header_line = lines[0]
    # Try to detect header based on delimiters
    # Possible delimiters: |, ,, tab, ;, multiple spaces
    # Normalize pipes: strip leading/trailing |
    def split_row(row: str) -> List[str]:
        row = row.strip()
        # If contains |, split by |
        if '|' in row:
            # Remove leading/trailing |
            row = row.strip('|')
            parts = [p.strip() for p in row.split('|')]
            return parts
        elif '\t' in row:
            return [p.strip() for p in row.split('\t')]
        elif ',' in row:
            # Simple CSV split respecting quotes
            import csv
            import io
            reader = csv.reader(io.StringIO(row))
            return [p.strip() for p in next(reader)]
        elif ';' in row:
            return [p.strip() for p in row.split(';')]
        else:
            # Split by 2+ spaces
            parts = re.split(r'\s{2,}', row)
            if len(parts) >= 2:
                return [p.strip() for p in parts]
            # Fallback single space
            return row.split()

    header_parts = split_row(header_line)
    header_lower = [h.lower().strip() for h in header_parts]

    # Try to identify column name and type and nullable indices
    # Common header names
    name_keys = ["field", "column_name", "column name", "name", "col", "attribute", "column"]
    type_keys = ["type", "data_type", "data type", "column_type", "column type", "sql_type", "sql type", "datatype", "udt_name"]
    null_keys = ["null", "is_nullable", "is nullable", "nullable", "is null", "null?"]
    
    name_idx = type_idx = null_idx = None
    for i, h in enumerate(header_lower):
        if any(k == h or k in h for k in name_keys) and name_idx is None:
            # Prefer exact match for field/column_name
            if h in name_keys or "field" in h or "column" in h or h == "name":
                name_idx = i
        if any(k == h or k in h for k in type_keys) and type_idx is None:
            type_idx = i
        if any(k == h or k in h for k in null_keys) and null_idx is None:
            null_idx = i

    # Heuristics if not found
    if name_idx is None:
        name_idx = 0
    if type_idx is None:
        # If header has 2 cols, second is type; if 3+ second or third
        if len(header_parts) >= 2:
            type_idx = 1
        else:
            type_idx = 0

    # If header is actually data (no known header words), treat first row as data
    known_headers = set(name_keys + type_keys + null_keys + ["key", "default", "extra", "udt_name", "character_maximum_length"])
    has_known_header = any(h in known_headers or any(k in h for k in known_headers) for h in header_lower)
    data_start = 1 if has_known_header else 0

    columns = []
    for line in lines[data_start:]:
        parts = split_row(line)
        if len(parts) < 1:
            continue
        # Pad parts if shorter than indices
        if name_idx >= len(parts) or type_idx >= len(parts):
            # Try fallback: if only 2 parts and we expected 3, maybe type contains spaces?
            # Just skip if malformed
            if len(parts) == 1:
                # Single line like "id INT NOT NULL"
                # Try to parse as DDL-like
                m = re.match(r'^\s*(\w+)\s+(.+?)(?:\s+(NOT\s+NULL|NULL))?\s*$', parts[0], re.IGNORECASE)
                if m:
                    col_name = m.group(1)
                    sql_type = m.group(2).strip()
                    nullable = True
                    if m.group(3) and re.search(r'NOT\s+NULL', m.group(3), re.IGNORECASE):
                        nullable = False
                    columns.append({"name": col_name, "sql_type": sql_type, "nullable": nullable, "raw": line})
                continue
            else:
                continue

        col_name = parts[name_idx].strip().strip('`"[]')
        sql_type = parts[type_idx].strip()
        nullable = True
        if null_idx is not None and null_idx < len(parts):
            null_val = parts[null_idx].strip().upper()
            if null_val in ("NO", "N", "FALSE", "NOT NULL", "0"):
                nullable = False
            elif null_val in ("YES", "Y", "TRUE", "NULL", "1", ""):
                # YES means nullable, but if header is null and value YES -> nullable True
                # Need distinguish: MySQL Null column: YES/NO
                if null_val == "NO":
                    nullable = False
                elif null_val == "YES":
                    nullable = True
                elif null_val == "NOT NULL":
                    nullable = False
            else:
                # Try to parse YES/NO
                if "NO" in null_val:
                    nullable = False
        else:
            # Check if sql_type contains NOT NULL
            if re.search(r'NOT\s+NULL', sql_type, re.IGNORECASE):
                nullable = False
                sql_type = re.sub(r'\bNOT\s+NULL\b', '', sql_type, flags=re.IGNORECASE).strip()
            elif re.search(r'\bNULL\b', line, re.IGNORECASE):
                # Hard to know
                pass

        # Clean sql_type: remove extra info after type like "unsigned" kept, but remove after constraints
        # sql_type might already be clean
        if sql_type:
            columns.append({"name": col_name, "sql_type": sql_type, "nullable": nullable, "raw": line})

    return columns


def generate_pyspark_code(columns: List[Dict], table_name: str = "my_table", include_imports: bool = True) -> Tuple[str, str, List[str]]:
    """
    Generate PySpark schema code from columns.
    Returns (code_str, imports_str, required_imports)
    """
    # Determine required imports
    required = set(["StructType", "StructField"])
    field_lines = []
    for col in columns:
        spark_expr, import_name, _ = map_sql_to_spark(col["sql_type"])
        required.add(import_name)
        if import_name == "ArrayType" and "StringType" in spark_expr:
            required.add("StringType")
        if import_name == "MapType":
            # Extract inner types? Just add StringType as fallback
            if "StringType" in spark_expr:
                required.add("StringType")
            if "IntegerType" in spark_expr:
                required.add("IntegerType")

    # Sort imports for consistency: put StructType, StructField first
    spark_types_order = ["StructType", "StructField", "StringType", "IntegerType", "LongType", "ShortType", "ByteType", "FloatType", "DoubleType", "DecimalType", "BooleanType", "BinaryType", "DateType", "TimestampType", "ArrayType", "MapType"]
    ordered_imports = [t for t in spark_types_order if t in required]
    # Add any remaining
    for t in required:
        if t not in ordered_imports:
            ordered_imports.append(t)

    imports_str = f"from pyspark.sql.types import {', '.join(ordered_imports)}"

    # Generate StructFields
    fields = []
    for col in columns:
        spark_expr, _, _ = map_sql_to_spark(col["sql_type"])
        nullable_str = "True" if col["nullable"] else "False"
        # Escape quotes in name
        name_escaped = col["name"].replace('"', '\\"')
        fields.append(f'    StructField("{name_escaped}", {spark_expr}, {nullable_str})')

    fields_block = ",\n".join(fields)
    schema_code = f"{table_name}_schema = StructType([\n{fields_block}\n])" if table_name else f"schema = StructType([\n{fields_block}\n])"

    # Also generate alternative: DDL string for spark
    # e.g., "id INT, name STRING"
    # Not needed now

    full_code = f"{imports_str}\n\n{schema_code}\n" if include_imports else f"{schema_code}\n"

    # Generate also createDataFrame example and DDL helper
    example = f"""
# Usage example:
# df = spark.createDataFrame(data, schema={table_name}_schema)
# Or for empty DF:
# df = spark.createDataFrame([], schema={table_name}_schema)
# df.printSchema()
"""

    # For backwards compatibility, return full_code
    return full_code, imports_str, ordered_imports


def generate_json_schema(columns: List[Dict]) -> List[Dict]:
    """
    Generate a JSON representation of schema, useful for API.
    """
    out = []
    for col in columns:
        spark_expr, import_name, _ = map_sql_to_spark(col["sql_type"])
        out.append({
            "name": col["name"],
            "sql_type": col["sql_type"],
            "nullable": col["nullable"],
            "spark_type": spark_expr,
            "spark_type_name": import_name
        })
    return out


def ddl_to_pyspark(ddl: str, table_name_override: Optional[str] = None) -> Dict:
    """
    High-level: DDL string -> dict with results per table
    """
    tables = parse_ddl(ddl)
    if not tables:
        raise ValueError("No tables found in DDL. Check syntax or try DESCRIBE mode if you pasted DESCRIBE output.")
    results = []
    for t in tables:
        tname = table_name_override or t["table"]
        code, imports_str, imports = generate_pyspark_code(t["columns"], table_name=tname)
        json_schema = generate_json_schema(t["columns"])
        results.append({
            "table": tname,
            "columns": json_schema,
            "code": code,
            "imports": imports_str,
        })
    return {"tables": results, "count": len(results)}


def describe_to_pyspark(describe_text: str, table_name: str = "my_table") -> Dict:
    cols = parse_describe_output(describe_text)
    if not cols:
        raise ValueError("Could not parse DESCRIBE output. Ensure it contains header row like 'Field | Type | Null' or 'column_name | data_type | is_nullable'. Try pasting as CSV or pipe-separated.")
    code, imports_str, imports = generate_pyspark_code(cols, table_name=table_name)
    json_schema = generate_json_schema(cols)
    return {
        "table": table_name,
        "columns": json_schema,
        "code": code,
        "imports": imports_str,
    }


# ---------------- Helpers for DB connector ---------------- #
def columns_from_inspector(columns_info: List[Dict]) -> List[Dict]:
    """
    Convert SQLAlchemy inspector.get_columns() output to our column format.
    Each col_info: {"name": str, "type": TypeEngine, "nullable": bool, ...}
    """
    cols = []
    for c in columns_info:
        raw_type = str(c["type"])
        # c["type"] may be like VARCHAR(length=255) etc; str is good
        # For types with params, use compile?
        cols.append({
            "name": c["name"],
            "sql_type": raw_type,
            "nullable": c.get("nullable", True),
            "raw": f"{c['name']} {raw_type}"
        })
    return cols
