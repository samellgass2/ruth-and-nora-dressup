#!/usr/bin/env python3
"""Create a deterministic sample SQLite database for item name similarity checks."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SAMPLE_DB_PATH = Path(__file__).parent / "item_similarity_sample.db"

ITEM_ROWS = [
    (1, "Red Ball Cap", 1),
    (2, "Red Baseball Cap", 1),
    (3, "Blue Shirt", 1),
    (4, "Blue T-Shirt", 1),
    (5, "Green Dress", 1),
    (6, "Yellow Boots", 1),
    (7, "Yellow Boot", 1),
    (8, "Kitchen Table", 1),
]


def main() -> int:
    if SAMPLE_DB_PATH.exists():
        SAMPLE_DB_PATH.unlink()

    connection = sqlite3.connect(SAMPLE_DB_PATH)
    try:
        connection.execute(
            """
            CREATE TABLE items (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        connection.executemany(
            "INSERT INTO items (id, name, is_active) VALUES (?, ?, ?)",
            ITEM_ROWS,
        )
        connection.commit()
    finally:
        connection.close()

    print(f"Created sample DB at {SAMPLE_DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
