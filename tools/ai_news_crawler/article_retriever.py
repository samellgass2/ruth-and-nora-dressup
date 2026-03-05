#!/usr/bin/env python3
"""Article retrieval logic for AI news crawling workflows.

This module provides:
- source definitions for RSS and HTML pages,
- deterministic parsing for Arxiv Atom feeds,
- retrieval orchestration across multiple configured sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
from typing import Any, Iterable, Protocol
from urllib.request import Request, urlopen
from xml.etree import ElementTree
import re

DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_USER_AGENT = (
    "ai-news-crawler/0.1 (+https://example.local/workflows/ai-news-crawler)"
)
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


@dataclass(frozen=True)
class RetrievedArticle:
    """Normalized article shape used by downstream summarization steps."""

    source_id: str
    source_name: str
    title: str
    url: str
    published_at: datetime
    summary: str
    authors: tuple[str, ...]


@dataclass(frozen=True)
class SourceDefinition:
    """Crawler source config definition."""

    source_id: str
    source_name: str
    source_type: str
    url: str
    limit: int = 10


class RetrieverError(RuntimeError):
    """Raised when retrieval/parsing fails for a source."""


class HttpFetcher(Protocol):
    """Minimal HTTP fetcher contract used for dependency injection."""

    def fetch_text(self, url: str) -> str:
        """Fetch a URL and return text payload."""


class UrllibFetcher:
    """HTTP fetcher backed by urllib from Python stdlib."""

    def __init__(
        self,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent

    def fetch_text(self, url: str) -> str:
        request = Request(url=url, headers={"User-Agent": self._user_agent})
        with urlopen(request, timeout=self._timeout_seconds) as response:
            payload = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")


def _to_datetime(value: str | datetime | None) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    if not value:
        return datetime.now(tz=timezone.utc)

    text = value.strip()
    try:
        # RFC3339-ish / ISO timestamps from Atom feeds.
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass

    try:
        # RFC2822 timestamps from RSS feeds.
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return datetime.now(tz=timezone.utc)


def _strip_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.split())


def _strip_html(value: str) -> str:
    # Lightweight HTML cleanup for summaries.
    no_tags = re.sub(r"<[^>]+>", " ", value)
    return _strip_text(unescape(no_tags))


def _safe_fromstring(xml_text: str, source: SourceDefinition) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as error:
        raise RetrieverError(
            f"XML parse failed for source '{source.source_id}': {error}"
        ) from error


def parse_arxiv_feed(
    source: SourceDefinition,
    feed_text: str,
) -> list[RetrievedArticle]:
    """Parse Arxiv Atom feed entries into normalized records."""
    root = _safe_fromstring(feed_text, source)

    entries = root.findall("atom:entry", ATOM_NS)
    articles: list[RetrievedArticle] = []
    for entry in entries[: source.limit]:
        title = _strip_text(entry.findtext("atom:title", default="", namespaces=ATOM_NS))

        link_url = ""
        for link in entry.findall("atom:link", ATOM_NS):
            href = _strip_text(link.attrib.get("href"))
            rel = _strip_text(link.attrib.get("rel"))
            if href and (not rel or rel == "alternate"):
                link_url = href
                break

        if not link_url:
            link_url = _strip_text(entry.findtext("atom:id", default="", namespaces=ATOM_NS))

        summary_raw = _strip_text(
            entry.findtext("atom:summary", default="", namespaces=ATOM_NS)
        )

        author_names: list[str] = []
        for author in entry.findall("atom:author", ATOM_NS):
            name = _strip_text(author.findtext("atom:name", default="", namespaces=ATOM_NS))
            if name:
                author_names.append(name)

        published_value = _strip_text(
            entry.findtext("atom:published", default="", namespaces=ATOM_NS)
        )
        if not published_value:
            published_value = _strip_text(
                entry.findtext("atom:updated", default="", namespaces=ATOM_NS)
            )

        if title and link_url:
            articles.append(
                RetrievedArticle(
                    source_id=source.source_id,
                    source_name=source.source_name,
                    title=title,
                    url=link_url,
                    published_at=_to_datetime(published_value),
                    summary=_strip_html(summary_raw),
                    authors=tuple(author_names),
                )
            )

    return articles


def parse_rss_feed(
    source: SourceDefinition,
    feed_text: str,
) -> list[RetrievedArticle]:
    """Parse standard RSS feed entries."""
    root = _safe_fromstring(feed_text, source)

    channel = root.find("channel")
    if channel is None:
        raise RetrieverError(f"RSS channel missing for source '{source.source_id}'")

    items: list[RetrievedArticle] = []
    for item in channel.findall("item")[: source.limit]:
        title = _strip_text(item.findtext("title", default=""))
        link_url = _strip_text(item.findtext("link", default=""))
        summary_raw = _strip_text(
            item.findtext("description", default="")
            or item.findtext("summary", default="")
        )
        author_text = _strip_text(item.findtext("author", default=""))
        published_value = _strip_text(
            item.findtext("pubDate", default="")
            or item.findtext("published", default="")
        )

        authors: tuple[str, ...] = (author_text,) if author_text else tuple()

        if title and link_url:
            items.append(
                RetrievedArticle(
                    source_id=source.source_id,
                    source_name=source.source_name,
                    title=title,
                    url=link_url,
                    published_at=_to_datetime(published_value),
                    summary=_strip_html(summary_raw),
                    authors=authors,
                )
            )

    return items


class _HeadlineLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._anchor_depth = 0
        self._current_href = ""
        self._current_text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = ""
        for name, value in attrs:
            if name == "href" and value:
                href = value
                break
        self._anchor_depth += 1
        self._current_href = href
        self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._anchor_depth > 0:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._anchor_depth == 0:
            return
        self._anchor_depth -= 1
        if self._anchor_depth > 0:
            return

        title = _strip_text("".join(self._current_text))
        href = _strip_text(self._current_href)
        if title and href and not href.startswith("#"):
            self.links.append((title, href))
        self._current_href = ""
        self._current_text = []


def parse_html_headlines(
    source: SourceDefinition,
    html_text: str,
) -> list[RetrievedArticle]:
    """Extract article-like links from an HTML page."""
    parser = _HeadlineLinkParser()
    parser.feed(html_text)

    results: list[RetrievedArticle] = []
    seen_urls: set[str] = set()
    for title, href in parser.links:
        if href in seen_urls:
            continue
        seen_urls.add(href)

        results.append(
            RetrievedArticle(
                source_id=source.source_id,
                source_name=source.source_name,
                title=title,
                url=href,
                published_at=datetime.now(tz=timezone.utc),
                summary="",
                authors=tuple(),
            )
        )
        if len(results) >= source.limit:
            break

    return results


class ArticleRetriever:
    """Retrieve and parse articles from configured sources."""

    def __init__(self, fetcher: HttpFetcher | None = None) -> None:
        self._fetcher = fetcher or UrllibFetcher()

    def retrieve_from_source(
        self, source: SourceDefinition
    ) -> list[RetrievedArticle]:
        """Retrieve article items for one source definition."""
        payload = self._fetcher.fetch_text(source.url)
        source_type = source.source_type.lower().strip()

        if source_type == "arxiv":
            return parse_arxiv_feed(source, payload)
        if source_type == "rss":
            return parse_rss_feed(source, payload)
        if source_type == "html":
            return parse_html_headlines(source, payload)
        raise RetrieverError(
            f"Unsupported source_type '{source.source_type}' "
            f"for source '{source.source_id}'"
        )

    def retrieve_all(
        self, sources: Iterable[SourceDefinition]
    ) -> list[RetrievedArticle]:
        """Retrieve all articles from multiple sources."""
        all_articles: list[RetrievedArticle] = []
        for source in sources:
            source_articles = self.retrieve_from_source(source)
            all_articles.extend(source_articles)
        return all_articles


def parse_source_definitions(raw_sources: list[object]) -> list[SourceDefinition]:
    """Validate and parse source definitions from plain JSON-like data."""
    parsed: list[SourceDefinition] = []
    for index, item in enumerate(raw_sources):
        if not isinstance(item, dict):
            raise RetrieverError(f"Source index {index} is not an object")

        source_id = item.get("source_id")
        source_name = item.get("source_name")
        source_type = item.get("source_type")
        url = item.get("url")
        limit = item.get("limit", 10)
        if not isinstance(source_id, str) or not source_id.strip():
            raise RetrieverError(f"Source index {index} has invalid source_id")
        if not isinstance(source_name, str) or not source_name.strip():
            raise RetrieverError(f"Source '{source_id}' has invalid source_name")
        if not isinstance(source_type, str) or not source_type.strip():
            raise RetrieverError(f"Source '{source_id}' has invalid source_type")
        if not isinstance(url, str) or not url.strip():
            raise RetrieverError(f"Source '{source_id}' has invalid url")
        if not isinstance(limit, int) or limit <= 0:
            raise RetrieverError(f"Source '{source_id}' has invalid limit")

        parsed.append(
            SourceDefinition(
                source_id=source_id.strip(),
                source_name=source_name.strip(),
                source_type=source_type.strip(),
                url=url.strip(),
                limit=limit,
            )
        )
    return parsed


def load_source_definitions(config_path: Path) -> list[SourceDefinition]:
    """Load source definitions from a JSON configuration file."""
    if not config_path.exists():
        raise RetrieverError(f"Source config file not found: {config_path}")

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RetrieverError(f"Invalid source config JSON: {error}") from error

    sources_value: Any
    if isinstance(payload, dict) and "sources" in payload:
        sources_value = payload["sources"]
    else:
        sources_value = payload

    if not isinstance(sources_value, list):
        raise RetrieverError("Source config must contain a list at root or `sources`")
    return parse_source_definitions(sources_value)


def articles_to_json_ready(articles: Iterable[RetrievedArticle]) -> list[dict[str, Any]]:
    """Serialize retrieved article records to JSON-ready objects."""
    serialized: list[dict[str, Any]] = []
    for article in articles:
        serialized.append(
            {
                "source_id": article.source_id,
                "source_name": article.source_name,
                "title": article.title,
                "url": article.url,
                "published_at": article.published_at.isoformat(),
                "summary": article.summary,
                "authors": list(article.authors),
            }
        )
    return serialized
