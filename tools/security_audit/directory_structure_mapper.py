#!/usr/bin/env python3
"""Directory structure mapping utility for security-audit workflows.

This module provides a callable API for building a deterministic map of a codebase
and optional rendering helpers for text-tree and JSON output.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any

DEFAULT_EXCLUDED_DIRS = {
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
}


@dataclass(frozen=True)
class DirectoryMapperOptions:
    """Configuration for directory mapping behavior."""

    include_hidden: bool = False
    follow_symlinks: bool = False
    max_depth: int | None = None
    excluded_dir_names: frozenset[str] = frozenset(DEFAULT_EXCLUDED_DIRS)


@dataclass(frozen=True)
class StructureEntry:
    """A single file-system entry in the directory map."""

    name: str
    relative_path: str
    is_directory: bool
    children: tuple["StructureEntry", ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Convert the entry to a JSON-serializable dictionary."""
        return {
            "name": self.name,
            "relative_path": self.relative_path,
            "kind": "directory" if self.is_directory else "file",
            "children": [child.to_dict() for child in self.children],
        }


@dataclass(frozen=True)
class DirectoryStructureMap:
    """Top-level mapped directory structure and summary metadata."""

    root: str
    total_directories: int
    total_files: int
    entries: tuple[StructureEntry, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convert the map payload to a JSON-serializable dictionary."""
        return {
            "root": self.root,
            "total_directories": self.total_directories,
            "total_files": self.total_files,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    def to_json(self, indent: int = 2) -> str:
        """Render the directory map as JSON text."""
        return json.dumps(self.to_dict(), indent=indent)


@dataclass(frozen=True)
class _TraversalCounts:
    """Internal counters returned from recursive traversal."""

    directories: int
    files: int


class DirectoryAccessError(RuntimeError):
    """Raised when the mapper cannot access a directory entry."""

    def __init__(self, path: Path, cause: OSError) -> None:
        self.path = path
        self.cause = cause
        super().__init__(f"Unable to access '{path}': {cause}")


def map_directory_structure(
    root: Path,
    options: DirectoryMapperOptions | None = None,
) -> DirectoryStructureMap:
    """Map the directory tree rooted at ``root``.

    Args:
        root: Path to directory that should be traversed.
        options: Optional traversal options.

    Returns:
        A structured, deterministic representation of the directory layout.

    Raises:
        ValueError: If ``root`` does not exist or is not a directory.
        DirectoryAccessError: If an entry cannot be read due to I/O issues.
    """
    effective_options = options or DirectoryMapperOptions()
    resolved_root = root.resolve()

    if not resolved_root.exists():
        raise ValueError(f"Root path does not exist: {resolved_root}")
    if not resolved_root.is_dir():
        raise ValueError(f"Root path is not a directory: {resolved_root}")

    entries, counts = _walk_directory(
        root=resolved_root,
        current=resolved_root,
        depth=0,
        options=effective_options,
    )

    return DirectoryStructureMap(
        root=str(resolved_root),
        total_directories=counts.directories,
        total_files=counts.files,
        entries=entries,
    )


def _walk_directory(
    *,
    root: Path,
    current: Path,
    depth: int,
    options: DirectoryMapperOptions,
) -> tuple[tuple[StructureEntry, ...], _TraversalCounts]:
    try:
        all_entries = list(current.iterdir())
    except OSError as error:
        raise DirectoryAccessError(current, error) from error

    filtered = [
        entry
        for entry in all_entries
        if _should_include_entry(entry=entry, is_root=entry == root, options=options)
    ]

    # Keep output deterministic: directories first, then files, both alphabetical.
    filtered.sort(key=lambda path: (not path.is_dir(), path.name.lower(), path.name))

    mapped_entries: list[StructureEntry] = []
    directory_count = 0
    file_count = 0

    for entry in filtered:
        entry_relative = str(entry.relative_to(root))

        try:
            is_symlink = entry.is_symlink()
        except OSError as error:
            raise DirectoryAccessError(entry, error) from error

        if entry.is_dir() and (options.follow_symlinks or not is_symlink):
            if options.max_depth is not None and depth >= options.max_depth:
                mapped_entries.append(
                    StructureEntry(
                        name=entry.name,
                        relative_path=entry_relative,
                        is_directory=True,
                        children=(),
                    )
                )
                directory_count += 1
                continue

            children, child_counts = _walk_directory(
                root=root,
                current=entry,
                depth=depth + 1,
                options=options,
            )
            mapped_entries.append(
                StructureEntry(
                    name=entry.name,
                    relative_path=entry_relative,
                    is_directory=True,
                    children=children,
                )
            )
            directory_count += 1 + child_counts.directories
            file_count += child_counts.files
            continue

        mapped_entries.append(
            StructureEntry(
                name=entry.name,
                relative_path=entry_relative,
                is_directory=False,
                children=(),
            )
        )
        file_count += 1

    return tuple(mapped_entries), _TraversalCounts(
        directories=directory_count,
        files=file_count,
    )


def _should_include_entry(
    *,
    entry: Path,
    is_root: bool,
    options: DirectoryMapperOptions,
) -> bool:
    if is_root:
        return True

    name = entry.name

    if not options.include_hidden and name.startswith("."):
        return False

    if entry.is_dir() and name in options.excluded_dir_names:
        return False

    return True


def render_tree_text(directory_map: DirectoryStructureMap) -> str:
    """Render a human-readable tree representation."""
    root_name = Path(directory_map.root).name or directory_map.root
    lines = [root_name]

    for index, entry in enumerate(directory_map.entries):
        is_last = index == len(directory_map.entries) - 1
        _append_tree_lines(
            lines=lines,
            entry=entry,
            prefix="",
            is_last=is_last,
        )

    lines.append("")
    lines.append(f"Directories: {directory_map.total_directories}")
    lines.append(f"Files: {directory_map.total_files}")
    return "\n".join(lines)


def _append_tree_lines(
    *,
    lines: list[str],
    entry: StructureEntry,
    prefix: str,
    is_last: bool,
) -> None:
    branch = "└── " if is_last else "├── "
    suffix = "/" if entry.is_directory else ""
    lines.append(f"{prefix}{branch}{entry.name}{suffix}")

    if not entry.children:
        return

    child_prefix = f"{prefix}{'    ' if is_last else '│   '}"
    for child_index, child in enumerate(entry.children):
        child_is_last = child_index == len(entry.children) - 1
        _append_tree_lines(
            lines=lines,
            entry=child,
            prefix=child_prefix,
            is_last=child_is_last,
        )
