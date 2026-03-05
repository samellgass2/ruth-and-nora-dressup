#!/usr/bin/env python3
"""Newsletter summarization and HTML rendering for AI news workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from typing import Any, Iterable


class SummarizerError(RuntimeError):
    """Raised when article payload or summarization rendering is invalid."""


@dataclass(frozen=True)
class NewsletterArticle:
    """Article model used by newsletter summarization/rendering."""

    source_id: str
    source_name: str
    title: str
    url: str
    published_at: datetime
    summary: str
    authors: tuple[str, ...]


@dataclass(frozen=True)
class NewsletterSection:
    """Grouped newsletter section for a single source."""

    source_id: str
    source_name: str
    articles: tuple[NewsletterArticle, ...]


def _strip_text(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.split())


def _parse_timestamp(raw_value: str, article_title: str) -> datetime:
    text = _strip_text(raw_value)
    if not text:
        return datetime.now(tz=timezone.utc)

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise SummarizerError(
            f"Invalid published_at for article '{article_title}': {raw_value}"
        ) from error

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_article(raw_item: object, index: int) -> NewsletterArticle:
    if not isinstance(raw_item, dict):
        raise SummarizerError(f"Article index {index} is not an object")

    source_id = raw_item.get("source_id")
    source_name = raw_item.get("source_name")
    title = raw_item.get("title")
    url = raw_item.get("url")
    published_at = raw_item.get("published_at")

    if not isinstance(source_id, str) or not _strip_text(source_id):
        raise SummarizerError(f"Article index {index} has invalid source_id")
    if not isinstance(source_name, str) or not _strip_text(source_name):
        raise SummarizerError(f"Article index {index} has invalid source_name")
    if not isinstance(title, str) or not _strip_text(title):
        raise SummarizerError(f"Article index {index} has invalid title")
    if not isinstance(url, str) or not _strip_text(url):
        raise SummarizerError(f"Article index {index} has invalid url")
    if not isinstance(published_at, str):
        raise SummarizerError(f"Article index {index} has invalid published_at")

    summary_value = raw_item.get("summary", "")
    if not isinstance(summary_value, str):
        raise SummarizerError(f"Article index {index} has invalid summary")

    authors_value = raw_item.get("authors", [])
    if not isinstance(authors_value, list) or not all(
        isinstance(author, str) for author in authors_value
    ):
        raise SummarizerError(f"Article index {index} has invalid authors")

    return NewsletterArticle(
        source_id=_strip_text(source_id),
        source_name=_strip_text(source_name),
        title=_strip_text(title),
        url=_strip_text(url),
        published_at=_parse_timestamp(published_at, _strip_text(title)),
        summary=_strip_text(summary_value),
        authors=tuple(_strip_text(author) for author in authors_value if _strip_text(author)),
    )


def load_articles_payload(payload: object) -> list[NewsletterArticle]:
    """Load normalized newsletter articles from retrieval JSON payload."""
    raw_articles: object
    if isinstance(payload, dict) and "articles" in payload:
        raw_articles = payload["articles"]
    else:
        raw_articles = payload

    if not isinstance(raw_articles, list):
        raise SummarizerError("Article payload must contain a list at root or `articles`")

    return [_normalize_article(item, index) for index, item in enumerate(raw_articles)]


def load_articles_from_json_file(input_path: Path) -> list[NewsletterArticle]:
    """Read and parse article payload from a JSON file."""
    if not input_path.exists():
        raise SummarizerError(f"Input JSON file not found: {input_path}")

    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SummarizerError(f"Invalid JSON in '{input_path}': {error}") from error

    return load_articles_payload(payload)


def summarize_article(article: NewsletterArticle, max_sentences: int = 2) -> str:
    """Return a short summary sentence block for newsletter consumption."""
    if article.summary:
        sentences = [item.strip() for item in article.summary.split(".") if item.strip()]
        selected = sentences[:max_sentences]
        if selected:
            return ". ".join(selected) + "."

    return f"{article.title}."


def group_articles_by_source(
    articles: Iterable[NewsletterArticle],
    max_articles_per_source: int,
) -> list[NewsletterSection]:
    """Group and limit articles by source, newest first in each section."""
    if max_articles_per_source <= 0:
        raise SummarizerError("max_articles_per_source must be positive")

    grouped: dict[str, tuple[str, list[NewsletterArticle]]] = {}
    for article in articles:
        if article.source_id not in grouped:
            grouped[article.source_id] = (article.source_name, [article])
        else:
            _, source_articles = grouped[article.source_id]
            source_articles.append(article)

    sections: list[NewsletterSection] = []
    for source_id in sorted(grouped.keys()):
        source_name, source_articles = grouped[source_id]
        sorted_articles = sorted(
            source_articles,
            key=lambda item: item.published_at,
            reverse=True,
        )
        limited = tuple(sorted_articles[:max_articles_per_source])
        sections.append(
            NewsletterSection(
                source_id=source_id,
                source_name=source_name,
                articles=limited,
            )
        )
    return sections


def _format_timestamp_utc(value: datetime) -> str:
    utc_value = value.astimezone(timezone.utc)
    return utc_value.strftime("%Y-%m-%d %H:%M UTC")


def _render_article_li(article: NewsletterArticle) -> str:
    safe_title = escape(article.title)
    safe_url = escape(article.url, quote=True)
    safe_summary = escape(summarize_article(article))
    safe_timestamp = escape(_format_timestamp_utc(article.published_at))
    author_label = "Unknown author"
    if article.authors:
        author_label = ", ".join(article.authors)

    return (
        "      <li class=\"newsletter-article\">\n"
        f"        <h3><a href=\"{safe_url}\">{safe_title}</a></h3>\n"
        f"        <p class=\"meta\">{escape(author_label)} | {safe_timestamp}</p>\n"
        f"        <p>{safe_summary}</p>\n"
        "      </li>"
    )


def render_newsletter_html(
    articles: Iterable[NewsletterArticle],
    newsletter_title: str,
    generated_at: datetime | None = None,
    max_articles_per_source: int = 5,
) -> str:
    """Render a complete newsletter HTML document from normalized articles."""
    normalized_title = _strip_text(newsletter_title) or "AI News Digest"
    timestamp = (generated_at or datetime.now(tz=timezone.utc)).astimezone(timezone.utc)
    sections = group_articles_by_source(articles, max_articles_per_source)

    section_blocks: list[str] = []
    for section in sections:
        safe_source_name = escape(section.source_name)
        safe_source_id = escape(section.source_id)
        if section.articles:
            rendered_articles = "\n".join(_render_article_li(item) for item in section.articles)
        else:
            rendered_articles = "      <li class=\"newsletter-empty\">No articles available.</li>"

        section_blocks.append(
            "    <section class=\"newsletter-source\" "
            f"data-source-id=\"{safe_source_id}\">\n"
            f"      <h2>{safe_source_name}</h2>\n"
            "      <ul class=\"newsletter-list\">\n"
            f"{rendered_articles}\n"
            "      </ul>\n"
            "    </section>"
        )

    empty_block = ""
    if not section_blocks:
        empty_block = (
            "    <section class=\"newsletter-source\" data-source-id=\"none\">\n"
            "      <h2>No Sources</h2>\n"
            "      <ul class=\"newsletter-list\">\n"
            "        <li class=\"newsletter-empty\">No articles available.</li>\n"
            "      </ul>\n"
            "    </section>"
        )

    body_sections = "\n".join(section_blocks) if section_blocks else empty_block
    generated_text = escape(_format_timestamp_utc(timestamp))
    safe_title = escape(normalized_title)

    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\" />\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />\n"
        f"  <title>{safe_title}</title>\n"
        "  <style>\n"
        "    body { font-family: Arial, sans-serif; margin: 24px; line-height: 1.45; color: #111; }\n"
        "    .newsletter-header { margin-bottom: 24px; }\n"
        "    .newsletter-header h1 { margin: 0 0 8px; }\n"
        "    .newsletter-source { margin: 0 0 20px; padding: 16px; border: 1px solid #d9d9d9; border-radius: 8px; }\n"
        "    .newsletter-list { margin: 0; padding-left: 20px; }\n"
        "    .newsletter-article { margin-bottom: 16px; }\n"
        "    .newsletter-article h3 { margin: 0 0 4px; font-size: 18px; }\n"
        "    .newsletter-article p { margin: 4px 0; }\n"
        "    .meta { color: #555; font-size: 14px; }\n"
        "    .newsletter-empty { color: #666; }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <main class=\"newsletter\">\n"
        "    <header class=\"newsletter-header\">\n"
        f"      <h1>{safe_title}</h1>\n"
        f"      <p>Generated at {generated_text}</p>\n"
        "    </header>\n"
        f"{body_sections}\n"
        "  </main>\n"
        "</body>\n"
        "</html>\n"
    )


def write_newsletter_html(output_path: Path, html: str) -> None:
    """Write HTML newsletter output to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
