from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from medical_news.ai.generator import generate_greek
from medical_news.ai.relevance import score
from medical_news.db.dynamodb import exists, put
from medical_news.feeds import fetch_all
from medical_news.github.pr import open_pr
from medical_news.markdown.mdx import build_mdx
from medical_news.normalize.article import dedup_key
from medical_news.types import ProcessedRecord, RawArticle, RunSummary
from medical_news.util import logger
from medical_news.util.hash import content_hash


def handler(event: dict[str, Any] | None, context: Any) -> RunSummary:
    min_score = float(os.environ.get("RELEVANCE_MIN_SCORE", "7"))
    max_articles = int(os.environ.get("MAX_ARTICLES_PER_RUN", "10"))

    summary: RunSummary = {
        "fetched": 0,
        "alreadyProcessed": 0,
        "skippedLowScore": 0,
        "generated": 0,
        "prsOpened": 0,
        "errors": [],
    }

    articles = fetch_all()
    summary["fetched"] = len(articles)
    processed_this_run = 0

    for article in articles:
        if processed_this_run >= max_articles:
            logger.info("max articles per run reached", {"maxArticles": max_articles})
            break

        pk = dedup_key(article)
        try:
            if exists(pk):
                summary["alreadyProcessed"] += 1
                continue

            relevance = score(article)
            if not relevance["relevant"] or relevance["score"] < min_score:
                summary["skippedLowScore"] += 1
                put(_skipped_record(pk, article, relevance["score"]))
                continue

            greek = generate_greek(article)
            summary["generated"] += 1

            mdx = build_mdx(article, greek, relevance["category"])
            pr = open_pr(mdx, title_gr=greek["title_gr"], source_url=article["url"])
            summary["prsOpened"] += 1

            record: ProcessedRecord = {
                "pk": pk,
                "title": article["title"],
                "source": article["source"],
                "url": article["url"],
                "hash": content_hash(article["title"], article["abstract"]),
                "status": "pr-open",
                "slug": mdx.slug,
                "prUrl": pr.url,
                "createdAt": article["published_date"],
                "processedAt": _now_iso(),
            }
            if article.get("doi"):
                record["doi"] = article["doi"]
            put(record)

            logger.info("pr opened", {"slug": mdx.slug, "pr": pr.url})
            processed_this_run += 1
        except Exception as exc:
            message = str(exc)
            logger.error("article failed", {"sourceId": article["source_id"], "message": message})
            summary["errors"].append({"sourceId": article["source_id"], "message": message})

    logger.info("run complete", {"summary": summary})
    return summary


def _skipped_record(pk: str, article: RawArticle, scored: float) -> ProcessedRecord:
    return {
        "pk": pk,
        "title": article["title"],
        "source": article["source"],
        "url": article["url"],
        "hash": content_hash(article["title"], article["abstract"]),
        "status": "skipped-low-score",
        "slug": f"skipped-{scored}",
        "createdAt": article["published_date"],
        "processedAt": _now_iso(),
        **({"doi": article["doi"]} if article.get("doi") else {}),
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
