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
        description="Run the article pipeline for recent RSS articles from the curated sources only."
    )
    parser.add_argument("--max-per-source", type=int, default=5, help="Maximum raw RSS articles to keep per feed.")
    parser.add_argument("--max-articles", type=int, help="Override MAX_ARTICLES_PER_RUN for this run.")
    parser.add_argument("--min-score", type=float, help="Override RELEVANCE_MIN_SCORE for this run.")
    parser.add_argument(
        "--source",
        choices=["all", "npj-digital-medicine", "lancet-digital-health", "radiology-ai"],
        default="all",
        help="Limit to one curated RSS source.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only fetch and print recent RSS candidates. Does not run OpenAI, GitHub, or DynamoDB.",
    )
    args = parser.parse_args()

    load_dotenv()
    if args.max_articles is not None:
        os.environ["MAX_ARTICLES_PER_RUN"] = str(args.max_articles)
    if args.min_score is not None:
        os.environ["RELEVANCE_MIN_SCORE"] = str(args.min_score)

    from medical_news.feeds.rss import fetch_rss
    from medical_news.handlers.orchestrator import process_articles
    from medical_news.types import RawArticle
    from medical_news.util import logger

    articles = fetch_rss()
    if args.source != "all":
        articles = [article for article in articles if _feed_label(article) == args.source]

    articles = _limit_per_source(_sort_recent_first(articles), args.max_per_source)
    logger.info(
        "rss fetch complete",
        {
            "source": args.source,
            "maxPerSource": args.max_per_source,
            "articles": len(articles),
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
                }
                for article in items
            ],
        }
        for label, items in sorted(grouped.items())
    ]


if __name__ == "__main__":
    main()
