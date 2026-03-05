#!/usr/bin/env python3
"""Run tools Python test suite using unittest discovery."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    tools_tests = repo_root / "tools" / "tests"

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(tools_tests), pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
