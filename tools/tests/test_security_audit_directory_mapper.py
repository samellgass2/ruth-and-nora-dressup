#!/usr/bin/env python3
"""Acceptance checks for security-audit directory structure mapping."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.security_audit.directory_structure_mapper import (
    DirectoryMapperOptions,
    map_directory_structure,
    render_tree_text,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_TOOL = REPO_ROOT / "tools" / "security_audit" / "map_directory_structure.py"


class DirectoryStructureMapperTests(unittest.TestCase):
    def test_maps_expected_structure_for_temp_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs" / "README.md").write_text("# docs\n", encoding="utf-8")
            (root / "package.json").write_text("{}\n", encoding="utf-8")

            directory_map = map_directory_structure(root)

            self.assertEqual(directory_map.total_directories, 2)
            self.assertEqual(directory_map.total_files, 3)

            entries = directory_map.to_dict()["entries"]
            self.assertEqual(
                [entry["name"] for entry in entries],
                ["docs", "src", "package.json"],
            )

            docs_entry = entries[0]
            src_entry = entries[1]

            self.assertEqual(docs_entry["children"][0]["name"], "README.md")
            self.assertEqual(src_entry["children"][0]["name"], "app.py")

    def test_hidden_and_excluded_directories_are_skipped_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".git").mkdir()
            (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "left-pad.js").write_text("module\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "main.ts").write_text("console.log('hi')\n", encoding="utf-8")

            directory_map = map_directory_structure(root)
            names = [entry.name for entry in directory_map.entries]

            self.assertEqual(names, ["src"])
            self.assertEqual(directory_map.total_directories, 1)
            self.assertEqual(directory_map.total_files, 1)

    def test_max_depth_limits_recursion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a").mkdir()
            (root / "a" / "b").mkdir()
            (root / "a" / "b" / "c.txt").write_text("data\n", encoding="utf-8")

            directory_map = map_directory_structure(
                root,
                DirectoryMapperOptions(max_depth=0),
            )

            self.assertEqual(directory_map.total_directories, 1)
            self.assertEqual(directory_map.total_files, 0)
            self.assertEqual(directory_map.entries[0].name, "a")
            self.assertEqual(directory_map.entries[0].children, ())

    def test_tree_rendering_contains_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "config").mkdir()
            (root / "config" / "settings.yml").write_text("a: 1\n", encoding="utf-8")

            directory_map = map_directory_structure(root)
            tree = render_tree_text(directory_map)

            self.assertIn("Directories: 1", tree)
            self.assertIn("Files: 1", tree)
            self.assertIn("config/", tree)
            self.assertIn("settings.yml", tree)

    def test_cli_json_output_for_repository_root_matches_expected_entries(self) -> None:
        result = subprocess.run(
            [
                "python3",
                str(CLI_TOOL),
                "--root",
                str(REPO_ROOT),
                "--json",
                "--max-depth",
                "0",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)

        top_level_names = [entry["name"] for entry in payload["entries"]]
        expected = {
            "DESIGN.md",
            "LICENSE",
            "README.md",
            "STATUS.md",
            "TASK_REPORT.md",
            "index.html",
            "package-lock.json",
            "package.json",
            "public",
            "scripts",
            "src",
            "styles.css",
            "tools",
            "tsconfig.json",
            "vite.config.ts",
        }

        self.assertEqual(set(top_level_names), expected)


if __name__ == "__main__":
    unittest.main()
