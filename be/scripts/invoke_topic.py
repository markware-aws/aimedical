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
    parser = argparse.ArgumentParser(description="Run the article pipeline for a one-off PubMed/arXiv topic query.")
    parser.add_argument("--query", required=True, help="Topic query, e.g. '2025 AI breakthroughs in medicine'.")
    parser.add_argument("--year", type=int, help="Restrict PubMed publication date and arXiv submitted date to this year.")
    parser.add_argument("--max-per-source", type=int, default=10, help="Maximum raw articles to fetch per source.")
    parser.add_argument("--max-articles", type=int, help="Override MAX_ARTICLES_PER_RUN for this run.")
    parser.add_argument("--min-score", type=float, help="Override RELEVANCE_MIN_SCORE for this run.")
    parser.add_argument(
        "--source",
        choices=["all", "pubmed", "arxiv"],
        default="all",
        help="Which source to query. RSS is intentionally omitted for topic runs.",
    )
    args = parser.parse_args()

    load_dotenv()
    if args.max_articles is not None:
        os.environ["MAX_ARTICLES_PER_RUN"] = str(args.max_articles)
    if args.min_score is not None:
        os.environ["RELEVANCE_MIN_SCORE"] = str(args.min_score)

    from medical_news.feeds.arxiv import fetch_arxiv_query
    from medical_news.feeds.pubmed import fetch_pubmed_query
    from medical_news.handlers.orchestrator import process_articles
    from medical_news.types import RawArticle
    from medical_news.util import logger

    articles: list[RawArticle] = []
    if args.source in {"all", "pubmed"}:
        articles.extend(fetch_pubmed_query(args.query, max_results=args.max_per_source, year=args.year))
    if args.source in {"all", "arxiv"}:
        articles.extend(fetch_arxiv_query(_arxiv_query(args.query), max_results=args.max_per_source, year=args.year))

    articles = _dedupe(articles)
    logger.info("topic fetch complete", {"query": args.query, "year": args.year, "source": args.source, "articles": len(articles)})
    summary = process_articles(articles)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _arxiv_query(query: str) -> str:
    terms = [part.strip() for part in query.replace(",", " ").split() if part.strip()]
    if not terms:
        return "abs:medical OR abs:health OR abs:clinical"
    text_query = " OR ".join(f'abs:"{term}"' for term in terms[:8])
    return f"({text_query}) AND (abs:medical OR abs:health OR abs:clinical)"


def _dedupe(articles: list["RawArticle"]) -> list["RawArticle"]:
    seen: set[tuple[str, str]] = set()
    out: list["RawArticle"] = []
    for article in articles:
        key = (article["source"], article["source_id"])
        if key in seen:
            continue
        seen.add(key)
        out.append(article)
    return out


if __name__ == "__main__":
    main()
