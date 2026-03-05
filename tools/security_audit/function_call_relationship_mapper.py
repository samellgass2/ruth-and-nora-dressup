#!/usr/bin/env python3
"""Function call relationship mapper for security-audit workflows.

This module provides a callable API that parses Python files in a repository and
builds a deterministic map of which functions call which other functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import ast
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
class FunctionCallMapperOptions:
    """Configuration for function-call mapping behavior."""

    include_hidden: bool = False
    follow_symlinks: bool = False
    max_depth: int | None = None
    excluded_dir_names: frozenset[str] = frozenset(DEFAULT_EXCLUDED_DIRS)
    file_extensions: frozenset[str] = frozenset({".py"})


@dataclass(frozen=True)
class FunctionDefinition:
    """Single discovered function definition."""

    name: str
    qualified_name: str
    module: str
    file_path: str
    line: int

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "name": self.name,
            "qualified_name": self.qualified_name,
            "module": self.module,
            "file_path": self.file_path,
            "line": self.line,
        }


@dataclass(frozen=True)
class FunctionCallRelation:
    """Call relationship from one discovered function to another."""

    caller: str
    callee: str

    def to_dict(self) -> dict[str, str]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "caller": self.caller,
            "callee": self.callee,
        }


@dataclass(frozen=True)
class FunctionCallMap:
    """Top-level mapped function definitions and call relationships."""

    root: str
    scanned_files: int
    parsed_files: int
    function_count: int
    relation_count: int
    functions: tuple[FunctionDefinition, ...]
    relations: tuple[FunctionCallRelation, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convert the map payload to a JSON-serializable dictionary."""
        return {
            "root": self.root,
            "scanned_files": self.scanned_files,
            "parsed_files": self.parsed_files,
            "function_count": self.function_count,
            "relation_count": self.relation_count,
            "functions": [function.to_dict() for function in self.functions],
            "relations": [relation.to_dict() for relation in self.relations],
        }

    def to_json(self, indent: int = 2) -> str:
        """Render function-call map as JSON text."""
        return json.dumps(self.to_dict(), indent=indent)


class DirectoryAccessError(RuntimeError):
    """Raised when the mapper cannot access a directory entry."""

    def __init__(self, path: Path, cause: OSError) -> None:
        self.path = path
        self.cause = cause
        super().__init__(f"Unable to access '{path}': {cause}")


class FileParseError(RuntimeError):
    """Raised when the mapper cannot parse a file."""

    def __init__(self, path: Path, cause: SyntaxError) -> None:
        self.path = path
        self.cause = cause
        super().__init__(
            f"Unable to parse '{path}': {cause.msg} (line {cause.lineno})"
        )


@dataclass(frozen=True)
class _FunctionRecord:
    """Internal per-function metadata used during traversal."""

    qualified_name: str
    name: str
    line: int
    calls: tuple[str, ...]


class _FunctionCollector(ast.NodeVisitor):
    """Collect functions and unresolved call names from a module AST."""

    def __init__(self) -> None:
        self._scope_stack: list[str] = []
        self.records: list[_FunctionRecord] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        return self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        return self._visit_function(node)

    def _visit_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        self._scope_stack.append(node.name)
        collector = _CallCollector()
        for statement in node.body:
            collector.visit(statement)

        self.records.append(
            _FunctionRecord(
                qualified_name=".".join(self._scope_stack),
                name=node.name,
                line=node.lineno,
                calls=tuple(sorted(collector.calls)),
            )
        )

        for statement in node.body:
            self.visit(statement)

        self._scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        self._scope_stack.append(node.name)
        for statement in node.body:
            self.visit(statement)
        self._scope_stack.pop()
        return None


class _CallCollector(ast.NodeVisitor):
    """Collect unresolved callable names used inside a function body."""

    def __init__(self) -> None:
        self.calls: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        return None

    def visit_Lambda(self, node: ast.Lambda) -> Any:
        self.generic_visit(node.body)
        return None

    def visit_Call(self, node: ast.Call) -> Any:
        resolved_name = _extract_call_name(node.func)
        if resolved_name is not None:
            self.calls.add(resolved_name)
        self.generic_visit(node)
        return None


