#!/usr/bin/env python3
"""Acceptance checks for tools/find_similar_item_names.py."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CREATE_DB = REPO_ROOT / "tools" / "samples" / "create_item_similarity_sample_db.py"
TOOL = REPO_ROOT / "tools" / "find_similar_item_names.py"
CONFIG = REPO_ROOT / "tools" / "samples" / "item_similarity_sample_config.json"

EXPECTED_PAIR_NAMES = {
    frozenset(("Red Ball Cap", "Red Baseball Cap")),
    frozenset(("Blue Shirt", "Blue T-Shirt")),
    frozenset(("Yellow Boots", "Yellow Boot")),
}


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class ItemNameSimilarityToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        create = run(["python3", str(CREATE_DB)])
        if create.returncode != 0:
            raise RuntimeError(
                "Failed to create sample database:\n"
                f"stdout:\n{create.stdout}\n"
                f"stderr:\n{create.stderr}"
            )

    def test_similarity_returns_expected_pairs(self) -> None:
        result = run(["python3", str(TOOL), "--config", str(CONFIG), "--json"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        payload = json.loads(result.stdout)
        output_pairs = {
            frozenset((pair["left"]["name"], pair["right"]["name"]))
            for pair in payload["pairs"]
        }

        missing_pairs = EXPECTED_PAIR_NAMES - output_pairs
        self.assertFalse(
            missing_pairs,
            msg=f"Missing expected similar pairs: {sorted([tuple(p) for p in missing_pairs])}",
        )
        self.assertGreaterEqual(payload["pair_count"], len(EXPECTED_PAIR_NAMES))

    def test_missing_config_fails_with_expected_exit_code(self) -> None:
        missing = REPO_ROOT / "tools" / "samples" / "does_not_exist.json"
        result = run(["python3", str(TOOL), "--config", str(missing)])

        self.assertEqual(result.returncode, 2)
        self.assertIn("Config file not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
