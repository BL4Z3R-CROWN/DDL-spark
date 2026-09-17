# DDL → PySpark Schema Converter

Convert **SQL DDL** (`CREATE TABLE`) and **`DESCRIBE` output** into `pyspark.sql.types.StructType` schemas.  
Supports live database introspection via `DESCRIBE` / `information_schema` / SQLAlchemy inspector.

Supports **MySQL, PostgreSQL, Oracle, SQL Server, Hive/Spark SQL, SQLite, DuckDB**.

---

## ✨ Features

- **SQL DDL parser** – handles `CREATE TABLE` with:
  - All common types: `INT`, `BIGINT`, `SMALLINT`, `TINYINT(1)` → `BooleanType`, `FLOAT/DOUBLE`, `DECIMAL(p,s)`, `VARCHAR/CHAR/TEXT`, `BLOB/BINARY`, `BOOLEAN`, `DATE/TIME/TIMESTAMP/DATETIME`, `JSON`, `ARRAY<*>, MAP<*,*>`, etc.
  - Constraints: `NOT NULL`, `PRIMARY KEY`, `DEFAULT`, `AUTO_INCREMENT`, `UNSIGNED`
  - Quoted identifiers: `` `backticks` ``, `"double quotes"`, `[brackets]`
  - Multiple tables in one file
  - Fallback: plain column list without `CREATE TABLE`

- **DESCRIBE parser** – paste output from:
  - `DESCRIBE table` (MySQL)
  - `SELECT column_name, data_type, is_nullable FROM information_schema.columns`
  - Pipe `|`, comma `,`, tab, semicolon `;`, markdown tables, or `2+ spaces`
  - Auto-detects `Field | Type | Null` or `column_name | data_type | is_nullable`

- **Live DB mode** – connect and run `DESCRIBE`:
  - SQLAlchemy inspector (`get_columns`) – no data fetched, only schema
  - Credentials never stored
  - SQLite `:memory:` demo creates a sample table automatically

- **Outputs**:
  - Ready-to-run Python: `from pyspark.sql.types import ...` + `StructType([...])`
  - JSON preview + column table
  - One-click **Copy** & **Download .py**

- **Interfaces**:
  - **Web UI** (Flask, single-page, no external CDN)
  - **REST API** (`/api/convert-ddl`, `/api/convert-describe`, `/api/connect`)
  - **CLI** (`cli.py`)
  - **Python library** (`converter.py`)

---

## 🚀 Quick Start

### 1. Install
```bash
pip install -r requirements.txt
# requires: Flask, sqlparse, SQLAlchemy, pyspark (only for type imports at runtime)
# For DB drivers: pymysql, psycopg2-binary, etc. as needed
```

### 2. Run Web App
```bash
python app.py
# → http://localhost:5000
```

### 3. CLI
```bash
# From DDL string
python cli.py --ddl "CREATE TABLE t (id INT PRIMARY KEY, name VARCHAR(100) NOT NULL, price DECIMAL(10,2))"

# From file
python cli.py --ddl-file sample.sql --output schema.py

# From DESCRIBE paste
python cli.py --describe-file describe.txt --table employees --json

# From stdin (pipe)
cat schema.sql | python cli.py --stdin -o out.py

# Live DB (MySQL example)
python cli.py --connect mysql --host localhost --port 3306 --user root --password secret --database mydb --table employees

# Live SQLite demo
python cli.py --connect sqlite --database /tmp/demo.db --table employees

# Library usage
```
```python
from converter import ddl_to_pyspark, describe_to_pyspark

result = ddl_to_pyspark("""
CREATE TABLE sales (
  order_id BIGINT NOT NULL,
  amount DECIMAL(10,2),
  is_returned BOOLEAN,
  created_at TIMESTAMP
)
""")
print(result["tables"][0]["code"])

# DESCRIBE text
res = describe_to_pyspark("Field | Type | Null\nid | int(11) | NO\nname | varchar(255) | YES", table_name="users")
print(res["code"])
```

---

## 🔌 REST API

**`POST /api/convert-ddl`**
```json
{
  "ddl": "CREATE TABLE t (id INT NOT NULL, name VARCHAR(100))",
  "table_name": "optional_override"
}
```
Response:
```json
{
  "count": 1,
  "tables": [
    {
      "table": "t",
      "imports": "from pyspark.sql.types import ...",
      "code": "t_schema = StructType([...])",
      "columns": [{"name":"id","sql_type":"INT","nullable":false,"spark_type":"IntegerType()"}]
    }
  ]
}
```

**`POST /api/convert-describe`**
```json
{
  "describe_text": "Field | Type | Null\nid | int(11) | NO",
  "table_name": "my_table"
}
```

**`POST /api/connect`**
```json
{
  "db_type": "mysql",
  "host": "localhost",
  "port": "3306",
  "user": "root",
  "password": "secret",
  "database": "mydb",
  "table": "employees",
  "schema": "public"
}
```

---

## 🗺️ Type Mapping

| SQL | PySpark |
|-----|---------|
| `INT / INTEGER` | `IntegerType()` |
| `BIGINT / BIGSERIAL` | `LongType()` |
| `SMALLINT` | `ShortType()` |
| `TINYINT / BYTEINT` | `ByteType()` |
| `TINYINT(1)` | `BooleanType()` |
| `FLOAT / REAL` | `FloatType()` |
| `DOUBLE / DOUBLE PRECISION` | `DoubleType()` |
| `DECIMAL(p,s) / NUMERIC / NUMBER` | `DecimalType(p,s)` |
| `CHAR / VARCHAR / TEXT / JSON / UUID / ENUM` | `StringType()` |
| `BINARY / VARBINARY / BLOB / BYTEA` | `BinaryType()` |
| `BOOLEAN / BOOL / BIT(1)` | `BooleanType()` |
| `DATE` | `DateType()` |
| `TIMESTAMP / DATETIME / TIMESTAMPTZ` | `TimestampType()` |
| `TIME` | `StringType()` (no Spark TimeType) |
| `ARRAY<STRING>` | `ArrayType(StringType())` |
| `MAP<STRING,STRING>` | `MapType(StringType(), StringType())` |

---

## 📁 Project Structure

```
.
├── app.py          # Flask web app + API
├── converter.py    # Core parser & generator
├── db_utils.py     # Live DB helpers (SQLAlchemy)
├── cli.py          # CLI
├── requirements.txt
└── README.md
```

---

## 🧪 Examples

**MySQL**
```sql
CREATE TABLE employees (
  id INT PRIMARY KEY AUTO_INCREMENT,
  full_name VARCHAR(255) NOT NULL,
  salary DECIMAL(10,2),
  is_active TINYINT(1) NOT NULL,
  hired_at DATETIME
);
```
→
```python
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DecimalType, BooleanType, TimestampType

employees_schema = StructType([
    StructField("id", IntegerType(), False),
    StructField("full_name", StringType(), False),
    StructField("salary", DecimalType(10,2), True),
    StructField("is_active", BooleanType(), False),
    StructField("hired_at", TimestampType(), True)
])
```

**Hive with complex types**
```sql
CREATE TABLE sales (
  order_id BIGINT,
  items ARRAY<STRING>,
  props MAP<STRING,STRING>
) STORED AS PARQUET;
```

---

## ⚙️ Notes

- **No Spark cluster needed** to generate schemas – we only emit code using `pyspark.sql.types`.
- For live DB, install the driver you need: `pip install pymysql psycopg2-binary`
- SQLite demo uses `/tmp/demo_ddl2spark.db` for `:memory:` requests (creates sample `employees`).

MIT — Lagos, 2026
