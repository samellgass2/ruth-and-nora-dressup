#!/usr/bin/env python3
"""CLI wrapper for directory structure mapping utility."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.security_audit.directory_structure_mapper import (  # noqa: E402
    DirectoryAccessError,
    DirectoryMapperOptions,
    map_directory_structure,
    render_tree_text,
)

ARGUMENT_ERROR_EXIT_CODE = 2
ACCESS_ERROR_EXIT_CODE = 3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Map and print the directory structure for a target path."
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
        help="Print machine-readable JSON output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.max_depth is not None and args.max_depth < 0:
        print("ERROR: --max-depth must be 0 or greater", file=sys.stderr)
        return ARGUMENT_ERROR_EXIT_CODE

    root = Path(args.root)
    options = DirectoryMapperOptions(
        include_hidden=bool(args.include_hidden),
        follow_symlinks=bool(args.follow_symlinks),
        max_depth=args.max_depth,
    )

    try:
        directory_map = map_directory_structure(root, options)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return ARGUMENT_ERROR_EXIT_CODE
    except DirectoryAccessError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return ACCESS_ERROR_EXIT_CODE

    if args.json:
        print(directory_map.to_json())
    else:
        print(render_tree_text(directory_map))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
