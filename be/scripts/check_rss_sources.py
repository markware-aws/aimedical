from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check RSS source coverage without running OpenAI, GitHub, or DynamoDB."
    )
    parser.add_argument("--year", type=int, default=2025, help="Published year to check.")
    parser.add_argument("--limit", type=int, default=5, help="Sample articles to print per source.")
    args = parser.parse_args()

    from medical_news.feeds.rss import FEEDS, _fetch_feed_xml, _parse_rss

    summary: list[dict[str, Any]] = []
    for feed in FEEDS:
        label = feed["label"]
        try:
            articles = _parse_rss(_fetch_feed_xml(feed["url"]), label)
            matches = [article for article in articles if article["published_date"].startswith(f"{args.year}-")]
            summary.append(
                {
                    "label": label,
                    "url": feed["url"],
                    "fetched": len(articles),
                    f"published_in_{args.year}": len(matches),
                    "samples": [
                        {
                            "date": article["published_date"],
                            "title": article["title"],
                            "url": article["url"],
                        }
                        for article in matches[: args.limit]
                    ],
                }
            )
        except Exception as exc:
            summary.append(
                {
                    "label": label,
                    "url": feed["url"],
                    "error": str(exc),
                }
            )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
