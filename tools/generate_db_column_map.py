#!/usr/bin/env python3
"""Generate map-like output from a SQLite table column operation.

Usage examples:
  python3 tools/generate_db_column_map.py \
    --database tools/samples/item_similarity_sample.db \
    --table items \
    --column is_active \
    --operation value_counts

  python3 tools/generate_db_column_map.py \
    --database tools/samples/item_similarity_sample.db \
    --table items \
    --column id \
    --operation sum \
    --json
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

CONFIG_INVALID_EXIT_CODE = 2
DB_CONNECTION_EXIT_CODE = 3
QUERY_FAILURE_EXIT_CODE = 4
OPERATION_INVALID_EXIT_CODE = 5

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SUPPORTED_OPERATIONS = {
    "value_counts",
    "count",
    "count_distinct",
    "min",
    "max",
    "sum",
    "avg",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an operation on a SQLite table column and output a map-like result"
    )
    parser.add_argument("--database", required=True, help="Path to SQLite database")
    parser.add_argument("--table", required=True, help="Table name")
    parser.add_argument("--column", required=True, help="Column name")
    parser.add_argument("--operation", required=True, help=f"One of: {', '.join(sorted(SUPPORTED_OPERATIONS))}")
    parser.add_argument("--where", help="Optional SQL WHERE clause")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    return parser.parse_args()


def fail(message: str, exit_code: int) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(exit_code)


def validated_identifier(value: str, label: str) -> str:
    if IDENTIFIER_PATTERN.match(value):
        return value
    fail(
        f"Invalid SQL identifier for {label}. Use letters, digits, and underscore only.",
        CONFIG_INVALID_EXIT_CODE,
    )


def build_where_clause(where: str | None) -> str:
    if where is None:
        return ""
    stripped = where.strip()
    if not stripped:
        fail("--where cannot be empty when provided", CONFIG_INVALID_EXIT_CODE)
    return f" WHERE {stripped}"


def connect_sqlite(database_path: Path) -> sqlite3.Connection:
    try:
        return sqlite3.connect(database_path)
    except sqlite3.Error as error:
        fail(f"Unable to connect to database at '{database_path}' ({error})", DB_CONNECTION_EXIT_CODE)


def run_operation(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    operation: str,
    where: str | None,
) -> dict[str, int | float | str | None]:
    sql_where = build_where_clause(where)

    if operation == "value_counts":
        sql = (
            f"SELECT {column} AS result_key, COUNT(*) AS result_count "
            f"FROM {table}{sql_where} GROUP BY {column} "
            "ORDER BY result_count DESC, result_key ASC"
        )
        try:
            rows = connection.execute(sql).fetchall()
        except sqlite3.Error as error:
            fail(f"Failed to execute operation '{operation}' ({error})", QUERY_FAILURE_EXIT_CODE)

        result: dict[str, int] = {}
        for key, count in rows:
            display_key = "<NULL>" if key is None else str(key)
            result[display_key] = int(count)
        return result

    operation_sql_map = {
        "count": f"SELECT COUNT({column}) AS result_value FROM {table}{sql_where}",
        "count_distinct": f"SELECT COUNT(DISTINCT {column}) AS result_value FROM {table}{sql_where}",
        "min": f"SELECT MIN({column}) AS result_value FROM {table}{sql_where}",
        "max": f"SELECT MAX({column}) AS result_value FROM {table}{sql_where}",
        "sum": f"SELECT SUM({column}) AS result_value FROM {table}{sql_where}",
        "avg": f"SELECT AVG({column}) AS result_value FROM {table}{sql_where}",
    }

    sql = operation_sql_map.get(operation)
    if sql is None:
        fail(
            f"Unsupported operation '{operation}'. Expected one of: {', '.join(sorted(SUPPORTED_OPERATIONS))}",
            OPERATION_INVALID_EXIT_CODE,
        )

    try:
        row = connection.execute(sql).fetchone()
    except sqlite3.Error as error:
        fail(f"Failed to execute operation '{operation}' ({error})", QUERY_FAILURE_EXIT_CODE)

    if row is None:
        return {operation: None}

    return {operation: row[0]}


def render_text_output(result: dict[str, int | float | str | None]) -> str:
    if not result:
        return "No results."

    lines = ["key | value"]
    for key, value in result.items():
        lines.append(f"{key} | {value}")
    return "\n".join(lines)


def render_json_output(
    *,
    table: str,
    column: str,
    operation: str,
    where: str | None,
    result: dict[str, int | float | str | None],
) -> str:
    payload = {
        "table": table,
        "column": column,
        "operation": operation,
        "where": where,
        "result": result,
    }
    return json.dumps(payload, indent=2)


def main() -> int:
    args = parse_args()

    table = validated_identifier(args.table, "table")
    column = validated_identifier(args.column, "column")
    operation = args.operation.strip().lower()

    if operation not in SUPPORTED_OPERATIONS:
        fail(
            f"Unsupported operation '{args.operation}'. Expected one of: {', '.join(sorted(SUPPORTED_OPERATIONS))}",
            OPERATION_INVALID_EXIT_CODE,
        )

    database_path = Path(args.database)
    if not database_path.exists():
        fail(f"Database file not found: {database_path}", CONFIG_INVALID_EXIT_CODE)

    connection = connect_sqlite(database_path)
    try:
        result = run_operation(
            connection=connection,
            table=table,
            column=column,
            operation=operation,
            where=args.where,
        )
    finally:
        connection.close()

    if args.json:
        print(
            render_json_output(
                table=table,
                column=column,
                operation=operation,
                where=args.where,
                result=result,
            )
        )
    else:
        print(render_text_output(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
