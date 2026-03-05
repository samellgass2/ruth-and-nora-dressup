#!/usr/bin/env python3
"""Acceptance checks for security-audit report generation tooling."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.security_audit.security_audit_report_generator import (
    SecurityAuditReportOptions,
    generate_security_audit_report,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_TOOL = REPO_ROOT / "tools" / "security_audit" / "generate_security_audit_report.py"


class SecurityAuditReportGeneratorTests(unittest.TestCase):
    def test_generates_findings_with_actionable_fixes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._create_sample_security_layout(root)

            report = generate_security_audit_report(root, SecurityAuditReportOptions())

            self.assertEqual(report.summary.high_findings, 1)
            self.assertEqual(report.summary.medium_findings, 1)
            self.assertEqual(report.summary.low_findings, 1)

            finding_ids = [item.finding_id for item in report.findings]
            self.assertEqual(finding_ids, ["SA-001", "SA-002", "SA-003"])

            for finding in report.findings:
                self.assertGreaterEqual(len(finding.recommended_fixes), 1)
                self.assertTrue(all(fix.strip() for fix in finding.recommended_fixes))

    def test_cli_writes_markdown_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._create_sample_security_layout(root)
            output_path = root / "SECURITY_AUDIT_REPORT.md"

            result = subprocess.run(
                [
                    "python3",
                    str(CLI_TOOL),
                    "--root",
                    str(root),
                    "--output",
                    str(output_path),
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            rendered = output_path.read_text(encoding="utf-8")
            self.assertIn("# Security Audit Report", rendered)
            self.assertIn("Recommended fixes:", rendered)

    def test_cli_json_output_contains_summary_and_findings(self) -> None:
        result = subprocess.run(
            [
                "python3",
                str(CLI_TOOL),
                "--root",
                str(REPO_ROOT),
                "--json",
                "--max-depth",
                "1",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertIn("summary", payload)
        self.assertIn("findings", payload)

    def _create_sample_security_layout(self, root: Path) -> None:
        (root / "tools" / "ai_news_crawler").mkdir(parents=True)
        (root / "tools" / "security_audit").mkdir(parents=True)

        (root / "tools" / "ai_news_crawler" / "article_retriever.py").write_text(
            "\n".join(
                [
                    "from urllib.request import Request, urlopen",
                    "",
                    "class UrllibFetcher:",
                    "    def fetch_text(self, url: str) -> str:",
                    "        request = Request(url=url)",
                    "        with urlopen(request, timeout=self._timeout_seconds) as response:",
                    "            return response.read().decode('utf-8')",
                    "",
                    "def parse_source_definitions(raw_sources):",
                    "    parsed = []",
                    "    for item in raw_sources:",
                    "        url = item.get('url')",
                    "        parsed.append({'url': url.strip()})",
                    "    return parsed",
                    "",
                    "def parse_html_headlines(source, html_text):",
                    "    href = 'javascript:alert(1)'",
                    "    return [{'url': href}]",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        (root / "tools" / "ai_news_crawler" / "newsletter_summarizer.py").write_text(
            "\n".join(
                [
                    "def _render_article_li(article):",
                    "    safe_url = article['url']",
                    "    return f'<a href=\"{safe_url}\">x</a>'",
                    "",
                    "def render_newsletter_html(articles, newsletter_title):",
                    "    return ''.join(_render_article_li(article) for article in articles)",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        (root / "tools" / "setup_ai_news_env.py").write_text(
            "def install_requirements(venv_python):\n"
            "    return [str(venv_python), '-m', 'pip', 'install', '-r', 'req']\n",
            encoding="utf-8",
        )
        (root / "tools" / "setup_security_audit_env.py").write_text(
            "def install_requirements(venv_python):\n"
            "    return [str(venv_python), '-m', 'pip', 'install', '-r', 'req']\n",
            encoding="utf-8",
        )

        (root / "tools" / "ai_news_crawler" / "requirements.txt").write_text(
            "requests==2.32.0\n",
            encoding="utf-8",
        )
        (root / "tools" / "security_audit" / "requirements.txt").write_text(
            "flask==3.0.0\n",
            encoding="utf-8",
        )
        (root / "tools" / "ai_news_crawler" / "sources.json").write_text(
            '{"sources": [{"url": "https://example.org"}]}\n',
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
