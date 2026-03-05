#!/usr/bin/env python3
"""Acceptance checks for security-audit function-call relationship mapping."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.security_audit.function_call_relationship_mapper import (
    FileParseError,
    FunctionCallMapperOptions,
    map_function_call_relationships,
    render_call_map_text,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_TOOL = REPO_ROOT / "tools" / "security_audit" / "map_function_calls.py"


class FunctionCallRelationshipMapperTests(unittest.TestCase):
    def test_maps_expected_function_relations_for_temp_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_file = root / "service.py"
            source_file.write_text(
                "\n".join(
                    [
                        "def helper():",
                        "    return 1",
                        "",
                        "def compute():",
                        "    helper()",
                        "    return helper()",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            call_map = map_function_call_relationships(root)

            self.assertEqual(call_map.scanned_files, 1)
            self.assertEqual(call_map.parsed_files, 1)
            self.assertEqual(call_map.function_count, 2)
            self.assertEqual(call_map.relation_count, 1)

            relations = call_map.to_dict()["relations"]
            self.assertEqual(
                relations,
                [
                    {
                        "caller": "service.compute",
                        "callee": "service.helper",
                    }
                ],
            )

    def test_maps_nested_functions_and_class_methods(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_file = root / "shapes.py"
            source_file.write_text(
                "\n".join(
                    [
                        "class Box:",
                        "    def area(self):",
                        "        return width()",
                        "",
                        "def width():",
                        "    return 2",
                        "",
                        "def outer():",
                        "    def inner():",
                        "        width()",
                        "        return 3",
                        "    return inner()",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            call_map = map_function_call_relationships(root)
            relation_pairs = {
                (entry["caller"], entry["callee"])
                for entry in call_map.to_dict()["relations"]
            }

            self.assertIn(("shapes.Box.area", "shapes.width"), relation_pairs)
            self.assertIn(("shapes.outer.inner", "shapes.width"), relation_pairs)
            self.assertIn(("shapes.outer", "shapes.outer.inner"), relation_pairs)

    def test_parse_failure_raises_file_parse_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "ok.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
            (root / "broken.py").write_text("def broken(:\n    return 1\n", encoding="utf-8")

            with self.assertRaises(FileParseError):
                map_function_call_relationships(root)

    def test_max_depth_filters_nested_python_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "top.py").write_text("def top():\n    return 1\n", encoding="utf-8")
            nested_dir = root / "pkg"
            nested_dir.mkdir()
            (nested_dir / "deep.py").write_text(
                "def deep():\n    return 2\n",
                encoding="utf-8",
            )

            call_map = map_function_call_relationships(
                root,
                FunctionCallMapperOptions(max_depth=0),
            )

            function_names = {entry.qualified_name for entry in call_map.functions}
            self.assertEqual(function_names, {"top.top"})
            self.assertEqual(call_map.scanned_files, 1)

    def test_render_text_contains_summary_and_relation_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.py").write_text(
                "def a():\n    return b()\n\ndef b():\n    return 1\n",
                encoding="utf-8",
            )

            call_map = map_function_call_relationships(root)
            output = render_call_map_text(call_map)

            self.assertIn("Scanned files: 1", output)
            self.assertIn("Parsed files: 1", output)
            self.assertIn("Functions: 2", output)
            self.assertIn("Relations: 1", output)
            self.assertIn("a.a -> a.b", output)

    def test_cli_json_output_for_repository_root(self) -> None:
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

        self.assertGreaterEqual(payload["scanned_files"], 0)
        self.assertGreaterEqual(payload["parsed_files"], 0)
        self.assertIn("functions", payload)
        self.assertIn("relations", payload)


if __name__ == "__main__":
    unittest.main()
