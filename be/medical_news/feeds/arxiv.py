from __future__ import annotations

from xml.etree import ElementTree

from medical_news.types import RawArticle
from medical_news.util.http import get_text
from medical_news.util import logger

ARXIV_API = "http://export.arxiv.org/api/query"
CATEGORIES = ["cs.AI", "cs.LG", "q-bio"]
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_arxiv(max_per_category: int = 5) -> list[RawArticle]:
    out: list[RawArticle] = []
    for category in CATEGORIES:
        try:
            query = f"cat:{category} AND (abs:medical OR abs:health OR abs:clinical)"
            out.extend(_fetch_arxiv_query(query, max_per_category))
        except Exception as exc:
            logger.warn("arxiv query failed", {"cat": category, "err": str(exc)})
    return out


def fetch_arxiv_query(query: str, *, max_results: int = 10, year: int | None = None) -> list[RawArticle]:
    dated_query = query
    if year is not None:
        dated_query = f"({query}) AND submittedDate:[{year}01010000 TO {year}12312359]"
    return _fetch_arxiv_query(dated_query, max_results)


def _fetch_arxiv_query(query: str, max_results: int) -> list[RawArticle]:
    xml = get_text(
        ARXIV_API,
        params={
            "search_query": query,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": max_results,
        },
        timeout=30,
    )
    return _parse_arxiv(xml)


def _parse_arxiv(xml: str) -> list[RawArticle]:
    root = ElementTree.fromstring(xml)
    articles: list[RawArticle] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        url = _text(entry, "atom:id")
        source_id = url.split("/abs/")[-1] if "/abs/" in url else url
        articles.append(
            {
                "source": "arxiv",
                "source_id": source_id,
                "title": " ".join(_text(entry, "atom:title").split()),
                "abstract": " ".join(_text(entry, "atom:summary").split()),
                "authors": [_text(author, "atom:name") for author in entry.findall("atom:author", ATOM_NS)],
                "published_date": _text(entry, "atom:published")[:10],
                "url": url,
            }
        )
    return articles


def _text(node: ElementTree.Element, path: str) -> str:
    child = node.find(path, ATOM_NS)
    return "".join(child.itertext()) if child is not None else ""
