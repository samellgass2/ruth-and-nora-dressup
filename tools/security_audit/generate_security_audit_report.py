#!/usr/bin/env python3
"""CLI wrapper for security audit report generation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.security_audit.directory_structure_mapper import DirectoryAccessError  # noqa: E402
from tools.security_audit.function_call_relationship_mapper import FileParseError  # noqa: E402
from tools.security_audit.security_audit_report_generator import (  # noqa: E402
    SecurityAuditReportOptions,
    generate_security_audit_report,
)

ARGUMENT_ERROR_EXIT_CODE = 2
ACCESS_ERROR_EXIT_CODE = 3
PARSE_ERROR_EXIT_CODE = 4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a security audit report from repo mappings.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Root directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files and directories.",
    )
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Follow symbolic links that point to directories.",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Limit recursion depth (0 means top-level only).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output instead of Markdown.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output file path to write generated report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.max_depth is not None and args.max_depth < 0:
        print("ERROR: --max-depth must be 0 or greater", file=sys.stderr)
        return ARGUMENT_ERROR_EXIT_CODE

    options = SecurityAuditReportOptions(
        include_hidden=bool(args.include_hidden),
        follow_symlinks=bool(args.follow_symlinks),
        max_depth=args.max_depth,
    )

    try:
        report = generate_security_audit_report(Path(args.root), options)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return ARGUMENT_ERROR_EXIT_CODE
    except DirectoryAccessError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return ACCESS_ERROR_EXIT_CODE
    except FileParseError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return PARSE_ERROR_EXIT_CODE

    rendered = report.to_json() if args.json else report.to_markdown()
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
