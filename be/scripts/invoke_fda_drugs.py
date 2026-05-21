#!/usr/bin/env python3
"""Manual pipeline run: FDA human drug approvals (openFDA Drugs@FDA).

Uses recent ORIG approvals; default restricts to ``TYPE 1`` (New Molecular Entity).
Relevance scoring is skipped (matches ``invoke_disease_advances`` pattern).

Examples:

  python scripts/invoke_fda_drugs.py --dry-run --days 180 --max-results 15

  python scripts/invoke_fda_drugs.py --since 20260101 --until 20260520 --batch-pr --max-articles 3

Optional ``OPENFDA_API_KEY`` in ``.env`` raises openFDA quota (see https://open.fda.gov/apis/authentication/).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the article pipeline for recent FDA Drugs@FDA original approvals "
            "(openFDA; default new molecular entities only)."
        )
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help=(
            "If --since/--until omitted: look back this many calendar days "
            "(default 90)."
        ),
    )
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Inclusive start YYYYMMDD (FDA openFDA submission_status_date query).",
    )
    parser.add_argument(
        "--until",
        type=str,
        default=None,
        help="Inclusive end YYYYMMDD.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=25,
        help="Maximum Drugs@FDA application records to normalize for this run (before dedup/table).",
    )
    parser.add_argument(
        "--all-original-types",
        action="store_true",
        help="Include every approved ORIG submission in the window, not only Type 1 / NME.",
    )
    parser.add_argument("--max-articles", type=int, help="Override MAX_ARTICLES_PER_RUN for this run.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and preview only — no OpenAI, GitHub, or DynamoDB.",
    )
    parser.add_argument(
        "--batch-pr",
        action="store_true",
        help="Open one draft PR for every MDX from this run (sets GITHUB_BATCH_PR).",
    )
    args = parser.parse_args()

    load_dotenv()
    if args.batch_pr:
        os.environ["GITHUB_BATCH_PR"] = "1"
    if args.max_articles is not None:
        os.environ["MAX_ARTICLES_PER_RUN"] = str(args.max_articles)

    from medical_news.feeds.fda_drugsfda import fetch_recent_drug_approvals
    from medical_news.handlers.orchestrator import process_articles
    from medical_news.util import logger

    try:
        articles = fetch_recent_drug_approvals(
            since_yyyymmdd=args.since,
            until_yyyymmdd=args.until,
            days=args.days,
            max_results=args.max_results,
            nme_only=not args.all_original_types,
        )
    except ValueError as exc:
        parser.error(str(exc))

    logger.info(
        "openFDA Drugs@FDA fetch complete",
        {
            "count": len(articles),
            "nmeOnly": not args.all_original_types,
            "dryRun": args.dry_run,
        },
    )

    if args.dry_run:
        print(
            json.dumps(
                [
                    {
                        "date": a["published_date"],
                        "title": a["title"],
                        "url": a["url"],
                        "source_id": a["source_id"],
                    }
                    for a in articles
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    summary = process_articles(articles)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