def map_function_call_relationships(
    root: Path,
    options: FunctionCallMapperOptions | None = None,
) -> FunctionCallMap:
    """Build a deterministic function-call relationship map for Python code.

    Args:
        root: Path to repository (or subdirectory) that should be scanned.
        options: Optional scan/mapping options.

    Returns:
        A structured map of discovered function definitions and call relations.

    Raises:
        ValueError: If ``root`` does not exist or is not a directory.
        DirectoryAccessError: If a directory entry cannot be accessed.
        FileParseError: If any scanned file cannot be parsed as Python code.
    """
    effective_options = options or FunctionCallMapperOptions()
    resolved_root = root.resolve()

    if not resolved_root.exists():
        raise ValueError(f"Root path does not exist: {resolved_root}")
    if not resolved_root.is_dir():
        raise ValueError(f"Root path is not a directory: {resolved_root}")

    files = _collect_target_files(resolved_root, effective_options)

    functions: list[FunctionDefinition] = []
    relations: set[tuple[str, str]] = set()

    parsed_files = 0
    for file_path in files:
        module = _path_to_module_name(root=resolved_root, file_path=file_path)
        source_text = file_path.read_text(encoding="utf-8")

        try:
            module_tree = ast.parse(source_text, filename=str(file_path))
        except SyntaxError as error:
            raise FileParseError(file_path, error) from error

        parsed_files += 1
        collector = _FunctionCollector()
        collector.visit(module_tree)

        # Name-to-qualified mapping is intentionally local to each module,
        # avoiding ambiguous cross-module best-effort linking.
        module_symbols: dict[str, list[str]] = {}
        for record in collector.records:
            local_qualified_name = f"{module}.{record.qualified_name}"
            module_symbols.setdefault(record.name, []).append(local_qualified_name)
            functions.append(
                FunctionDefinition(
                    name=record.name,
                    qualified_name=local_qualified_name,
                    module=module,
                    file_path=str(file_path.relative_to(resolved_root)),
                    line=record.line,
                )
            )

        for record in collector.records:
            caller = f"{module}.{record.qualified_name}"
            for call_name in record.calls:
                for target in module_symbols.get(call_name, []):
                    relations.add((caller, target))

    sorted_functions = tuple(
        sorted(
            functions,
            key=lambda function: (
                function.qualified_name,
                function.file_path,
                function.line,
            ),
        )
    )
    sorted_relations = tuple(
        FunctionCallRelation(caller=caller, callee=callee)
        for caller, callee in sorted(relations)
    )

    return FunctionCallMap(
        root=str(resolved_root),
        scanned_files=len(files),
        parsed_files=parsed_files,
        function_count=len(sorted_functions),
        relation_count=len(sorted_relations),
        functions=sorted_functions,
        relations=sorted_relations,
    )


def _collect_target_files(root: Path, options: FunctionCallMapperOptions) -> list[Path]:
    collected: list[Path] = []

    def _walk_directory(current: Path, depth: int) -> None:
        try:
            entries = sorted(current.iterdir(), key=lambda path: (path.name.lower(), path.name))
        except OSError as error:
            raise DirectoryAccessError(current, error) from error

        for entry in entries:
            if not _should_include_entry(entry=entry, is_root=entry == root, options=options):
                continue

            try:
                is_symlink = entry.is_symlink()
            except OSError as error:
                raise DirectoryAccessError(entry, error) from error

            if entry.is_dir() and (options.follow_symlinks or not is_symlink):
                if options.max_depth is not None and depth >= options.max_depth:
                    continue
                _walk_directory(entry, depth + 1)
                continue

            if entry.suffix in options.file_extensions:
                collected.append(entry)

    _walk_directory(root, 0)
    return collected


def _should_include_entry(
    *,
    entry: Path,
    is_root: bool,
    options: FunctionCallMapperOptions,
) -> bool:
    if is_root:
        return True

    name = entry.name

    if not options.include_hidden and name.startswith("."):
        return False

    if entry.is_dir() and name in options.excluded_dir_names:
        return False

    return True


def _path_to_module_name(*, root: Path, file_path: Path) -> str:
    relative = file_path.relative_to(root)
    parts = list(relative.parts)

    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]

    if parts[-1] == "__init__":
        parts = parts[:-1]

    filtered = [part for part in parts if part]
    if not filtered:
        return "<root>"
    return ".".join(filtered)


def _extract_call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    return None


def render_call_map_text(function_call_map: FunctionCallMap) -> str:
    """Render a human-readable function-call relationship map."""
    lines = [f"Root: {function_call_map.root}"]
    lines.append(f"Scanned files: {function_call_map.scanned_files}")
    lines.append(f"Parsed files: {function_call_map.parsed_files}")
    lines.append(f"Functions: {function_call_map.function_count}")
    lines.append(f"Relations: {function_call_map.relation_count}")
    lines.append("")
    lines.append("Call relationships:")

    if not function_call_map.relations:
        lines.append("  (none)")
    else:
        for relation in function_call_map.relations:
            lines.append(f"  {relation.caller} -> {relation.callee}")

    return "\n".join(lines)
