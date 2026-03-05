#!/usr/bin/env python3
"""Acceptance checks for tools/find_similar_item_names.py."""

from __future__ import annotations

import json
import subprocess
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


def main() -> int:
    create = run(["python3", str(CREATE_DB)])
    if create.returncode != 0:
        print(create.stdout)
        print(create.stderr)
        raise SystemExit("Failed to create sample database")

    result = run(["python3", str(TOOL), "--config", str(CONFIG), "--json"])
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise SystemExit("Similarity tool failed for sample config")

    payload = json.loads(result.stdout)
    output_pairs = {
        frozenset((pair["left"]["name"], pair["right"]["name"]))
        for pair in payload["pairs"]
    }

    missing_pairs = EXPECTED_PAIR_NAMES - output_pairs
    if missing_pairs:
        raise SystemExit(f"Missing expected similar pairs: {sorted([tuple(p) for p in missing_pairs])}")

    if payload["pair_count"] < len(EXPECTED_PAIR_NAMES):
        raise SystemExit(
            f"Expected at least {len(EXPECTED_PAIR_NAMES)} pairs, got {payload['pair_count']}"
        )

    print("Acceptance check passed: expected similar records were returned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
