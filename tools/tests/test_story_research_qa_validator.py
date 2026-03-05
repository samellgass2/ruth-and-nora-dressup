#!/usr/bin/env python3
"""Acceptance checks for tools/validate_story_research_qa.py."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "validate_story_research_qa.py"
EVIDENCE = REPO_ROOT / "research" / "workflow-6-qa-evidence.json"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def load_evidence() -> dict[str, Any]:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


class StoryResearchQaValidatorTests(unittest.TestCase):
    def test_repository_evidence_passes(self) -> None:
        result = run(["python3", str(TOOL), "--evidence", str(EVIDENCE), "--json"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["errors"], [])

    def test_missing_openclaw_url_fails(self) -> None:
        evidence = load_evidence()
        openclaw = evidence["openclaw_coverage"]
        sources = openclaw["sources"]
        openclaw["sources"] = [source for source in sources if "openclaw" not in source["url"].lower()]

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(json.dumps(evidence))

        try:
            result = run(["python3", str(TOOL), "--evidence", str(temp_path), "--json"])
        finally:
            temp_path.unlink(missing_ok=True)

        self.assertEqual(result.returncode, 3)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "fail")
        self.assertIn(
            "openclaw_coverage.sources must include an OpenClaw URL",
            payload["errors"],
        )

    def test_unknown_evidence_reference_fails(self) -> None:
        evidence = load_evidence()
        evidence["qa_answers"][0]["evidence_ref_ids"] = ["unknown-source-id"]

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(json.dumps(evidence))

        try:
            result = run(["python3", str(TOOL), "--evidence", str(temp_path), "--json"])
        finally:
            temp_path.unlink(missing_ok=True)

        self.assertEqual(result.returncode, 3)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "fail")
        self.assertIn(
            "qa_answers[0] references unknown evidence id 'unknown-source-id'",
            payload["errors"],
        )


if __name__ == "__main__":
    unittest.main()
