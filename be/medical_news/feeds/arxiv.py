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
            xml = get_text(
                ARXIV_API,
                params={
                    "search_query": query,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                    "max_results": max_per_category,
                },
                timeout=30,
            )
            out.extend(_parse_arxiv(xml))
        except Exception as exc:
            logger.warn("arxiv query failed", {"cat": category, "err": str(exc)})
    return out


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
