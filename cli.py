#!/usr/bin/env python3
"""
CLI for DDL → PySpark converter.
Usage:
  python cli.py --ddl-file sample.sql
  python cli.py --ddl "CREATE TABLE t (id INT, name VARCHAR(50))"
  python cli.py --describe-file describe.txt --table my_table
  python cli.py --connect mysql --host localhost --port 3306 --user root --password pass --database mydb --table employees
  cat schema.sql | python cli.py --stdin

Outputs PySpark StructType code to stdout or --output file.
"""
import argparse
import sys
import os
from converter import ddl_to_pyspark, describe_to_pyspark
from db_utils import build_connection_string, fetch_schema_via_inspector

def main():
    parser = argparse.ArgumentParser(description="Convert SQL DDL / DESCRIBE to PySpark schema")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ddl", type=str, help="DDL string")
    group.add_argument("--ddl-file", type=str, help="Path to .sql file with CREATE TABLE")
    group.add_argument("--describe", type=str, help="DESCRIBE text string")
    group.add_argument("--describe-file", type=str, help="Path to file with DESCRIBE output")
    group.add_argument("--connect", type=str, help="DB type to live-connect (mysql, postgresql, sqlite, mssql, oracle, duckdb)")
    group.add_argument("--stdin", action="store_true", help="Read DDL from stdin")

    parser.add_argument("--table", type=str, help="Table name override / target table for DESCRIBE", default=None)
    parser.add_argument("--host", type=str, default="localhost", help="DB host")
    parser.add_argument("--port", type=str, default="", help="DB port")
    parser.add_argument("--user", type=str, default="", help="DB user")
    parser.add_argument("--password", type=str, default="", help="DB password")
    parser.add_argument("--database", type=str, default="", help="DB name / SQLite file")
    parser.add_argument("--schema", type=str, default=None, help="DB schema (optional)")
    parser.add_argument("--output", "-o", type=str, help="Output file (default stdout)")
    parser.add_argument("--json", action="store_true", help="Also output JSON")
    parser.add_argument("--no-imports", action="store_true", help="Don't include imports in output")

    args = parser.parse_args()

    try:
        result = None
        if args.ddl is not None:
            result = ddl_to_pyspark(args.ddl, table_name_override=args.table)
            output_code = "\n\n".join([t["code"] for t in result["tables"]])
            output_json = result
        elif args.ddl_file is not None:
            with open(args.ddl_file, "r", encoding="utf-8") as f:
                ddl = f.read()
            result = ddl_to_pyspark(ddl, table_name_override=args.table)
            output_code = "\n\n".join([t["code"] for t in result["tables"]])
            output_json = result
        elif args.describe is not None:
            table = args.table or "my_table"
            result = describe_to_pyspark(args.describe, table_name=table)
            output_code = result["code"]
            output_json = result
        elif args.describe_file is not None:
            with open(args.describe_file, "r", encoding="utf-8") as f:
                txt = f.read()
            table = args.table or "my_table"
            result = describe_to_pyspark(txt, table_name=table)
            output_code = result["code"]
            output_json = result
        elif args.stdin:
            ddl = sys.stdin.read()
            result = ddl_to_pyspark(ddl, table_name_override=args.table)
            output_code = "\n\n".join([t["code"] for t in result["tables"]])
            output_json = result
        elif args.connect:
            if not args.database or not args.table:
                parser.error("--connect requires --database and --table")
            conn_str = build_connection_string(args.connect, args.host, args.port, args.user, args.password, args.database)
            print(f"# Connecting to {args.connect}://{args.host}/{args.database} table={args.table} ...", file=sys.stderr)
            result = fetch_schema_via_inspector(conn_str, args.table, schema=args.schema)
            output_code = result["code"]
            output_json = result

        if args.no_imports and result:
            # Strip imports - naive: remove first line if starts with from pyspark
            lines = output_code.splitlines()
            output_code = "\n".join([l for l in lines if not l.strip().startswith("from pyspark")])

        if args.output:
            with open(args.output, "w", encoding="utf-8") as out:
                out.write(output_code)
                out.write("\n")
            print(f"Wrote PySpark schema to {args.output}", file=sys.stderr)
            if args.json:
                jpath = os.path.splitext(args.output)[0] + ".json"
                import json
                with open(jpath, "w", encoding="utf-8") as jf:
                    json.dump(output_json, jf, indent=2)
                print(f"Wrote JSON to {jpath}", file=sys.stderr)
        else:
            print(output_code)
            if args.json:
                import json
                print("\n# --- JSON ---", file=sys.stderr)
                print(json.dumps(output_json, indent=2))

        # Pretty table to stderr
        if result:
            cols = result["columns"] if "columns" in result else (result["tables"][0]["columns"] if "tables" in result else [])
            if cols:
                print(f"\n# Columns: {len(cols)}", file=sys.stderr)
                for c in cols:
                    print(f"#  - {c['name']:20s} {c['sql_type']:25s} -> {c['spark_type']:25s} nullable={c['nullable']}", file=sys.stderr)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
