#!/usr/bin/env python3
"""Acceptance checks for tools/generate_db_column_map.py."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CREATE_DB = REPO_ROOT / "tools" / "samples" / "create_item_similarity_sample_db.py"
TOOL = REPO_ROOT / "tools" / "generate_db_column_map.py"
DB_PATH = REPO_ROOT / "tools" / "samples" / "item_similarity_sample.db"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class DbColumnMapToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        create = run(["python3", str(CREATE_DB)])
        if create.returncode != 0:
            raise RuntimeError(
                "Failed to create sample database:\n"
                f"stdout:\n{create.stdout}\n"
                f"stderr:\n{create.stderr}"
            )

    def test_value_counts_returns_expected_map(self) -> None:
        result = run(
            [
                "python3",
                str(TOOL),
                "--database",
                str(DB_PATH),
                "--table",
                "items",
                "--column",
                "is_active",
                "--operation",
                "value_counts",
                "--json",
            ]
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["operation"], "value_counts")
        self.assertEqual(payload["result"], {"1": 8})

    def test_count_operation_returns_expected_value(self) -> None:
        result = run(
            [
                "python3",
                str(TOOL),
                "--database",
                str(DB_PATH),
                "--table",
                "items",
                "--column",
                "name",
                "--operation",
                "count",
                "--json",
            ]
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["result"], {"count": 8})

    def test_invalid_operation_fails(self) -> None:
        result = run(
            [
                "python3",
                str(TOOL),
                "--database",
                str(DB_PATH),
                "--table",
                "items",
                "--column",
                "id",
                "--operation",
                "median",
            ]
        )

        self.assertEqual(result.returncode, 5)
        self.assertIn("Unsupported operation", result.stderr)


if __name__ == "__main__":
    unittest.main()
