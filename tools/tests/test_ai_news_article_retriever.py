#!/usr/bin/env python3
"""Unit tests for AI news article retrieval module."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.ai_news_crawler.article_retriever import (
    ArticleRetriever,
    RetrievedArticle,
    RetrieverError,
    SourceDefinition,
    articles_to_json_ready,
    load_source_definitions,
)


class FakeFetcher:
    def __init__(self, responses: dict[str, str]) -> None:
        self._responses = responses
        self.called_urls: list[str] = []

    def fetch_text(self, url: str) -> str:
        self.called_urls.append(url)
        if url not in self._responses:
            raise RuntimeError(f"No mocked response for URL: {url}")
        return self._responses[url]


ARXIV_ATOM_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2601.00001v1</id>
    <updated>2026-01-15T10:30:00Z</updated>
    <published>2026-01-14T12:00:00Z</published>
    <title>  Efficient Multi-Agent Planning with Graph Memory  </title>
    <summary>We propose a planning method for cooperative agents.</summary>
    <author><name>Alex Rivera</name></author>
    <author><name>Sam Lee</name></author>
    <link href="http://arxiv.org/abs/2601.00001v1" rel="alternate" type="text/html"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2601.00002v1</id>
    <updated>2026-01-14T09:00:00Z</updated>
    <published>2026-01-13T12:00:00Z</published>
    <title>Adaptive Compression for AI News Indexing</title>
    <summary>Data compression for index maintenance.</summary>
    <author><name>Jordan Kim</name></author>
    <link href="http://arxiv.org/abs/2601.00002v1" rel="alternate" type="text/html"/>
  </entry>
</feed>
"""

RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example AI News</title>
    <item>
      <title>Lab Releases Agent Benchmark</title>
      <link>https://example.com/news/agent-benchmark</link>
      <pubDate>Thu, 05 Mar 2026 12:00:00 GMT</pubDate>
      <author>editor@example.com (Editor One)</author>
      <description>Benchmark covers planning and tool use.</description>
    </item>
    <item>
      <title>New Open Dataset for Robotics</title>
      <link>https://example.com/news/open-dataset</link>
      <pubDate>Wed, 04 Mar 2026 17:00:00 GMT</pubDate>
      <description>Dataset targets household tasks.</description>
    </item>
  </channel>
</rss>
"""

HTML_SAMPLE = """
<html>
  <body>
    <article><a href="https://example.org/post/1">Site Post One</a></article>
    <article><a href="https://example.org/post/2">Site Post Two</a></article>
    <article><a href="https://example.org/post/2">Site Post Two</a></article>
    <h2><a href="#skip-anchor">Skip Anchor</a></h2>
  </body>
