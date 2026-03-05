#!/usr/bin/env python3
"""CLI for retrieving articles from configured AI news sources."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.ai_news_crawler.article_retriever import (
    ArticleRetriever,
    RetrieverError,
    articles_to_json_ready,
    load_source_definitions,
)

DEFAULT_CONFIG_PATH = Path("tools/ai_news_crawler/sources.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retrieve articles from configured websites and feeds."
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help=(
            "JSON source config path. Default: "
            "tools/ai_news_crawler/sources.json"
        ),
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)

    try:
        sources = load_source_definitions(config_path)
        retriever = ArticleRetriever()
        articles = retriever.retrieve_all(sources)
    except RetrieverError as error:
        print(str(error), file=sys.stderr)
        return 2
    except OSError as error:
        print(f"I/O error during retrieval: {error}", file=sys.stderr)
        return 1

    payload = {"article_count": len(articles), "articles": articles_to_json_ready(articles)}
    if args.pretty:
        print(json.dumps(payload, indent=2))
    else:
        print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
