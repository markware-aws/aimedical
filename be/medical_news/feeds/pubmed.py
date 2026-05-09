from __future__ import annotations

from datetime import date
from typing import Iterable
from xml.etree import ElementTree

from medical_news.types import RawArticle
from medical_news.util.http import get_json, get_text
from medical_news.util import logger

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

QUERIES = [
    "artificial intelligence medicine",
    "machine learning healthcare",
    "deep learning diagnostics",
    "large language model clinical",
    "AI radiology",
    "AI oncology",
]


def fetch_pubmed(max_per_query: int = 5) -> list[RawArticle]:
    all_articles: list[RawArticle] = []
    for query in QUERIES:
        try:
            ids = _search_ids(query, max_per_query)
            if not ids:
                continue
            all_articles.extend(_fetch_articles(ids))
        except Exception as exc:
            logger.warn("pubmed query failed", {"query": query, "err": str(exc)})
    return _dedupe_by_source_id(all_articles)


def fetch_pubmed_query(query: str, *, max_results: int = 10, year: int | None = None) -> list[RawArticle]:
    ids = _search_ids(query, max_results, year=year)
    if not ids:
        return []
    return _dedupe_by_source_id(_fetch_articles(ids))


def _search_ids(query: str, n: int, *, year: int | None = None) -> list[str]:
    params = {"db": "pubmed", "retmode": "json", "retmax": n, "sort": "date", "term": query}
    if year is not None:
        params.update({"mindate": f"{year}/01/01", "maxdate": f"{year}/12/31", "datetype": "pdat"})
    payload = get_json(
        ESEARCH,
        params=params,
        timeout=30,
    )
    return payload.get("esearchresult", {}).get("idlist", [])


def _fetch_articles(ids: list[str]) -> list[RawArticle]:
    xml = get_text(EFETCH, params={"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}, timeout=30)
    return _parse_pubmed_xml(xml)


def _parse_pubmed_xml(xml: str) -> list[RawArticle]:
    root = ElementTree.fromstring(xml)
    out: list[RawArticle] = []
    for item in root.findall(".//PubmedArticle"):
        try:
            medline = item.find("MedlineCitation")
            article = medline.find("Article") if medline is not None else None
            if medline is None or article is None:
                continue

            pmid = _node_text(medline.find("PMID"))
            if not pmid:
                continue

            out.append(
                {
                    "source": "pubmed",
                    "source_id": pmid,
                    "title": _node_text(article.find("ArticleTitle")).strip(),
                    "abstract": _extract_abstract(article),
                    "authors": _extract_authors(article.findall(".//Author")),
                    "published_date": _extract_date(article),
                    "doi": _extract_doi(item),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                }
            )
        except Exception as exc:
            logger.warn("pubmed parse failed", {"err": str(exc)})
    return out


def _node_text(node: ElementTree.Element | None) -> str:
    if node is None:
        return ""
    return "".join(node.itertext())


def _extract_abstract(article: ElementTree.Element) -> str:
    parts = [_node_text(node).strip() for node in article.findall(".//AbstractText")]
    return "\n\n".join(part for part in parts if part)


def _extract_authors(nodes: Iterable[ElementTree.Element]) -> list[str]:
    authors: list[str] = []
    for author in nodes:
        collective = _node_text(author.find("CollectiveName"))
        if collective:
            authors.append(collective)
            continue
        name = " ".join(part for part in [_node_text(author.find("ForeName")), _node_text(author.find("LastName"))] if part)
        if name:
            authors.append(name)
    return authors


def _extract_date(article: ElementTree.Element) -> str:
    node = article.find("ArticleDate")
    if node is None:
        node = article.find("./Journal/JournalIssue/PubDate")
    year = _node_text(node.find("Year") if node is not None else None)
    if not year:
        return date.today().isoformat()
    month = _node_text(node.find("Month") if node is not None else None) or "01"
    day = _node_text(node.find("Day") if node is not None else None) or "01"
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


def _extract_doi(item: ElementTree.Element) -> str | None:
    for article_id in item.findall(".//ArticleId"):
        if article_id.attrib.get("IdType") == "doi":
            doi = _node_text(article_id).strip()
            return doi or None
    return None


def _dedupe_by_source_id(articles: list[RawArticle]) -> list[RawArticle]:
    seen: set[str] = set()
    out: list[RawArticle] = []
    for article in articles:
        if article["source_id"] in seen:
            continue
        seen.add(article["source_id"])
        out.append(article)
    return out