</html>
"""


class AiNewsArticleRetrieverTests(unittest.TestCase):
    def test_retrieve_arxiv_articles(self) -> None:
        source = SourceDefinition(
            source_id="arxiv-cs-ai",
            source_name="Arxiv CS.AI",
            source_type="arxiv",
            url="https://export.arxiv.org/api/query?search_query=cat:cs.AI",
            limit=5,
        )
        retriever = ArticleRetriever(
            fetcher=FakeFetcher(
                responses={
                    "https://export.arxiv.org/api/query?search_query=cat:cs.AI": (
                        ARXIV_ATOM_SAMPLE
                    )
                }
            )
        )

        articles = retriever.retrieve_from_source(source)

        self.assertEqual(len(articles), 2)
        self.assertEqual(articles[0].title, "Efficient Multi-Agent Planning with Graph Memory")
        self.assertEqual(articles[0].url, "http://arxiv.org/abs/2601.00001v1")
        self.assertEqual(articles[0].authors, ("Alex Rivera", "Sam Lee"))
        self.assertEqual(
            articles[0].published_at.isoformat(),
            "2026-01-14T12:00:00+00:00",
        )
        self.assertEqual(articles[1].authors, ("Jordan Kim",))

    def test_retrieve_rss_articles(self) -> None:
        source = SourceDefinition(
            source_id="example-rss",
            source_name="Example RSS",
            source_type="rss",
            url="https://example.com/rss.xml",
            limit=1,
        )
        retriever = ArticleRetriever(
            fetcher=FakeFetcher(responses={"https://example.com/rss.xml": RSS_SAMPLE})
        )

        articles = retriever.retrieve_from_source(source)

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "Lab Releases Agent Benchmark")
        self.assertEqual(
            articles[0].summary,
            "Benchmark covers planning and tool use.",
        )
        self.assertEqual(
            articles[0].published_at.isoformat(),
            "2026-03-05T12:00:00+00:00",
        )

    def test_retrieve_html_headlines_deduplicates_links(self) -> None:
        source = SourceDefinition(
            source_id="example-html",
            source_name="Example HTML",
            source_type="html",
            url="https://example.org/news",
            limit=10,
        )
        retriever = ArticleRetriever(
            fetcher=FakeFetcher(responses={"https://example.org/news": HTML_SAMPLE})
        )

        articles = retriever.retrieve_from_source(source)

        self.assertEqual(len(articles), 2)
        self.assertEqual(
            [article.url for article in articles],
            ["https://example.org/post/1", "https://example.org/post/2"],
        )
        self.assertTrue(
            all(article.published_at.tzinfo == timezone.utc for article in articles)
        )

    def test_retrieve_all_combines_multiple_sources(self) -> None:
        fetcher = FakeFetcher(
            responses={
                "https://export.arxiv.org/api/query?search_query=cat:cs.AI": ARXIV_ATOM_SAMPLE,
                "https://example.com/rss.xml": RSS_SAMPLE,
            }
        )
        retriever = ArticleRetriever(fetcher=fetcher)
        sources = [
            SourceDefinition(
                source_id="arxiv-cs-ai",
                source_name="Arxiv CS.AI",
                source_type="arxiv",
                url="https://export.arxiv.org/api/query?search_query=cat:cs.AI",
                limit=1,
            ),
            SourceDefinition(
                source_id="example-rss",
                source_name="Example RSS",
                source_type="rss",
                url="https://example.com/rss.xml",
                limit=2,
            ),
        ]

        articles = retriever.retrieve_all(sources)

        self.assertEqual(len(articles), 3)
        self.assertEqual(
            fetcher.called_urls,
            [
                "https://export.arxiv.org/api/query?search_query=cat:cs.AI",
                "https://example.com/rss.xml",
            ],
        )
        self.assertTrue(all(isinstance(article, RetrievedArticle) for article in articles))

    def test_unsupported_source_type_raises_error(self) -> None:
        source = SourceDefinition(
            source_id="unsupported",
            source_name="Unsupported",
            source_type="json",
            url="https://example.com/data.json",
            limit=5,
        )
        retriever = ArticleRetriever(
            fetcher=FakeFetcher(responses={"https://example.com/data.json": "{}"})
        )

        with self.assertRaises(RetrieverError):
            retriever.retrieve_from_source(source)

    def test_load_source_definitions_from_sources_key(self) -> None:
        payload = {
            "sources": [
                {
                    "source_id": "arxiv-cs-ai",
                    "source_name": "Arxiv CS.AI",
                    "source_type": "arxiv",
                    "url": "https://export.arxiv.org/api/query?search_query=cat:cs.AI",
                    "limit": 3,
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "sources.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            sources = load_source_definitions(config_path)

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].limit, 3)
        self.assertEqual(sources[0].source_type, "arxiv")

    def test_load_source_definitions_rejects_invalid_limit(self) -> None:
        payload = [
            {
                "source_id": "bad-source",
                "source_name": "Bad Source",
                "source_type": "rss",
                "url": "https://example.com/rss.xml",
                "limit": 0,
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "sources.json"
            config_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(RetrieverError):
                load_source_definitions(config_path)

    def test_articles_to_json_ready_serializes_shape(self) -> None:
        source = SourceDefinition(
            source_id="example-rss",
            source_name="Example RSS",
            source_type="rss",
            url="https://example.com/rss.xml",
            limit=1,
        )
        retriever = ArticleRetriever(
            fetcher=FakeFetcher(responses={"https://example.com/rss.xml": RSS_SAMPLE})
        )
        articles = retriever.retrieve_from_source(source)
        payload = articles_to_json_ready(articles)

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["source_id"], "example-rss")
        self.assertIsInstance(payload[0]["authors"], list)
        self.assertEqual(payload[0]["url"], "https://example.com/news/agent-benchmark")


if __name__ == "__main__":
    unittest.main()
