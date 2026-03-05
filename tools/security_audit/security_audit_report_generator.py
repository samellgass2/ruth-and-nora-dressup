#!/usr/bin/env python3
"""Security audit report generator for repository risk review workflows.

This module combines directory and function-call mapping outputs with focused
static checks to produce a deterministic Markdown and JSON security report.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from tools.security_audit.directory_structure_mapper import (
    DirectoryMapperOptions,
    DirectoryStructureMap,
    StructureEntry,
    map_directory_structure,
)
from tools.security_audit.function_call_relationship_mapper import (
    FunctionCallMap,
    FunctionCallMapperOptions,
    map_function_call_relationships,
)


@dataclass(frozen=True)
class SecurityAuditReportOptions:
    """Configuration for security-audit report generation."""

    include_hidden: bool = False
    follow_symlinks: bool = False
    max_depth: int | None = None


@dataclass(frozen=True)
class SecurityAuditFinding:
    """Single security-audit finding with actionable remediation guidance."""

    finding_id: str
    severity: str
    title: str
    description: str
    evidence: tuple[str, ...]
    related_files: tuple[str, ...]
    related_functions: tuple[str, ...]
    recommended_fixes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convert finding to JSON-serializable form."""
        return {
            "finding_id": self.finding_id,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "evidence": list(self.evidence),
            "related_files": list(self.related_files),
            "related_functions": list(self.related_functions),
            "recommended_fixes": list(self.recommended_fixes),
        }


@dataclass(frozen=True)
class SecurityAuditSummary:
    """Top-level summary metrics for the generated report."""

    directory_count: int
    file_count: int
    python_file_count: int
    discovered_function_count: int
    discovered_relation_count: int
    high_findings: int
    medium_findings: int
    low_findings: int

    def to_dict(self) -> dict[str, int]:
        """Convert summary to JSON-serializable form."""
        return {
            "directory_count": self.directory_count,
            "file_count": self.file_count,
            "python_file_count": self.python_file_count,
            "discovered_function_count": self.discovered_function_count,
            "discovered_relation_count": self.discovered_relation_count,
            "high_findings": self.high_findings,
            "medium_findings": self.medium_findings,
            "low_findings": self.low_findings,
        }


