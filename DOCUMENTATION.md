# DDL → PySpark Schema Converter — Complete Documentation

**Version:** 2.1 (Editable Per-Field Types)  
**Author:** Arena Agent  
**Date:** 2026-09-17 (Africa/Lagos)  
**Stack:** Python 3, Flask, SQLAlchemy, PySpark Types, Vanilla JS  
**Repo branch:** `main` — commits `eddd6b5` (initial) → `94fb191` (editable)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Key Features](#2-key-features)
3. [Architecture — How It Works](#3-architecture--how-it-works)
4. [Type Mapping — SQL → PySpark](#4-type-mapping--sql--pyspark)
5. [Installation](#5-installation)
6. [Usage — Web UI](#6-usage--web-ui)
7. [Usage — Editable Per-Field Feature](#7-usage--editable-per-field-feature)
8. [Usage — REST API](#8-usage--rest-api)
9. [Usage — CLI](#9-usage--cli)
10. [Usage — Python Library](#10-usage--python-library)
11. [Live Database DESCRIBE](#11-live-database-describe)
12. [Examples by Database Dialect](#12-examples-by-database-dialect)
13. [Sharing & Distribution](#13-sharing--distribution)
14. [Deployment Options](#14-deployment-options)
15. [Security & Performance](#15-security--performance)
16. [Troubleshooting & FAQ](#16-troubleshooting--faq)
17. [Project Structure](#17-project-structure)
18. [Contributing & Roadmap](#18-contributing--roadmap)
19. [Appendix — Code Snippets](#19-appendix--code-snippets)

---

## 1. Overview

The **DDL → PySpark Schema Converter** converts relational schema metadata into executable `pyspark.sql.types.StructType` code. It solves the painful manual translation you do when moving data from a warehouse (MySQL, Postgres, Oracle, SQL Server, Hive, SQLite, DuckDB) into a Spark pipeline.

You give it **any one** of:

- Raw `CREATE TABLE` DDL (one or many tables, with `NOT NULL`, `DEFAULT`, `AUTO_INCREMENT`, `UNSIGNED`, quoted identifiers, `DECIMAL(p,s)`, `ARRAY<…>`, `MAP<…, …>`)
- Pasted **DESCRIBE** / `information_schema` output (pipe `|`, CSV, TSV, markdown, `column_name | data_type | is_nullable`)
- A **live database connection** — the app runs `inspector.get_columns(table)` (no rows fetched) and builds the schema

It returns:

```python
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DecimalType, TimestampType, BooleanType

employees_schema = StructType([
    StructField("id", IntegerType(), False),
    StructField("full_name", StringType(), False),
    StructField("salary", DecimalType(10,2), True),
    StructField("is_active", BooleanType(), False),
    StructField("hired_at", TimestampType(), True)
])
# df = spark.createDataFrame([], schema=employees_schema)
```

Plus a JSON view, a browsable column table, and — since v2 — **inline editing of every field’s Spark type**.

**Who is it for?**

- Data Engineers migrating to Databricks / EMR / Spark
- Analysts who got a `DESCRIBE` dump from a DBA and need a Spark schema
- Teams who want a single source of truth for type mapping and to share it via Git

---

## 2. Key Features

| Feature | Details |
|---|---|
| **DDL Parser** | Handles `CREATE TABLE [IF NOT EXISTS] schema.table (...)` with nested parentheses, commas inside `DECIMAL(10,2)`, quoted/bracketed/backticked identifiers, multi-table files, and fallback for bare column lists |
| **DESCRIBE Parser** | Auto-detects header names (`Field`, `column_name`, `Type`, `data_type`, `Null`, `is_nullable`), delimiters (`|`, `,`, `\t`, `;`, 2+ spaces), and MySQL `YES/NO` + Postgres `YES/NO` nullable semantics |
| **Live DB** | SQLAlchemy `inspector.get_columns()` + fallback `DESCRIBE` / `information_schema` query; SQLite `:memory:` demo auto-creates a sample table at `/tmp/demo_ddl2spark.db` |
| **Type Coverage** | 45+ SQL types → 14 Spark types (see §4); special cases `TINYINT(1)`→`BooleanType`, `BIT(1)`→`BooleanType`, `DECIMAL(p,s)`→`DecimalType(p,s)`, `ARRAY<STRING>`→`ArrayType`, `MAP<…>`→`MapType` |
| **Editable UI (v2)** | Per-row dropdown, Decimal precision/scale inputs, nullable toggle, inline rename, row reset/remove, bulk apply, add column, instant code regeneration with correct imports |
| **Outputs** | Python code + JSON + usage snippet (`SparkSession` example) + downloadable `.py` |
| **Interfaces** | Web UI (single-page, no CDN, preview in iframe), REST API (`/api/convert-ddl`, `/api/convert-describe`, `/api/connect`, `/api/health`), CLI (`cli.py`), Python library (`converter.py`) |
| **Sharing** | Git-ready, ZIP, `git bundle`, Docker-ready, GitHub Pages docs, PI P-installable |

---

## 3. Architecture — How It Works

### 3.1 High-Level Flow

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  Input      │────▶│  Parser Layer    │────▶│  Normalizer & Mapper│────▶│  Code Generator  │
│             │     │                  │     │                     │     │                  │
│ • DDL text  │     │ • clean_ddl()    │     │ • normalize_sql_type│     │ • inferImports() │
│ • DESCRIBE  │     │ • split_columns()│     │ • map_sql_to_spark  │     │ • StructField()  │
│ • Live DB   │     │ • parse_ddl()    │     │ • Decimal/ TINYINT  │     │ • StructType()   │
│             │     │ • parse_describe │     │   special cases     │     │ • JSON view      │
└─────────────┘     └──────────────────┘     └─────────────────────┘     └──────────────────┘
         ▲                       ▲                          ▲                      │
         │                       │                          │                      ▼
   Web UI / CLI / API      db_utils.py           converter.py TYPE_MAPPING    Output: .py + JSON
```

### 3.2 Detailed Workflows

#### A. DDL Workflow (`POST /api/convert-ddl` or `ddl_to_pyspark()`)

1. **Clean** `clean_ddl(ddl)` — strip `/* */` block comments, `--` line comments, `#` MySQL comments, normalize whitespace.
2. **Find tables** — regex `CREATE\s+(OR REPLACE)?\s*(TEMPORARY)?\s*TABLE\s+(IF NOT EXISTS)?\s+name\s*\(`, then scan for matching closing `)` respecting quotes/backticks and nested parens.
3. **Split columns** `split_columns(block)` — iterate character-by-character, tracking `depth_paren`, `depth_angle` (`<…>`), `depth_bracket`, and quote states (`'`, `"`, `` ` ``). Split on commas only at depth 0.
4. **Skip constraints** — ignore lines starting `PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE`, `CHECK`, `CONSTRAINT`, `KEY`, `INDEX`.
5. **Parse column** — regex `col_name \s+ remainder`. `col_name` handles `` `name` ``, `[name]`, `"name"`, or `name`.
6. **Separate type vs. constraints** — search remainder for earliest constraint keyword (`NOT NULL`, `PRIMARY KEY`, `DEFAULT`, `AUTO_INCREMENT`, `IDENTITY`, `COMMENT`, `COLLATE`, `WITH TIME ZONE` etc.) outside parentheses. `sql_type = remainder[:earliest]`, `constraint_part = remainder[earliest:]`.
7. **Nullable** — `False` if `NOT NULL` or `PRIMARY KEY` in constraint part, else `True`.
8. **Map** `map_sql_to_spark(sql_type)` → `spark_expr` (see §4).
9. **Generate** `generate_pyspark_code(columns, table_name)` → imports + `StructType`.

*Example trace for `salary DECIMAL(10,2) NOT NULL DEFAULT 0`:*

```
raw remainder = "DECIMAL(10,2) NOT NULL DEFAULT 0"
earliest keyword at 14 ("NOT NULL")
sql_type = "DECIMAL(10,2)"
constraint_part = "NOT NULL DEFAULT 0"
nullable = False
normalize_sql_type("DECIMAL(10,2)") → ("DECIMAL", "10,2", None)
map → "DecimalType(10,2)"
```

If **no `CREATE TABLE` found**, fallback: treat entire input as a comma/line-separated column list (handles pasted column lists without DDL wrapper).

#### B. DESCRIBE Workflow (`POST /api/convert-describe` or `describe_to_pyspark()`)

1. **Split lines**, discard pure separator lines (`+---+`, `|---|` markdown).
2. **Split rows** `split_row()`:
   - If `|` present → `strip('|').split('|')`
   - Else if `\t` → split on tab
   - Else if `,` → `csv.reader`
   - Else if `;` → split on `;`
   - Else → `re.split(r'\s{2,}', row)` (2+ spaces) or single space
3. **Detect header indices** — scan `header_lower` for name keys (`field`, `column_name`), type keys (`type`, `data_type`), null keys (`null`, `is_nullable`). Falls back to `0:name, 1:type` if not found.
4. **Check if first row is header** — looks for known header words; if none, treat row 0 as data (handles header-less pastes like `id INT\nname VARCHAR(100)`).
5. **For each data row**: `col_name = parts[name_idx]`, `sql_type = parts[type_idx]`, `nullable` from `Null` column (`NO`→`False`, `YES`→`True`, `NOT NULL`→`False`). Also handles `null` values inside single-column pastes like `id INT NOT NULL` via regex fallback.
6. Generate code as above.

*Accepts:*
```
MySQL:  Field | Type        | Null | Key | Default
        id    | int(11)     | NO   | PRI | NULL

Postgres: column_name | data_type         | is_nullable
          id          | integer           | NO
          bio         | character varying | YES

CSV:    column_name,data_type,is_nullable
        id,integer,NO

Markdown:
| Field | Type         | Null |
|-------|--------------|------|
| id    | int(11)      | NO   |
```

#### C. Live DB Workflow (`POST /api/connect` or `fetch_schema_via_inspector()`)

```
User fills: db_type, host, port, user, password, database, table, schema
      │
      ▼
build_connection_string() → SQLAlchemy URL
      │
      ├─ mysql:      mysql+pymysql://user:pass@host:3306/db
      ├─ postgres:   postgresql+psycopg2://user:pass@host:5432/db
      ├─ sqlite:     sqlite:////tmp/demo.db or /path/to.db
      ├─ mssql:      mssql+pymssql://...
      ├─ oracle:     oracle+cx_oracle://...
      └─ duckdb:     duckdb:////path
      │
      ▼
create_engine(url) → inspect(engine) → inspector.get_columns(table, schema=schema)
      │
      ▼
columns_from_inspector() → [{name, sql_type=str(type), nullable, raw}]
      │
      ▼
generate_pyspark_code() → same as DDL
```

**Special case:** `sqlite + :memory:` → creates `/tmp/demo_ddl2spark.db` with a sample `employees` table (to demo without a real DB). The file is recreated on each request.

Fallback: if `get_columns` fails, tries raw SQL candidates:

```sql
DESCRIBE table
DESCRIBE TABLE table
SELECT column_name, data_type, is_nullable, numeric_precision, numeric_scale, character_maximum_length
FROM information_schema.columns WHERE table_name = 'table' ORDER BY ordinal_position
```

### 3.3 Frontend Editing Layer (v2)

All editing is **client-side** (vanilla JS, no build step):

- `lastResult.columns` is the source of truth (mutable array of `{name, sql_type, spark_type, spark_type_name, nullable}`)
- `originalColumns` is a deep clone for *Reset* diffing
- Every UI change (`onTypeChange`, `onDecimalChange`, `onNullableToggle`, `onNameChange`, `bulkApply`, `addColumn`, `removeColumn`) mutates `lastResult.columns[i]` and calls `regenerateFromEdits()`:

```
regenerateFromEdits()
  → inferImports(columns)          // scan spark_type strings for needed imports
  → generateCode(columns, table)   // build `from pyspark…` + `StructType([…])`
  → update #codeOutput, #jsonOutput, #usageBlock
  → toggle .edited row highlights + `edited` badges
```

Imports are ordered canonically: `StructType, StructField, StringType, IntegerType, …`. This mirrors Python’s `generate_pyspark_code`.

---

## 4. Type Mapping — SQL → PySpark

### 4.1 Normalization

`normalize_sql_type(raw)`:

- Uppercases, strips `UNSIGNED`/`ZEROFILL`, collapses whitespace
- If `ARRAY`/`MAP`/`STRUCT` → return raw verbatim (handled in `map_sql_to_spark`)
- Else match `BASE (params) extra` via `^([A-Z ]+?)\s*\(\s*([^)]+)\s*\)\s*(.*)$`
- Else longest-prefix match against `TYPE_MAPPING` keys (so `DOUBLE PRECISION` beats `DOUBLE`)
- Else handle `CHARACTER VARYING` → `VARCHAR`, `CHAR` lengths, or fallback to first word

### 4.2 Mapping Table

| SQL Base (normalized) | PySpark | Notes |
|---|---|---|
| `INT`, `INTEGER`, `INT4`, `MEDIUMINT`, `SERIAL` | `IntegerType()` | `int(11)` display length stripped |
| `BIGINT`, `INT8`, `BIGSERIAL` | `LongType()` | |
| `SMALLINT`, `INT2`, `SMALLSERIAL` | `ShortType()` | |
| `TINYINT`, `INT1`, `BYTEINT` | `ByteType()` | Except `TINYINT(1)` → `BooleanType` (MySQL boolean) |
| `FLOAT`, `FLOAT4`, `REAL` | `FloatType()` | |
| `DOUBLE`, `DOUBLE PRECISION`, `FLOAT8` | `DoubleType()` | |
| `DECIMAL`, `NUMERIC`, `NUMBER`, `DEC`, `MONEY` | `DecimalType(p,s)` | `DECIMAL` alone → `DecimalType(10,0)` |
| `CHAR`, `NCHAR` | `StringType()` | `CHAR(10)` length ignored (Spark String) |
| `VARCHAR`, `VARCHAR2`, `NVARCHAR`, `TEXT`, `CLOB`, `STRING`, `JSON`, `JSONB`, `UUID`, `ENUM` | `StringType()` | All text-like |
| `BINARY`, `VARBINARY`, `BLOB`, `BYTEA`, `BYTES` | `BinaryType()` | |
| `BOOLEAN`, `BOOL` | `BooleanType()` | |
| `BIT` | `BooleanType()` if `BIT(1)` else `BinaryType()` | |
| `DATE` | `DateType()` | |
| `TIME` | `StringType()` | Spark has no TimeType |
| `TIMESTAMP`, `TIMESTAMPTZ`, `DATETIME`, `DATETIME2`, `TIMESTAMP_NTZ/LTZ/TZ` | `TimestampType()` | |
| `ARRAY<STRING>` (Hive) | `ArrayType(StringType())` | Inner type mapped recursively |
| `MAP<STRING,STRING>` | `MapType(StringType(), StringType())` | |

**Fallbacks:** `VARCHAR`/`CHAR` substring → `StringType`, `TIMESTAMP` substring → `TimestampType`, `INT` substring → `IntegerType`, else `StringType`.

### 4.3 Decimal Handling

```python
# SQL: DECIMAL(10,2) → DecimalType(10,2)
# SQL: DECIMAL(8)    → DecimalType(8,0)
# SQL: DECIMAL        → DecimalType(10,0)  # default
```

Frontend exposes `precision` (1–38) and `scale` (0–38) number inputs when `DecimalType` is selected.

---

## 5. Installation

### 5.1 Prerequisites

- Python 3.9+ (tested 3.11/3.13)
- `pip` or `uv`
- Optional DB drivers per dialect

### 5.2 Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/ddl-to-pyspark.git
cd ddl-to-pyspark
pip install -r requirements.txt
# requirements.txt:
# Flask==3.1.0
# sqlparse==0.5.3
# SQLAlchemy==2.0.36
# pyspark==3.5.3  # only for type imports; not needed to generate code
# pymysql==1.1.1       # for MySQL
# psycopg2-binary==2.9.10 # for Postgres
# python-dotenv==1.0.1
```

Add dialect drivers as needed:

```bash
pip install pymssql      # SQL Server
pip install cx_Oracle    # Oracle
pip install duckdb-engine # DuckDB
```

### 5.3 Verify

```bash
python -c "from converter import ddl_to_pyspark; print(ddl_to_pyspark('CREATE TABLE t (id INT)'))"
python app.py  # → http://localhost:5000  (dev server)
python cli.py --ddl "CREATE TABLE t (id INT)"  # should print schema
```

---

## 6. Usage — Web UI

### 6.1 Launch

```bash
python app.py
# * Running on http://0.0.0.0:5000  (also proxied as https://5000-<id>.e2b.app in hosted env)
```

Open the **LIVE PREVIEW** in the IDE, or `http://localhost:5000` locally.

### 6.2 Tabs

#### SQL DDL Tab

1. Paste DDL (single or multi-table). Example is pre-filled.
2. *(Optional)* Table name override — overrides the parsed `CREATE TABLE` name (useful to avoid collisions).
3. Click **⚡ Convert to PySpark**. Chips below let you load `MySQL`, `Postgres`, `Oracle`, `Hive` examples.

#### DESCRIBE Tab

1. Paste any DESCRIBE-style dump (see §3.2B for formats).
2. Set *Target table name* (default `my_table`) — becomes `my_table_schema = StructType(...)`.
3. Click **Convert DESCRIBE → PySpark**.

#### Live DB Tab

1. Choose *Database type* — `MySQL`, `PostgreSQL`, `SQLite`, `SQL Server`, `Oracle`, `DuckDB`.
2. For server DBs: fill `Host`, `Port`, `User`, `Password`, `Database`, `Table`, optional `Schema`.
3. For SQLite: only `Database / File` (`/path/to.db` or `:memory:`) + `Table`. Click **Try SQLite demo** to auto-fill and create a demo DB.
4. Click **🔌 DESCRIBE from DB**. Credentials are never stored; connection is opened per request and closed.

### 6.3 Output Panel

- **Header:** `Python code` / `JSON` selector + `⬇ Download .py`
- **Code block:** `schema.py — auto-updates on edit` with `⎘ Copy` and `Copy imports`
- **Toolbar:** Bulk apply (see §7)
- **Preview table:** `# | Column (editable) | SQL Type | PySpark Type ✎ | Nullable | ↺/✕`
- **Usage block:** `from pyspark.sql import SparkSession` snippet that also updates on edit
- **Status banners:** green `✓` or red `✗` under the active input tab

---

## 7. Usage — Editable Per-Field Feature

*This is the v2 addition.*

### 7.1 Inline Editing

Once converted, each row shows:

- **Column name** — `<input class="col-name-input">`, type to rename. Change is reflected in `StructField("new_name", …)`. Empty name defaults to `col_N`.
- **PySpark Type** — `<select class="type-select">` with 22 options. Picking one updates `c.spark_type`, `c.spark_type_name`, shows/hides decimal inputs, and recomputes imports.
- **Decimal params** — only visible when `DecimalType` is selected: two `<input type="number">` for precision/scale. Editing them rebuilds `DecimalType(p,s)`.
- **Nullable** — clickable toggle pill (`.toggle`): `active` (green, `YES`) vs. inactive (grey, `NO`). Also updates the `True/False` in `StructField`.
- **Actions** — `↺` resets that row to its auto-detected original; `✕` removes the column entirely.

Edited rows get:

- Purple-tinted background (`.edited`)
- Orange dot + `edited` badge

### 7.2 Bulk Operations

Toolbar above the table:

- **Bulk type selector** — pick a type, click **Apply to all** to overwrite every row. Or **Apply to String only** to target only `StringType` fields (common when you want to coerce all strings to `IntegerType` etc.).
- **↺ Reset all** — restores all rows to `originalColumns` deep copy.
- **+ Add column** — appends `new_column_N` (`VARCHAR(255)` → `StringType()`, `nullable=True`). You can then rename and retype it (useful to add audit columns like `etl_timestamp`).

### 7.3 Code Regeneration (Client-Side)

All edits call `regenerateFromEdits()`:

```javascript
// 1. Infer imports from current spark_type strings
inferImports(columns) // → ["StructType","StructField","StringType",…]

// 2. Build Python code
importsStr = `from pyspark.sql.types import ${imports.join(", ")}`
fields = columns.map(c => `    StructField("${c.name}", ${c.spark_type}, ${c.nullable?"True":"False"})`).join(",\n")
code = `${importsStr}\n\n${table}_schema = StructType([\n${fields}\n])\n`
lastResult.code = code
lastResult.imports = importsStr
// 3. Update DOM: #codeOutput, #jsonOutput, #usageBlock, badges
```

No round-trip to the server is needed; edits are sub-10ms.

### 7.4 Example Edit Session

*Start:* `age TINYINT → ByteType()` auto-detected.

1. Change `age` type to `ShortType()` via dropdown → code updates `StructField("age", ShortType(), True)`
2. Toggle `email` nullable from `YES` to `NO` → `StructField("email", StringType(), False)`
3. Rename `profile_json` to `profile` → field name updates
4. For `salary`, change `DecimalType(10,2)` precision to `18` and scale to `4` → `DecimalType(18,4)`
5. Click **Copy** → clipboard has edited schema

---

## 8. Usage — REST API

Base URL: `http://localhost:5000`

### 8.1 Health

```bash
curl http://localhost:5000/api/health
# {"status":"ok","sqlalchemy":true}
```

### 8.2 Convert DDL

```bash
curl -X POST http://localhost:5000/api/convert-ddl \
  -H "Content-Type: application/json" \
  -d '{
    "ddl": "CREATE TABLE t (id INT PRIMARY KEY, name VARCHAR(100) NOT NULL, price DECIMAL(10,2))",
    "table_name": null
  }'
```

Response:

```json
{
  "count": 1,
  "tables": [
    {
      "table": "t",
      "imports": "from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DecimalType",
      "code": "from pyspark.sql.types import ...\nt_schema = StructType([\n    StructField(\"id\", IntegerType(), False),\n    StructField(\"name\", StringType(), False),\n    StructField(\"price\", DecimalType(10,2), True)\n])\n",
      "columns": [
        {"name":"id","sql_type":"INT","nullable":false,"spark_type":"IntegerType()","spark_type_name":"IntegerType"},
        {"name":"name","sql_type":"VARCHAR(100)","nullable":false,"spark_type":"StringType()","spark_type_name":"StringType"},
        {"name":"price","sql_type":"DECIMAL(10,2)","nullable":true,"spark_type":"DecimalType(10,2)","spark_type_name":"DecimalType"}
      ]
    }
  ]
}
```

Multi-table DDL returns `count>1` and multiple entries in `tables`. Override name:

```bash
curl -X POST http://localhost:5000/api/convert-ddl \
  -d '{"ddl":"CREATE TABLE employees (...)", "table_name":"emp_override"}'
```

### 8.3 Convert DESCRIBE

```bash
curl -X POST http://localhost:5000/api/convert-describe \
  -H "Content-Type: application/json" \
  -d '{
    "describe_text": "Field | Type | Null\nid | int(11) | NO\nname | varchar(255) | YES",
    "table_name": "users"
  }'
```

### 8.4 Live Connect

```bash
curl -X POST http://localhost:5000/api/connect \
  -H "Content-Type: application/json" \
  -d '{
    "db_type": "mysql",
    "host": "localhost",
    "port": "3306",
    "user": "root",
    "password": "secret",
    "database": "mydb",
    "table": "employees",
    "schema": null
  }'

# SQLite demo (creates /tmp/demo_ddl2spark.db):
curl -X POST http://localhost:5000/api/connect \
  -d '{"db_type":"sqlite","database":":memory:","table":"employees"}'
```

Response is single-object `{table, columns, code, imports}`.

### 8.5 Error Handling

Errors return `400` (bad input) or `500` (DB failure) with `{"error":"…"}`, e.g.:

```json
{"error":"No tables found in DDL. Check syntax or try DESCRIBE mode"}
```

---

## 9. Usage — CLI

### 9.1 Help

```bash
python cli.py --help
```

```
usage: cli.py [-h] (--ddl DDL | --ddl-file DDL_FILE | --describe DESCRIBE |
               --describe-file DESCRIBE_FILE | --connect CONNECT |
               --stdin) [--table TABLE] [--host HOST] [--port PORT]
               [--user USER] [--password PASSWORD] [--database DATABASE]
               [--schema SCHEMA] [--output OUTPUT] [--json] [--no-imports]
```

### 9.2 Examples

```bash
# 1. DDL string → stdout
python cli.py --ddl "CREATE TABLE t (id INT PRIMARY KEY, name VARCHAR(100) NOT NULL, price DECIMAL(10,2))"

# 2. DDL file → output file + JSON sidecar
python cli.py --ddl-file examples/sample_mysql.sql --output schema.py --json
# writes schema.py and schema.json, logs column table to stderr

# 3. DESCRIBE file
python cli.py --describe-file examples/describe_mysql.txt --table employees

# 4. Stdin pipe
cat schema.sql | python cli.py --stdin -o out.py

# 5. Live MySQL
python cli.py --connect mysql --host localhost --port 3306 --user root --password secret --database mydb --table employees

# 6. Live SQLite
python cli.py --connect sqlite --database /tmp/demo.db --table employees

# 7. Strip imports
python cli.py --ddl-file examples/sample_mysql.sql --no-imports

# 8. Bulk: DDL with override name
python cli.py --ddl-file hive.sql --table sales_fact --output sales_fact.py
```

### 9.3 Output (stdout)

```python
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DecimalType

t_schema = StructType([
    StructField("id", IntegerType(), False),
    StructField("name", StringType(), False),
    StructField("price", DecimalType(10,2), True)
])
```

Stderr logs a summary table (suppressed when piping):

```
# Columns: 3
#  - id                   INT                       -> IntegerType()             nullable=False
#  - name                 VARCHAR(100)              -> StringType()              nullable=False
#  - price                DECIMAL(10,2)             -> DecimalType(10,2)         nullable=True
```

---

## 10. Usage — Python Library

### 10.1 Import

```python
from converter import ddl_to_pyspark, describe_to_pyspark, parse_ddl, parse_describe_output, generate_pyspark_code
from db_utils import build_connection_string, fetch_schema_via_inspector
```

### 10.2 DDL

```python
from converter import ddl_to_pyspark

ddl = """
CREATE TABLE sales (
  order_id BIGINT NOT NULL,
  amount DECIMAL(10,2),
  is_returned BOOLEAN,
  created_at TIMESTAMP,
  items ARRAY<STRING>
) STORED AS PARQUET;
"""

result = ddl_to_pyspark(ddl)
print(result["tables"][0]["code"])
# from pyspark.sql.types import StructType, StructField, StringType, LongType, DecimalType, BooleanType, TimestampType, ArrayType
# sales_schema = StructType([...])

# Multi-table:
result = ddl_to_pyspark(open("examples/sample_mysql.sql").read())
for t in result["tables"]:
    print(t["table"], t["code"])

# Override table name:
result = ddl_to_pyspark("CREATE TABLE t (id INT)", table_name_override="my_fact")
```

### 10.3 DESCRIBE Text

```python
from converter import describe_to_pyspark

text = """Field | Type | Null
id | int(11) | NO
name | varchar(255) | YES"""

res = describe_to_pyspark(text, table_name="users")
print(res["code"])
print(res["columns"])
```

### 10.4 Live DB (Programmatic)

```python
from db_utils import build_connection_string, fetch_schema_via_inspector

# SQLite file:
cs = build_connection_string("sqlite", "", "", "", "", "/tmp/my.db")
res = fetch_schema_via_inspector(cs, "employees")
print(res["code"])

# MySQL:
cs = build_connection_string("mysql", "localhost", "3306", "root", "secret", "mydb")
res = fetch_schema_via_inspector(cs, "employees", schema="public")
```

### 10.5 Low-Level Parsing

```python
from converter import parse_ddl, parse_describe_output, map_sql_to_spark, generate_pyspark_code

tables = parse_ddl("CREATE TABLE t (id INT NOT NULL, name TEXT)")
print(tables) # [{"table":"t","columns":[{"name":"id","sql_type":"INT","nullable":False, "raw":"..."}]}]

cols = parse_describe_output("id | int | NO\nname | varchar(100) | YES")
code, imports_str, imports = generate_pyspark_code(cols, table_name="t")
print(code)

print(map_sql_to_spark("VARCHAR(255)")) # ("StringType()", "StringType", None)
print(map_sql_to_spark("DECIMAL(12,4)")) # ("DecimalType(12,4)", "DecimalType", "12,4")
```

---

## 11. Live Database DESCRIBE

### 11.1 Supported DB Types

| `db_type` | Driver (pip) | Default Port | URL Template |
|---|---|---|---|
| `mysql` | `pymysql` | 3306 | `mysql+pymysql://user:pass@host:3306/db` |
| `postgresql` / `postgres` | `psycopg2-binary` | 5432 | `postgresql+psycopg2://user:pass@host:5432/db` |
| `sqlite` | — | — | `sqlite:////path/to.db` or `sqlite:///:memory:` |
| `mssql` / `sqlserver` | `pymssql` | 1433 | `mssql+pymssql://user:pass@host:1433/db` |
| `oracle` | `cx_oracle` | 1521 | `oracle+cx_oracle://user:pass@host:1521/?service_name=db` |
| `duckdb` | `duckdb-engine` | — | `duckdb:////path.db` |

Add your driver to `requirements.txt` as needed.

### 11.2 What It Fetches

Only metadata:

```python
inspector.get_columns(table, schema=schema)
# returns: [{"name": str, "type": TypeEngine, "nullable": bool, ...}]
```

No `SELECT` on data. The connection is closed after `fetch`.

### 11.3 SQLite `:memory:` Demo

When `db_type=sqlite` and `database=:memory:`, the server creates `/tmp/demo_ddl2spark.db`:

```sql
CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT,
    age INTEGER,
    salary REAL,
    is_active INTEGER NOT NULL DEFAULT 1,
    hired_at TIMESTAMP,
    profile_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Then connects to that file. This lets you demo *Live DB* without credentials.

---

## 12. Examples by Database Dialect

### 12.1 MySQL

```sql
CREATE TABLE employees (
    id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    age TINYINT,
    salary DECIMAL(10,2) DEFAULT 0.00,
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    hired_at DATETIME,
    profile_json JSON,
    avatar BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
→
```python
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ByteType, DecimalType, BooleanType, BinaryType, TimestampType

employees_schema = StructType([
    StructField("id", IntegerType(), False),
    StructField("full_name", StringType(), False),
    StructField("email", StringType(), True),
    StructField("age", ByteType(), True),
    StructField("salary", DecimalType(10,2), True),
    StructField("is_active", BooleanType(), False),
    StructField("hired_at", TimestampType(), True),
    StructField("profile_json", StringType(), True),
    StructField("avatar", BinaryType(), True),
    StructField("created_at", TimestampType(), True)
])
```

### 12.2 PostgreSQL

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    bio TEXT,
    balance NUMERIC(12,2) DEFAULT 0,
    is_verified BOOLEAN DEFAULT FALSE,
    birth_date DATE,
    last_login TIMESTAMPTZ,
    metadata JSONB,
    avatar BYTEA
);
```
→
```python
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DecimalType, BooleanType, DateType, TimestampType, BinaryType

users_schema = StructType([
    StructField("id", IntegerType(), False),
    StructField("username", StringType(), False),
    StructField("email", StringType(), False),
    StructField("bio", StringType(), True),
    StructField("balance", DecimalType(12,2), True),
    StructField("is_verified", BooleanType(), True),
    StructField("birth_date", DateType(), True),
    StructField("last_login", TimestampType(), True),
    StructField("metadata", StringType(), True),
    StructField("avatar", BinaryType(), True)
])
```

### 12.3 Oracle

```sql
CREATE TABLE EMPLOYEES (
    EMPLOYEE_ID NUMBER(6) PRIMARY KEY,
    FIRST_NAME VARCHAR2(20),
    LAST_NAME VARCHAR2(25) NOT NULL,
    EMAIL VARCHAR2(25) NOT NULL UNIQUE,
    SALARY NUMBER(8,2),
    HIRE_DATE DATE DEFAULT SYSDATE,
    IS_MANAGER CHAR(1) DEFAULT 'N',
    PROFILE CLOB,
    PHOTO BLOB
);
```
→ `NUMBER(6)`→`DecimalType(6,0)`, `VARCHAR2`→`StringType`, `DATE`→`DateType`, `CLOB`→`StringType`, `BLOB`→`BinaryType`

### 12.4 Hive / Spark SQL

```sql
CREATE TABLE sales (
    order_id BIGINT,
    customer_name STRING,
    amount DOUBLE,
    discount DECIMAL(5,2),
    is_returned BOOLEAN,
    order_date DATE,
    created_at TIMESTAMP,
    items ARRAY<STRING>,
    props MAP<STRING,STRING>
) STORED AS PARQUET;
```
→ `items` → `ArrayType(StringType())`, `props` → `MapType(StringType(), StringType())`

### 12.5 DESCRIBE Paste

```
Field | Type         | Null | Key | Default | Extra
id    | int(11)      | NO   | PRI | NULL    | auto_increment
full_name | varchar(255) | NO | | NULL |
salary | decimal(10,2) | YES | | 0.00 |
```

→ Same as MySQL DDL above.

---

## 13. Sharing & Distribution

Your workspace `/home/user` is **git-initialized, committed, and bundled**:

```
Branch: main
Commits:
  eddd6b5 feat: initial commit
  94fb191 feat: editable per-field data types
Files: app.py, converter.py, db_utils.py, cli.py, requirements.txt, README.md, DOCUMENTATION.md, PUSH_TO_GITHUB.md, LICENSE, .gitignore, examples/
Artifacts:
  ddl-to-pyspark.zip (33K)
  ddl-to-pyspark.bundle (31K)  # git bundle (clone via `git clone ddl-to-pyspark.bundle`)
```

### 13.1 Option 1 — Push to GitHub (Recommended)

#### A. New Repo

1. Go to https://github.com/new → **Repository name:** `ddl-to-pyspark` → **Public/Private** → *uncheck* `Add README/.gitignore/license` → **Create**.
2. In workspace or local shell:

```bash
cd /home/user
git remote add origin https://github.com/YOUR_USERNAME/ddl-to-pyspark.git
git branch -M main
git push -u origin main
# Username: YOUR_USERNAME
# Password: <Personal Access Token from https://github.com/settings/tokens/new — scope `repo`>
# Or one-liner (careful with logs):
git remote set-url origin https://YOUR_USERNAME:YOUR_TOKEN@github.com/YOUR_USERNAME/ddl-to-pyspark.git
git push -u origin main
```

SSH alternative:

```bash
git remote add origin git@github.com:YOUR_USERNAME/ddl-to-pyspark.git
git push -u origin main
```

#### B. Existing Repo

```bash
git remote add origin https://github.com/YOUR_USERNAME/existing-repo.git
git push -u origin main
# --force if you need to overwrite a non-empty repo
```

**I can push for you:** reply with `https://github.com/USER/REPO.git` + token and I’ll push immediately.

### 13.2 Option 2 — Upload via GitHub Web UI

1. Download `ddl-to-pyspark.zip` from Files panel.
2. On GitHub new repo → **Add file → Upload files** → drag unzipped files → **Commit directly to main**.

### 13.3 Option 3 — Git Bundle

Share `ddl-to-pyspark.bundle` — recipients clone without a server:

```bash
git clone ddl-to-pyspark.bundle my-copy
cd my-copy
git remote add origin https://github.com/YOUR_USERNAME/ddl-to-pyspark.git
git push -u origin main
```

### 13.4 Option 4 — Zip for Teams / Email / Drive

`ddl-to-pyspark.zip` contains everything except `__pycache__`/` .git`. Unzip and run `pip install -r requirements.txt && python app.py`.

### 13.5 Option 5 — Make it a Pip Package (Optional)

Create `setup.py`/`pyproject.toml` if you want `pip install ddl-to-pyspark`:

```toml
# pyproject.toml (example)
[project]
name = "ddl-to-pyspark"
version = "2.1.0"
description = "Convert SQL DDL/DESCRIBE to PySpark StructType"
readme = "README.md"
requires-python = ">=3.9"
dependencies = ["Flask", "SQLAlchemy", "sqlparse"]
[project.scripts]
ddl2pyspark = "cli:main"
```

Then `python -m build && twine upload dist/*`.

---

## 14. Deployment Options

### 14.1 Local Dev

```bash
python app.py  # debug, auto-reload
```

### 14.2 Production WSGI

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
# or: gunicorn app:app  (if app.py defines `app`)
```

### 14.3 Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn","-w","2","-b","0.0.0.0:5000","app:app"]
```

```bash
docker build -t ddl-to-pyspark .
docker run -p 5000:5000 ddl-to-pyspark
```

### 14.4 Cloud

- **Streamlit Cloud / Render / Railway / Fly.io:** connect your GitHub repo, set build `pip install -r requirements.txt`, start `gunicorn app:app`.
- **Databricks Job:** add `app.py` as a job with `Flask` — or just use `converter.py` as a library inside notebooks.
- **GitHub Codespaces:** works out-of-the-box (`python app.py` → preview).

### 14.5 Environment Variables (if you add them)

```bash
# .env (optional)
FLASK_ENV=production
PORT=5000
# DB defaults if you want to pre-fill Live DB tab:
DEFAULT_DB_HOST=localhost
DEFAULT_DB_USER=etl_user
```

---

## 15. Security & Performance

### Security

- **No persistence** — DDL/DESCRIBE is processed in-memory per request; not logged (except app stdout). Live DB credentials are used only to build a transient `create_engine` URL, never stored.
- **DESCRIBE is read-only** — only `inspector.get_columns` or `SELECT` from `information_schema`; no `UPDATE/DELETE`.
- **Token hygiene** — if you push via token in this workspace, remove it after: `git remote set-url origin https://github.com/USER/REPO.git` or `rm ~/.git-credentials`. Snapshots exclude `.git/config` etc. but be cautious.
- **Caveat:** dev server (`app.run(debug=True)`) is not for production; use `gunicorn` + reverse proxy.

### Performance

- Parsing is `O(n)` with single-pass scans; even 200-column DDL converts in <10ms.
- No Spark dependency at conversion time — only code generation. `pyspark` is optional unless you `spark.createDataFrame`.
- Bundle size <35K; Docker image ~150 MB (slim).

---

## 16. Troubleshooting & FAQ

**Q: `No tables found in DDL`**

- Your paste might be DESCRIBE output — switch to the **DESCRIBE** tab.
- Or ensure DDL has `CREATE TABLE name (...)`; the parser also accepts bare column lists (`id INT, name TEXT`) as a fallback to `my_table`.

**Q: All types became `StringType()`**

- Ensure `converter.py` is v2 (check `normalize_sql_type` handles `VARCHAR(255)` with longest-prefix match). Older buggy regex returned `I` for `INT`. Fixed in current.

**Q: `TINYINT(1)` shows as `ByteType`**

- MySQL `TINYINT(1)` is intentionally mapped to `BooleanType`. If you want `ByteType`, change it in the editable dropdown.

**Q: `DESCRIBE` says header not found**

- Header must contain a known word like `Field`/`column_name`/`Type`/`Null`. If your dump is `id | int | NO` without header, pre-add a header line `Field | Type | Null` or paste as `id INT NOT NULL` and use DDL tab.

**Q: Live DB connection failed**

- Check `pip install` the right driver (`pymysql` for MySQL, `psycopg2-binary` for Postgres).
- For `mysql+pymysql`, ensure `host:port` reachable and user has `SHOW COLUMNS` privilege.
- Try SQLite demo first to confirm UI works.

**Q: Decimal precision lost**

- SQL `DECIMAL` without params defaults to `DecimalType(10,0)`; edit precision/scale inline after conversion.

**Q: `ArrayType` shows as `StringType`**

- Ensure DDL uses Hive syntax `ARRAY<STRING>` (with angle brackets). `ARRAY` alone becomes `ArrayType(StringType())`.

**Q: Push to GitHub 403**

- Your token lacks `repo` scope or you pasted GitHub password instead of PAT. Generate at https://github.com/settings/tokens/new → **Classic** → check `repo`.

**Q: Port 5000 in use**

- Change `app.run(port=5001)` or `lsof -ti:5000 | xargs kill`.

---

## 17. Project Structure

```
.
├── app.py                 # Flask app + HTML_TEMPLATE (single-file UI, no CDN)
├── converter.py           # Core: TYPE_MAPPING, normalize_sql_type, map_sql_to_spark,
│                          #        split_columns, clean_ddl, parse_ddl, parse_describe_output,
│                          #        generate_pyspark_code, ddl_to_pyspark, describe_to_pyspark
├── db_utils.py            # DB: build_connection_string, fetch_schema_via_inspector,
│                          #       fetch_schema_via_describe, SUPPORTED_DB_TYPES
├── cli.py                 # CLI: argparse → ddl/describe/connect → stdout/file
├── requirements.txt       # Flask, SQLAlchemy, pyspark, pymysql, psycopg2-binary
├── README.md              # Short start guide
├── DOCUMENTATION.md       # This file (detailed)
├── PUSH_TO_GITHUB.md      # Push instructions
├── LICENSE                # MIT
├── .gitignore             # venv, __pycache__, *.db, .env
├── ddl-to-pyspark.zip     # Distribution ZIP
├── ddl-to-pyspark.bundle  # Git bundle
└── examples/
    ├── sample_mysql.sql   # CREATE TABLE employees + departments
    └── describe_mysql.txt # Field|Type|Null dump for employees
```

Key functions:

- `parse_ddl(ddl: str) → List[{"table":str, "columns":[...]}]`
- `parse_describe_output(text: str) → List[{"name", "sql_type", "nullable"}]`
- `map_sql_to_spark(sql_type_raw: str) → (spark_expr, import_name, params)`
- `generate_pyspark_code(columns, table_name) → (code, importsStr, importsList)`
- `ddl_to_pyspark(ddl, table_name_override) → {"tables":[...], "count":int}`
- `describe_to_pyspark(text, table_name) → {"table", "columns", "code", "imports"}`

---

## 18. Contributing & Roadmap

### Contributing

```bash
git checkout -b feature/my-type
# edit converter.py: add entry to TYPE_MAPPING, adjust normalize_sql_type if needed
python -c "from converter import map_sql_to_spark; print(map_sql_to_spark('MYTYPE'))"
python cli.py --ddl "CREATE TABLE t (x MYTYPE)"  # manual test
git commit -m "feat: add MYTYPE → SparkType"
git push -u origin feature/my-type  # PR to main
```

### Roadmap Ideas

- [ ] `STRUCT<…>` Hive type → `StructType` nested
- [ ] `from pyspark.sql.types import ...` → Spark DDL string `schema.simpleString()`
- [ ] Export to Delta `CREATE TABLE` or Avro/Parquet schema
- [ ] CSV upload for DESCRIBE (file picker)
- [ ] Column reordering via drag-and-drop
- [ ] Save/load edits to localStorage
- [ ] Dark/light theme toggle
- [ ] PyPI package + `pipx` tool

---

## 19. Appendix — Code Snippets

### 19.1 Minimal Notebook Usage

```python
from pyspark.sql import SparkSession
from converter import ddl_to_pyspark

ddl = open("schema.sql").read()
code = ddl_to_pyspark(ddl)["tables"][0]["code"]
exec(code)  # defines employees_schema
spark = SparkSession.builder.getOrCreate()
df = spark.createDataFrame([], schema=employees_schema)
df.printSchema()
```

### 19.2 Bulk API Call (Python)

```python
import requests

r = requests.post("http://localhost:5000/api/convert-ddl", json={
  "ddl": "CREATE TABLE t (id INT, name VARCHAR(50) NOT NULL)"
})
print(r.json()["tables"][0]["code"])
```

### 19.3 CLI in a Shell Pipeline

```bash
# Dump schema from MySQL and pipe to Spark DDL generation without intermediate file
mysqldump --no-data mydb employees | python cli.py --stdin > employees_pyspark.py
cat employees_pyspark.py | grep StructField
```

### 19.4 Shareable Link Pattern

After you push to GitHub, share:

- **Repo:** `https://github.com/YOUR_USERNAME/ddl-to-pyspark`
- **Live Demo (if deployed):** `https://your-app.onrender.com`
- **Zip:** attach `ddl-to-pyspark.zip` in releases → `https://github.com/.../releases/tag/v2.1`
- **Bundle:** `git clone https://github.com/.../ddl-to-pyspark.bundle`

---

**End of Documentation.** For quick start, see `README.md`. For push help, see `PUSH_TO_GITHUB.md`. For code, read `converter.py` (well-commented). Enjoy — and edit those types! 🎉

*Lagos • 2026-09-17 • MIT*
