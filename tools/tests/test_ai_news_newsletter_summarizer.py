#!/usr/bin/env python3
"""Unit tests for AI news newsletter summarization and HTML rendering."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.ai_news_crawler.newsletter_summarizer import (
    NewsletterArticle,
    SummarizerError,
    group_articles_by_source,
    load_articles_from_json_file,
    load_articles_payload,
    render_newsletter_html,
    summarize_article,
)


SAMPLE_PAYLOAD = {
    "article_count": 3,
    "articles": [
        {
            "source_id": "arxiv-cs-ai",
            "source_name": "Arxiv CS.AI",
            "title": "Efficient Multi-Agent Planning",
            "url": "https://arxiv.org/abs/2601.00001",
            "published_at": "2026-01-14T12:00:00+00:00",
            "summary": "We propose a planning method. It improves agent coordination.",
            "authors": ["Alex Rivera", "Sam Lee"],
        },
        {
            "source_id": "hn",
            "source_name": "Hacker News",
            "title": "Lab publishes benchmark",
            "url": "https://news.ycombinator.com/item?id=1",
            "published_at": "2026-03-05T12:00:00+00:00",
            "summary": "Benchmark covers tool use and planning.",
            "authors": [],
        },
        {
            "source_id": "hn",
            "source_name": "Hacker News",
            "title": "Open model eval suite",
            "url": "https://news.ycombinator.com/item?id=2",
            "published_at": "2026-03-04T08:30:00+00:00",
            "summary": "",
            "authors": ["Community"],
        },
    ],
}


class AiNewsNewsletterSummarizerTests(unittest.TestCase):
    def test_load_articles_payload_from_articles_key(self) -> None:
        articles = load_articles_payload(SAMPLE_PAYLOAD)

        self.assertEqual(len(articles), 3)
        self.assertEqual(articles[0].source_id, "arxiv-cs-ai")
        self.assertEqual(articles[1].authors, tuple())
        self.assertEqual(
            articles[1].published_at.isoformat(),
            "2026-03-05T12:00:00+00:00",
        )

    def test_load_articles_payload_accepts_list_root(self) -> None:
        articles = load_articles_payload(SAMPLE_PAYLOAD["articles"])

        self.assertEqual(len(articles), 3)
        self.assertEqual(articles[2].title, "Open model eval suite")

    def test_load_articles_payload_rejects_invalid_shape(self) -> None:
        with self.assertRaises(SummarizerError):
            load_articles_payload({"articles": {"not": "a list"}})

    def test_load_articles_from_json_file_reads_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "retrieved.json"
            input_path.write_text(json.dumps(SAMPLE_PAYLOAD), encoding="utf-8")

            articles = load_articles_from_json_file(input_path)

        self.assertEqual(len(articles), 3)
        self.assertEqual(articles[0].authors, ("Alex Rivera", "Sam Lee"))

    def test_summarize_article_limits_sentences(self) -> None:
        article = NewsletterArticle(
            source_id="sample",
            source_name="Sample",
            title="Sample Title",
            url="https://example.com/a",
            published_at=datetime(2026, 3, 5, 12, 0, tzinfo=timezone.utc),
            summary="Sentence one. Sentence two. Sentence three.",
            authors=tuple(),
        )

        summarized = summarize_article(article, max_sentences=2)

        self.assertEqual(summarized, "Sentence one. Sentence two.")

    def test_summarize_article_falls_back_to_title(self) -> None:
        article = NewsletterArticle(
            source_id="sample",
            source_name="Sample",
            title="Fallback headline",
            url="https://example.com/b",
            published_at=datetime(2026, 3, 5, 12, 0, tzinfo=timezone.utc),
            summary="",
            authors=tuple(),
        )

        summarized = summarize_article(article)

        self.assertEqual(summarized, "Fallback headline.")

    def test_group_articles_by_source_sorts_and_limits(self) -> None:
        articles = load_articles_payload(SAMPLE_PAYLOAD)

        sections = group_articles_by_source(articles, max_articles_per_source=1)

        self.assertEqual(len(sections), 2)
        self.assertEqual([section.source_id for section in sections], ["arxiv-cs-ai", "hn"])
        self.assertEqual(len(sections[1].articles), 1)
        self.assertEqual(sections[1].articles[0].title, "Lab publishes benchmark")

    def test_render_newsletter_html_contains_expected_structure_and_content(self) -> None:
        articles = load_articles_payload(SAMPLE_PAYLOAD)

        html = render_newsletter_html(
            articles=articles,
            newsletter_title="AI Daily",
            generated_at=datetime(2026, 3, 5, 13, 0, tzinfo=timezone.utc),
            max_articles_per_source=2,
        )

        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn('<main class="newsletter">', html)
        self.assertIn("<h1>AI Daily</h1>", html)
        self.assertIn("Generated at 2026-03-05 13:00 UTC", html)
        self.assertIn('data-source-id="arxiv-cs-ai"', html)
        self.assertIn('data-source-id="hn"', html)
        self.assertIn("Efficient Multi-Agent Planning", html)
        self.assertIn("Lab publishes benchmark", html)
        self.assertIn("Open model eval suite", html)
        self.assertIn("Unknown author", html)

    def test_render_newsletter_html_escapes_unsafe_content(self) -> None:
        unsafe_article = NewsletterArticle(
            source_id="unsafe",
            source_name="Unsafe <Source>",
            title="Breaking <script>alert(1)</script>",
            url='https://example.com/"bad"',
            published_at=datetime(2026, 3, 5, 12, 0, tzinfo=timezone.utc),
            summary="Summary with <b>tag</b>.",
            authors=("<Admin>",),
        )

        html = render_newsletter_html(
            articles=[unsafe_article],
            newsletter_title="Unsafe <Title>",
            generated_at=datetime(2026, 3, 5, 13, 0, tzinfo=timezone.utc),
            max_articles_per_source=5,
        )

        self.assertIn("Unsafe &lt;Title&gt;", html)
        self.assertIn("Unsafe &lt;Source&gt;", html)
        self.assertIn("Breaking &lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertIn("https://example.com/&quot;bad&quot;", html)
        self.assertIn("&lt;Admin&gt;", html)

    def test_render_newsletter_html_empty_articles_adds_empty_section(self) -> None:
        html = render_newsletter_html(
            articles=[],
            newsletter_title="Empty Digest",
            generated_at=datetime(2026, 3, 5, 13, 0, tzinfo=timezone.utc),
        )

        self.assertIn('data-source-id="none"', html)
        self.assertIn("No articles available.", html)

    def test_summarize_articles_cli_writes_html_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "input.json"
            output_path = Path(temp_dir) / "newsletter.html"
            input_path.write_text(json.dumps(SAMPLE_PAYLOAD), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "tools/ai_news_crawler/summarize_articles.py",
                    "--input-json",
                    str(input_path),
                    "--output-html",
                    str(output_path),
                    "--title",
                    "CLI Digest",
                ],
                cwd=str(REPO_ROOT),
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(output_path.exists())
            html = output_path.read_text(encoding="utf-8")

        self.assertIn("<h1>CLI Digest</h1>", html)
        self.assertIn("Lab publishes benchmark", html)
        self.assertIn('data-source-id="hn"', html)


if __name__ == "__main__":
    unittest.main()
