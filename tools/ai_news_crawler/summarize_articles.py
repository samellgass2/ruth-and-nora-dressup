#!/usr/bin/env python3
"""Generate an HTML AI newsletter from retrieved article JSON."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.ai_news_crawler.article_retriever import (
    ArticleRetriever,
    RetrieverError,
    articles_to_json_ready,
    load_source_definitions,
)
from tools.ai_news_crawler.newsletter_summarizer import (
    SummarizerError,
    load_articles_payload,
    render_newsletter_html,
    write_newsletter_html,
)

DEFAULT_CONFIG_PATH = Path("tools/ai_news_crawler/sources.json")
DEFAULT_OUTPUT_PATH = Path("tools/ai_news_crawler/output/newsletter.html")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize retrieved articles into newsletter HTML."
    )
    parser.add_argument(
        "--input-json",
        help=(
            "Path to retrieved articles JSON (shape from retrieve_articles.py). "
            "If omitted, sources are crawled directly using --config."
        ),
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help=(
            "Source config used when --input-json is omitted. "
            "Default: tools/ai_news_crawler/sources.json"
        ),
    )
    parser.add_argument(
        "--output-html",
        default=str(DEFAULT_OUTPUT_PATH),
        help=(
            "Output HTML path for generated newsletter. "
            "Default: tools/ai_news_crawler/output/newsletter.html"
        ),
    )
    parser.add_argument(
        "--title",
        default="AI News Digest",
        help="Newsletter title.",
    )
    parser.add_argument(
        "--max-articles-per-source",
        type=int,
        default=5,
        help="Maximum articles to include per source section.",
    )
    parser.add_argument(
        "--print-html",
        action="store_true",
        help="Print generated HTML to stdout in addition to writing file.",
    )
    return parser.parse_args()


def _load_articles_from_source_config(config_path: Path) -> object:
    sources = load_source_definitions(config_path)
    retriever = ArticleRetriever()
    retrieved = retriever.retrieve_all(sources)
    return {"article_count": len(retrieved), "articles": articles_to_json_ready(retrieved)}


def _load_payload(args: argparse.Namespace) -> object:
    if args.input_json:
        input_path = Path(args.input_json)
        if not input_path.exists():
            raise SummarizerError(f"Input JSON file not found: {input_path}")
        try:
            return json.loads(input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise SummarizerError(f"Invalid JSON in '{input_path}': {error}") from error

    return _load_articles_from_source_config(Path(args.config))


def main() -> int:
    args = parse_args()

    if args.max_articles_per_source <= 0:
        print("--max-articles-per-source must be positive", file=sys.stderr)
        return 2

    try:
        payload = _load_payload(args)
        articles = load_articles_payload(payload)
        html = render_newsletter_html(
            articles=articles,
            newsletter_title=args.title,
            generated_at=datetime.now(tz=timezone.utc),
            max_articles_per_source=args.max_articles_per_source,
        )
        output_path = Path(args.output_html)
        write_newsletter_html(output_path, html)
    except (RetrieverError, SummarizerError) as error:
        print(str(error), file=sys.stderr)
        return 2
    except OSError as error:
        print(f"I/O error during summarization: {error}", file=sys.stderr)
        return 1

    print(f"Wrote newsletter HTML to {output_path}")
    if args.print_html:
        print(html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
