#!/usr/bin/env python3
"""Manual pipeline run: curated society/disease-news RSS feeds, low-frequency.

Skips relevance scoring (so non-AI stories can pass) and defaults to ``featured: true``
in MDX unless you pass ``--no-featured``.

Uses ``ADVANCE_FEEDS`` in ``medical_news.feeds.disease_advances`` — expand that list
with foundation-specific RSS URLs.

Examples:

  PYTHONIOENCODING=utf-8 python scripts/invoke_disease_advances.py --dry-run --max-per-source 3

  PYTHONIOENCODING=utf-8 python scripts/invoke_disease_advances.py --max-articles 5 --batch-pr
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the article pipeline for curated disease breakthrough / advocacy RSS feeds (manual)."
    )
    parser.add_argument("--max-per-source", type=int, default=3, help="Maximum items to keep per feed URL.")
    parser.add_argument("--max-articles", type=int, help="Override MAX_ARTICLES_PER_RUN for this run.")
    parser.add_argument(
        "--source",
        type=str,
        default="",
        help="Limit to feeds whose ``label`` in ADVANCE_FEEDS contains this substring (case-insensitive).",
    )
    parser.add_argument(
        "--no-featured",
        action="store_true",
        help="Do not set featured: true in generated frontmatter.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and preview only. No OpenAI, GitHub, or DynamoDB.",
    )
    parser.add_argument(
        "--batch-pr",
        action="store_true",
        help="Open one draft PR for all MDX files from this run (sets env GITHUB_BATCH_PR).",
    )
    args = parser.parse_args()

    load_dotenv()
    if args.batch_pr:
        os.environ["GITHUB_BATCH_PR"] = "1"
    if args.max_articles is not None:
        os.environ["MAX_ARTICLES_PER_RUN"] = str(args.max_articles)

    from medical_news.feeds.disease_advances import fetch_disease_advance_candidates
    from medical_news.handlers.orchestrator import process_articles
    from medical_news.types import RawArticle
    from medical_news.util import logger

    articles = fetch_disease_advance_candidates(featured=not args.no_featured)
    needle = args.source.strip().lower()
    if needle:
        articles = [a for a in articles if needle in _feed_label(a)]

    articles = _limit_per_source(_sort_recent_first(articles), args.max_per_source)
    logger.info(
        "disease advance fetch complete",
        {
            "maxPerSource": args.max_per_source,
            "articles": len(articles),
            "featured": not args.no_featured,
            "dryRun": args.dry_run,
        },
    )

    if args.dry_run:
        print(json.dumps(_preview(articles), ensure_ascii=False, indent=2))
        return

    summary = process_articles(articles)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _feed_label(article: "RawArticle") -> str:
    return article["source_id"].split(":", 1)[0]


def _sort_recent_first(articles: list["RawArticle"]) -> list["RawArticle"]:
    return sorted(articles, key=lambda article: article["published_date"], reverse=True)


def _limit_per_source(articles: list["RawArticle"], limit: int) -> list["RawArticle"]:
    counts: dict[str, int] = defaultdict(int)
    out: list["RawArticle"] = []
    for article in articles:
        label = _feed_label(article)
        if counts[label] >= limit:
            continue
        counts[label] += 1
        out.append(article)
    return out


def _preview(articles: list["RawArticle"]) -> list[dict[str, object]]:
    grouped: dict[str, list["RawArticle"]] = defaultdict(list)
    for article in articles:
        grouped[_feed_label(article)].append(article)

    return [
        {
            "label": label,
            "count": len(items),
            "articles": [
                {
                    "date": article["published_date"],
                    "title": article["title"],
                    "url": article["url"],
                    "featured": article.get("featured", False),
                    "category_override": article.get("category_override", ""),
                }
                for article in items
            ],
        }
        for label, items in sorted(grouped.items())
    ]


if __name__ == "__main__":
    main()
