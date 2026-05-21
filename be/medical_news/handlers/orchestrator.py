from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, cast

from medical_news.ai.generator import generate_greek
from medical_news.ai.relevance import VALID_CATEGORIES, score
from medical_news.db.dynamodb import exists, put
from medical_news.feeds import fetch_all
from medical_news.github.pr import BatchArticleEntry, PrResult, open_batch_pr, open_pr
from medical_news.markdown.mdx import MdxFile, build_mdx
from medical_news.normalize.article import dedup_key
from medical_news.types import ArticleCategory, ProcessedRecord, RawArticle, RunSummary
from medical_news.util import logger
from medical_news.util.hash import content_hash


def handler(event: dict[str, Any] | None, context: Any) -> RunSummary:
    return process_articles(fetch_all())


def _batch_pr_requested() -> bool:
    raw = os.environ.get("GITHUB_BATCH_PR", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def process_articles(articles: list[RawArticle]) -> RunSummary:
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

    summary["fetched"] = len(articles)
    processed_this_run = 0
    batch_pr = _batch_pr_requested()
    batch_queue: list[dict[str, Any]] = []

    for article in articles:
        if processed_this_run >= max_articles:
            logger.info("max articles per run reached", {"maxArticles": max_articles})
            break

        pk = dedup_key(article)
        try:
            if exists(pk):
                summary["alreadyProcessed"] += 1
                continue

            if article.get("bypass_relevance"):
                cat = article.get("category_override")
                category: ArticleCategory = (
                    cast(ArticleCategory, cat) if isinstance(cat, str) and cat in VALID_CATEGORIES else "other"
                )
            else:
                relevance = score(article)
                if not relevance["relevant"] or relevance["score"] < min_score:
                    summary["skippedLowScore"] += 1
                    put(_skipped_record(pk, article, relevance["score"]))
                    continue
                category = relevance["category"]

            greek = generate_greek(article)
            summary["generated"] += 1

            mdx = build_mdx(article, greek, category)
            if article.get("bypass_relevance"):
                bypass_lines = []
                if article.get("source") == "fda":
                    bypass_lines.append(
                        "**FDA Drugs@FDA (openFDA):** relevance scoring was skipped; summarize regulatory approvals metadata faithfully. Direct readers to the official label and prescribing information for efficacy/safety."
                    )
                else:
                    bypass_lines.append(
                        "**Curated disease/advance feeds:** relevance scoring was skipped for this batch.",
                    )
                if article.get("featured"):
                    bypass_lines.append(
                        "**Auto-feature:** `featured: true` was set — clear it if the story does not merit the homepage carousel."
                    )
                pipeline_note = " ".join(bypass_lines)
            else:
                pipeline_note = None

            if batch_pr:
                batch_queue.append(
                    {
                        "pk": pk,
                        "article": article,
                        "mdx": mdx,
                        "pipeline_note": pipeline_note,
                    }
                )
            else:
                pr = open_pr(
                    mdx,
                    title_gr=greek["title_gr"],
                    source_url=article["url"],
                    pipeline_note=pipeline_note,
                )
                summary["prsOpened"] += 1
                put(_processed_record(pk, article, mdx, pr))
                logger.info("pr opened", {"slug": mdx.slug, "pr": pr.url})

            processed_this_run += 1
        except Exception as exc:
            message = str(exc)
            logger.error("article failed", {"sourceId": article["source_id"], "message": message})
            summary["errors"].append({"sourceId": article["source_id"], "message": message})

    if batch_pr and batch_queue:
        entries: list[BatchArticleEntry] = [
            (chunk["mdx"], chunk["article"]["url"], chunk["pipeline_note"]) for chunk in batch_queue
        ]
        pr = open_batch_pr(entries)
        summary["prsOpened"] += 1
        logger.info(
            "batch pr opened",
            {"pr": pr.url, "branch": pr.branch, "articles": len(batch_queue)},
        )
        for chunk in batch_queue:
            put(_processed_record(chunk["pk"], chunk["article"], chunk["mdx"], pr))

    logger.info("run complete", {"summary": summary})
    return summary


def _processed_record(pk: str, article: RawArticle, mdx: MdxFile, pr: PrResult) -> ProcessedRecord:
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
    return record


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
