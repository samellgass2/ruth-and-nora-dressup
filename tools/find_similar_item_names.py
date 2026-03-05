#!/usr/bin/env python3
"""Find similar item names in a configured database table.

Usage:
  python3 tools/find_similar_item_names.py --config tools/samples/item_similarity_sample_config.json
  python3 tools/find_similar_item_names.py --config /path/to/config.json --json

Config schema (JSON):
{
  "database": {
    "driver": "sqlite",
    "path": "tools/samples/item_similarity_sample.db",
    "uri": false
  },
  "query": {
    "table": "items",
    "id_column": "id",
    "name_column": "name",
    "where": "is_active = 1"
  },
  "similarity": {
    "threshold": 0.72,
    "top_k_per_item": 3,
    "min_name_length": 3
  }
}
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONFIG_MISSING_EXIT_CODE = 2
DB_CONNECTION_EXIT_CODE = 3
QUERY_FAILURE_EXIT_CODE = 4
CONFIG_INVALID_EXIT_CODE = 5

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SPACE_PATTERN = re.compile(r"\s+")
NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9\s]+")


@dataclass(frozen=True)
class DatabaseConfig:
    driver: str
    path: str
    uri: bool


@dataclass(frozen=True)
class QueryConfig:
    table: str
    id_column: str
    name_column: str
    where: str | None


@dataclass(frozen=True)
class SimilarityConfig:
    threshold: float
    top_k_per_item: int
    min_name_length: int


@dataclass(frozen=True)
class ToolConfig:
    database: DatabaseConfig
    query: QueryConfig
    similarity: SimilarityConfig


@dataclass(frozen=True)
class ItemRecord:
    item_id: str
    name: str


@dataclass(frozen=True)
class NamePair:
    left: ItemRecord
    right: ItemRecord
    score: float
    levenshtein_similarity: float
    token_jaccard: float
    prefix_similarity: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Find similar item names from a DB table")
    parser.add_argument("--config", required=True, help="Path to JSON config")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    return parser.parse_args()


def fail(message: str, exit_code: int) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(exit_code)


def load_config(config_path: Path) -> ToolConfig:
    if not config_path.exists():
        fail(f"Config file not found: {config_path}", CONFIG_MISSING_EXIT_CODE)

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"Config is not valid JSON ({error})", CONFIG_INVALID_EXIT_CODE)

    if not isinstance(data, dict):
        fail("Config root must be an object", CONFIG_INVALID_EXIT_CODE)

    database_data = require_object(data, "database")
    query_data = require_object(data, "query")
    similarity_data = require_object(data, "similarity")

    database = DatabaseConfig(
        driver=require_string(database_data, "driver"),
        path=require_string(database_data, "path"),
        uri=require_bool_with_default(database_data, "uri", default=False),
    )

    query = QueryConfig(
        table=validated_identifier(require_string(query_data, "table"), "query.table"),
        id_column=validated_identifier(require_string(query_data, "id_column"), "query.id_column"),
        name_column=validated_identifier(require_string(query_data, "name_column"), "query.name_column"),
        where=optional_string(query_data, "where"),
    )

    similarity = SimilarityConfig(
        threshold=require_float_with_default(similarity_data, "threshold", default=0.72),
        top_k_per_item=require_int_with_default(similarity_data, "top_k_per_item", default=3),
        min_name_length=require_int_with_default(similarity_data, "min_name_length", default=3),
    )

    if database.driver != "sqlite":
        fail(
            f"Unsupported database driver '{database.driver}'. Only 'sqlite' is supported.",
            CONFIG_INVALID_EXIT_CODE,
        )

    if not (0.0 <= similarity.threshold <= 1.0):
        fail("similarity.threshold must be between 0 and 1", CONFIG_INVALID_EXIT_CODE)

    if similarity.top_k_per_item < 1:
        fail("similarity.top_k_per_item must be at least 1", CONFIG_INVALID_EXIT_CODE)

    if similarity.min_name_length < 1:
        fail("similarity.min_name_length must be at least 1", CONFIG_INVALID_EXIT_CODE)

    return ToolConfig(database=database, query=query, similarity=similarity)


def require_object(source: dict[str, Any], key: str) -> dict[str, Any]:
    value = source.get(key)
    if isinstance(value, dict):
        return value
    fail(f"Missing or invalid object for key '{key}'", CONFIG_INVALID_EXIT_CODE)


def require_string(source: dict[str, Any], key: str) -> str:
    value = source.get(key)
    if isinstance(value, str) and value.strip():
        return value
    fail(f"Missing or invalid string for key '{key}'", CONFIG_INVALID_EXIT_CODE)


def optional_string(source: dict[str, Any], key: str) -> str | None:
    value = source.get(key)
    if value is None:
        return None
    if isinstance(value, str) and value.strip():
        return value
    fail(f"Invalid value for optional key '{key}'", CONFIG_INVALID_EXIT_CODE)


def require_bool_with_default(source: dict[str, Any], key: str, default: bool) -> bool:
    value = source.get(key, default)
    if isinstance(value, bool):
        return value
    fail(f"Invalid boolean value for key '{key}'", CONFIG_INVALID_EXIT_CODE)


def require_int_with_default(source: dict[str, Any], key: str, default: int) -> int:
    value = source.get(key, default)
    if isinstance(value, int):
        return value
    fail(f"Invalid integer value for key '{key}'", CONFIG_INVALID_EXIT_CODE)


def require_float_with_default(source: dict[str, Any], key: str, default: float) -> float:
    value = source.get(key, default)
    if isinstance(value, (int, float)):
        return float(value)
    fail(f"Invalid numeric value for key '{key}'", CONFIG_INVALID_EXIT_CODE)


def validated_identifier(value: str, label: str) -> str:
    if IDENTIFIER_PATTERN.match(value):
        return value
    fail(
        f"Invalid SQL identifier for {label}. Use letters, digits, and underscore only.",
        CONFIG_INVALID_EXIT_CODE,
    )


def open_db_connection(config: DatabaseConfig) -> sqlite3.Connection:
    try:
        connection = sqlite3.connect(config.path, uri=config.uri)
        connection.row_factory = sqlite3.Row
        return connection
    except sqlite3.Error as error:
        fail(f"Unable to connect to database at '{config.path}' ({error})", DB_CONNECTION_EXIT_CODE)


def fetch_item_records(connection: sqlite3.Connection, query: QueryConfig) -> list[ItemRecord]:
    select_sql = (
        f"SELECT {query.id_column} AS item_id, {query.name_column} AS item_name "
        f"FROM {query.table}"
    )
    if query.where:
        select_sql = f"{select_sql} WHERE {query.where}"

    try:
        rows = connection.execute(select_sql).fetchall()
    except sqlite3.Error as error:
        fail(
            f"Failed querying table '{query.table}' for id/name columns ({error})",
            QUERY_FAILURE_EXIT_CODE,
        )

    records: list[ItemRecord] = []
    for row in rows:
        item_id = row["item_id"]
        item_name = row["item_name"]
        if item_id is None or item_name is None:
            continue
        records.append(ItemRecord(item_id=str(item_id), name=str(item_name)))

    return records


def normalize_name(name: str) -> str:
    lowered = name.lower().strip()
    stripped = NON_ALNUM_PATTERN.sub(" ", lowered)
    return SPACE_PATTERN.sub(" ", stripped).strip()


def token_set(name: str) -> set[str]:
    normalized = normalize_name(name)
    if not normalized:
        return set()
    return {part for part in normalized.split(" ") if part}


def levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous_row = list(range(len(right) + 1))

    for i, left_char in enumerate(left, start=1):
        current_row = [i]
        for j, right_char in enumerate(right, start=1):
            insertions = previous_row[j] + 1
            deletions = current_row[j - 1] + 1
            substitutions = previous_row[j - 1] + (left_char != right_char)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def levenshtein_similarity(left: str, right: str) -> float:
    normalized_left = normalize_name(left)
    normalized_right = normalize_name(right)
    denominator = max(len(normalized_left), len(normalized_right))
    if denominator == 0:
        return 1.0
    distance = levenshtein_distance(normalized_left, normalized_right)
    return 1.0 - (distance / denominator)


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    union = left.union(right)
    if not union:
        return 0.0
    intersection = left.intersection(right)
    return len(intersection) / len(union)


def prefix_similarity(left: str, right: str) -> float:
    normalized_left = normalize_name(left)
    normalized_right = normalize_name(right)

    max_len = max(len(normalized_left), len(normalized_right))
    if max_len == 0:
        return 1.0

    common = 0
    for left_char, right_char in zip(normalized_left, normalized_right):
        if left_char != right_char:
            break
        common += 1

    return common / max_len


def compute_hybrid_similarity(left: str, right: str) -> tuple[float, float, float, float]:
    lev = levenshtein_similarity(left, right)
    jac = jaccard_similarity(token_set(left), token_set(right))
    prefix = prefix_similarity(left, right)

    score = (0.55 * lev) + (0.35 * jac) + (0.10 * prefix)
    return score, lev, jac, prefix


def find_similar_pairs(records: list[ItemRecord], config: SimilarityConfig) -> list[NamePair]:
    pairs: list[NamePair] = []

    for left_index, left in enumerate(records):
        for right in records[left_index + 1 :]:
            if len(normalize_name(left.name)) < config.min_name_length:
                continue
            if len(normalize_name(right.name)) < config.min_name_length:
                continue

            score, lev, jac, prefix = compute_hybrid_similarity(left.name, right.name)
            if score < config.threshold:
                continue

            pairs.append(
                NamePair(
                    left=left,
                    right=right,
                    score=score,
                    levenshtein_similarity=lev,
                    token_jaccard=jac,
                    prefix_similarity=prefix,
                )
            )

    pairs.sort(key=lambda pair: pair.score, reverse=True)

    if not pairs:
        return []

    per_item_count: dict[str, int] = {}
    limited_pairs: list[NamePair] = []

    for pair in pairs:
        left_count = per_item_count.get(pair.left.item_id, 0)
        right_count = per_item_count.get(pair.right.item_id, 0)

        if left_count >= config.top_k_per_item or right_count >= config.top_k_per_item:
            continue

        limited_pairs.append(pair)
        per_item_count[pair.left.item_id] = left_count + 1
        per_item_count[pair.right.item_id] = right_count + 1

    return limited_pairs


def render_text_output(pairs: list[NamePair], total_records: int) -> str:
    if not pairs:
        return f"No similar records found across {total_records} records."

    lines: list[str] = []
    lines.append(f"Found {len(pairs)} similar record pair(s) across {total_records} records.")
    lines.append("score | left_id | left_name | right_id | right_name")

    for pair in pairs:
        lines.append(
            " | ".join(
                [
                    f"{pair.score:.3f}",
                    pair.left.item_id,
                    pair.left.name,
                    pair.right.item_id,
                    pair.right.name,
                ]
            )
        )

    return "\n".join(lines)


def render_json_output(pairs: list[NamePair], total_records: int) -> str:
    payload = {
        "total_records": total_records,
        "pair_count": len(pairs),
        "pairs": [
            {
                "score": round(pair.score, 6),
                "levenshtein_similarity": round(pair.levenshtein_similarity, 6),
                "token_jaccard": round(pair.token_jaccard, 6),
                "prefix_similarity": round(pair.prefix_similarity, 6),
                "left": {"id": pair.left.item_id, "name": pair.left.name},
                "right": {"id": pair.right.item_id, "name": pair.right.name},
            }
            for pair in pairs
        ],
    }
    return json.dumps(payload, indent=2)


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    config = load_config(config_path)

    connection = open_db_connection(config.database)
    try:
        records = fetch_item_records(connection, config.query)
    finally:
        connection.close()

    pairs = find_similar_pairs(records, config.similarity)

    if args.json:
        print(render_json_output(pairs, len(records)))
    else:
        print(render_text_output(pairs, len(records)))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
