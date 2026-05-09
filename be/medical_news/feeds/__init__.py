from __future__ import annotations

from medical_news.feeds.arxiv import fetch_arxiv
from medical_news.feeds.pubmed import fetch_pubmed
from medical_news.feeds.rss import fetch_rss
from medical_news.types import RawArticle
from medical_news.util import logger


def fetch_all() -> list[RawArticle]:
    pubmed = _safe_fetch("pubmed", fetch_pubmed)
    arxiv = _safe_fetch("arxiv", fetch_arxiv)
    rss = _safe_fetch("rss", fetch_rss)
    logger.info("fetched", {"pubmed": len(pubmed), "arxiv": len(arxiv), "rss": len(rss)})
    return [*pubmed, *arxiv, *rss]


def _safe_fetch(name: str, fn) -> list[RawArticle]:
    try:
        return fn()
    except Exception as exc:
        logger.error(f"{name} failed", {"err": str(exc)})
        return []