@dataclass(frozen=True)
class SecurityAuditReport:
    """Generated security-audit report payload."""

    root: str
    generated_at: str
    summary: SecurityAuditSummary
    findings: tuple[SecurityAuditFinding, ...]

    def to_dict(self) -> dict[str, Any]:
        """Convert report to JSON-serializable form."""
        return {
            "root": self.root,
            "generated_at": self.generated_at,
            "summary": self.summary.to_dict(),
            "findings": [finding.to_dict() for finding in self.findings],
        }

    def to_json(self, indent: int = 2) -> str:
        """Render report as JSON text."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_markdown(self) -> str:
        """Render report as Markdown text suitable for STATUS artifacts."""
        lines: list[str] = []
        lines.append("# Security Audit Report")
        lines.append("")
        lines.append(f"Root: `{self.root}`")
        lines.append(f"Generated: `{self.generated_at}`")
        lines.append("")
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Directories scanned: {self.summary.directory_count}")
        lines.append(f"- Files scanned: {self.summary.file_count}")
        lines.append(f"- Python files scanned: {self.summary.python_file_count}")
        lines.append(
            f"- Functions discovered: {self.summary.discovered_function_count}"
        )
        lines.append(
            f"- Intra-module call relations discovered: "
            f"{self.summary.discovered_relation_count}"
        )
        lines.append(f"- High findings: {self.summary.high_findings}")
        lines.append(f"- Medium findings: {self.summary.medium_findings}")
        lines.append(f"- Low findings: {self.summary.low_findings}")
        lines.append("")
        lines.append("## Findings")
        lines.append("")

        if not self.findings:
            lines.append("No findings detected by the current rule set.")
            return "\n".join(lines) + "\n"

        for finding in self.findings:
            lines.append(
                f"### {finding.finding_id} [{finding.severity}] {finding.title}"
            )
            lines.append("")
            lines.append(finding.description)
            lines.append("")
            lines.append("Evidence:")
            for evidence_line in finding.evidence:
                lines.append(f"- {evidence_line}")
            lines.append("Related files:")
            for file_path in finding.related_files:
                lines.append(f"- `{file_path}`")
            lines.append("Related functions:")
            for function_name in finding.related_functions:
                lines.append(f"- `{function_name}`")
            lines.append("Recommended fixes:")
            for fix in finding.recommended_fixes:
                lines.append(f"- {fix}")
            lines.append("")

        return "\n".join(lines)


def generate_security_audit_report(
    root: Path,
    options: SecurityAuditReportOptions | None = None,
) -> SecurityAuditReport:
    """Generate a deterministic security audit report for ``root``."""
    effective_options = options or SecurityAuditReportOptions()
    dir_options = DirectoryMapperOptions(
        include_hidden=effective_options.include_hidden,
        follow_symlinks=effective_options.follow_symlinks,
        max_depth=effective_options.max_depth,
    )
    call_options = FunctionCallMapperOptions(
        include_hidden=effective_options.include_hidden,
        follow_symlinks=effective_options.follow_symlinks,
        max_depth=effective_options.max_depth,
    )

    directory_map = map_directory_structure(root, dir_options)
    function_map = map_function_call_relationships(root, call_options)

    python_files = _collect_python_files(directory_map)
    supplemental_files = [
        "tools/ai_news_crawler/requirements.txt",
        "tools/security_audit/requirements.txt",
        "tools/ai_news_crawler/sources.json",
    ]
    file_text_by_path = _read_selected_file_texts(
        root=Path(directory_map.root),
        paths=python_files + supplemental_files,
    )
    findings = _build_findings(function_map=function_map, file_text_by_path=file_text_by_path)
    findings = tuple(sorted(findings, key=_finding_sort_key))

    high_count = sum(1 for finding in findings if finding.severity == "HIGH")
    medium_count = sum(1 for finding in findings if finding.severity == "MEDIUM")
    low_count = sum(1 for finding in findings if finding.severity == "LOW")

    summary = SecurityAuditSummary(
        directory_count=directory_map.total_directories,
        file_count=directory_map.total_files,
        python_file_count=len(python_files),
        discovered_function_count=function_map.function_count,
        discovered_relation_count=function_map.relation_count,
        high_findings=high_count,
        medium_findings=medium_count,
        low_findings=low_count,
    )

    generated_at = datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()

    return SecurityAuditReport(
        root=directory_map.root,
        generated_at=generated_at,
        summary=summary,
        findings=findings,
    )


def _collect_python_files(directory_map: DirectoryStructureMap) -> list[str]:
    python_files: list[str] = []

    def _walk(entries: tuple[StructureEntry, ...]) -> None:
        for entry in entries:
            if entry.is_directory:
                _walk(entry.children)
            elif entry.relative_path.endswith(".py"):
                python_files.append(entry.relative_path)

    _walk(directory_map.entries)
    python_files.sort()
    return python_files


def _read_selected_file_texts(*, root: Path, paths: list[str]) -> dict[str, str]:
    contents: dict[str, str] = {}
    unique_paths = sorted(set(paths))
    for relative_path in unique_paths:
        file_path = root / relative_path
        try:
            contents[relative_path] = file_path.read_text(encoding="utf-8")
        except OSError:
            # If a file becomes unavailable mid-scan, skip it and keep report generation stable.
            continue
    return contents


def _build_findings(
    *,
    function_map: FunctionCallMap,
    file_text_by_path: dict[str, str],
) -> list[SecurityAuditFinding]:
    finding_list: list[SecurityAuditFinding] = []
    function_names = {entry.qualified_name for entry in function_map.functions}

    ssrf_finding = _detect_unrestricted_source_url_fetch(function_names, file_text_by_path)
    if ssrf_finding is not None:
        finding_list.append(ssrf_finding)

    newsletter_finding = _detect_unvalidated_newsletter_link_schemes(
        function_names,
        file_text_by_path,
    )
    if newsletter_finding is not None:
        finding_list.append(newsletter_finding)

    dependency_finding = _detect_unpinned_hash_requirements(file_text_by_path)
    if dependency_finding is not None:
        finding_list.append(dependency_finding)

    return finding_list


def _detect_unrestricted_source_url_fetch(
    function_names: set[str],
    file_text_by_path: dict[str, str],
) -> SecurityAuditFinding | None:
    retriever_file = "tools/ai_news_crawler/article_retriever.py"
    retriever_text = file_text_by_path.get(retriever_file)
    if retriever_text is None:
        return None

    required_functions = {
        "tools.ai_news_crawler.article_retriever.parse_source_definitions",
        "tools.ai_news_crawler.article_retriever.UrllibFetcher.fetch_text",
    }
    has_required_functions = required_functions.issubset(function_names)
    has_open_fetch = "urlopen(request, timeout=self._timeout_seconds)" in retriever_text
    lacks_url_validation = "urlparse(" not in retriever_text

    if not (has_required_functions and has_open_fetch and lacks_url_validation):
        return None

    return SecurityAuditFinding(
        finding_id="SA-001",
        severity="HIGH",
        title="Unrestricted URL fetching from configuration",
        description=(
            "Source URLs are accepted from JSON config and fetched without scheme "
            "or host allowlisting. If config is attacker-influenced, the crawler "
            "can be used for SSRF or internal network probing."
        ),
        evidence=(
            "`parse_source_definitions` accepts any non-empty URL string.",
            "`UrllibFetcher.fetch_text` performs direct `urlopen` on that URL.",
            "No `urlparse`-based scheme/host validation is present in the retriever.",
        ),
        related_files=(retriever_file, "tools/ai_news_crawler/sources.json"),
        related_functions=tuple(sorted(required_functions)),
        recommended_fixes=(
            "Validate source URLs with `urllib.parse.urlparse` and reject non-`https` schemes.",
            "Add an allowlist of approved hostnames for production source configs.",
            "Block loopback/private-network targets by resolving and checking IP ranges.",
            "Add unit tests covering rejected schemes such as `file://`, `ftp://`, and local IP hosts.",
        ),
    )


def _detect_unvalidated_newsletter_link_schemes(
    function_names: set[str],
    file_text_by_path: dict[str, str],
) -> SecurityAuditFinding | None:
    retriever_file = "tools/ai_news_crawler/article_retriever.py"
    summarizer_file = "tools/ai_news_crawler/newsletter_summarizer.py"
    retriever_text = file_text_by_path.get(retriever_file)
    summarizer_text = file_text_by_path.get(summarizer_file)

    if retriever_text is None or summarizer_text is None:
        return None

    required_functions = {
        "tools.ai_news_crawler.article_retriever.parse_html_headlines",
        "tools.ai_news_crawler.newsletter_summarizer.render_newsletter_html",
    }
    has_required_functions = required_functions.issubset(function_names)
    stores_raw_href = "url=href" in retriever_text or "'url': href" in retriever_text
    renders_anchor_href = "<a href" in summarizer_text and "{safe_url}" in summarizer_text
    lacks_scheme_filter = "javascript:" not in summarizer_text and "urlparse(" not in summarizer_text

    if not (has_required_functions and stores_raw_href and renders_anchor_href and lacks_scheme_filter):
        return None

    return SecurityAuditFinding(
        finding_id="SA-002",
        severity="MEDIUM",
        title="Newsletter links are rendered without URL scheme filtering",
        description=(
            "HTML headline extraction preserves arbitrary anchor URLs, which are later "
            "rendered as clickable links in newsletter output. Escaping prevents HTML "
            "injection, but it does not block unsafe schemes like `javascript:`."
        ),
        evidence=(
            "`parse_html_headlines` stores `href` values directly as article URLs.",
            "`render_newsletter_html` emits those URLs into `<a href=...>` links.",
            "No scheme validation exists before rendering newsletter anchors.",
        ),
        related_files=(retriever_file, summarizer_file),
        related_functions=tuple(sorted(required_functions)),
        recommended_fixes=(
            "Normalize and validate article URLs before persistence and rendering.",
            "Allow only `https` and `http` schemes; reject `javascript:`, `data:`, and empty hosts.",
            "Add tests to ensure malicious schemes are dropped or replaced with safe placeholders.",
        ),
    )


def _detect_unpinned_hash_requirements(
    file_text_by_path: dict[str, str],
) -> SecurityAuditFinding | None:
    setup_files = [
        "tools/setup_ai_news_env.py",
        "tools/setup_security_audit_env.py",
    ]
    requirements_files = [
        "tools/ai_news_crawler/requirements.txt",
        "tools/security_audit/requirements.txt",
    ]

    present_setup_files = [path for path in setup_files if path in file_text_by_path]
    has_pip_install_r = False
    for path in setup_files:
        source_text = file_text_by_path.get(path, "")
        if "pip" in source_text and "install" in source_text and "-r" in source_text:
            has_pip_install_r = True
            break

    if not has_pip_install_r:
        return None

    missing_hash_files: list[str] = []
    for req_file in requirements_files:
        text = file_text_by_path.get(req_file)
        if text is None:
            continue
        has_requirement_line = any(
            line.strip() and not line.strip().startswith("#")
            for line in text.splitlines()
        )
        has_hash_pin = "--hash=" in text
        if has_requirement_line and not has_hash_pin:
            missing_hash_files.append(req_file)

    if not missing_hash_files:
        return None

    return SecurityAuditFinding(
        finding_id="SA-003",
        severity="LOW",
        title="Dependencies are version-pinned but not hash-verified",
        description=(
            "Setup scripts install dependencies from requirements files without `--require-hashes` "
            "or per-package hashes. This leaves room for tampered package artifact retrieval in "
            "supply-chain attack scenarios."
        ),
        evidence=(
            "Environment setup scripts run `pip install -r <requirements>`.",
            "Requirement files pin versions but do not include `--hash` entries.",
        ),
        related_files=tuple(sorted(set(present_setup_files + missing_hash_files))),
        related_functions=(
            "tools.setup_ai_news_env.install_requirements",
            "tools.setup_security_audit_env.install_requirements",
        ),
        recommended_fixes=(
            "Generate hashed lock files (e.g., with `pip-compile --generate-hashes`).",
            "Install with `pip install --require-hashes -r <file>` in setup scripts.",
            "Enforce dependency integrity checks in CI verification steps.",
        ),
    )


def _finding_sort_key(finding: SecurityAuditFinding) -> tuple[int, str]:
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return (severity_order.get(finding.severity, 99), finding.finding_id)
