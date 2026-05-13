from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

from medical_news.types import RawArticle
from medical_news.util.http import request
from medical_news.util import logger

FEEDS: list[dict[str, str]] = [
    {"label": "npj-digital-medicine", "url": "https://feeds.nature.com/npjdigitalmed/rss/current"},
    {"label": "lancet-digital-health", "url": "https://www.thelancet.com/rssfeed/landig_current.xml"},
    {"label": "radiology-ai", "url": "https://radiologyai.substack.com/feed"},
]
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_rss() -> list[RawArticle]:
    return fetch_labeled_feeds(FEEDS)


def fetch_labeled_feeds(feeds: list[dict[str, str]]) -> list[RawArticle]:
    """Fetch RSS/Atom URLs. Each dict must include ``label`` and ``url`` keys."""
    if not feeds:
        return []
    out: list[RawArticle] = []
    for feed in feeds:
        label = feed.get("label") or "rss"
        url = feed.get("url")
        if not url:
            continue
        try:
            xml = _fetch_feed_xml(url)
            out.extend(_parse_rss(xml, label))
        except Exception as exc:
            logger.warn("rss feed failed", {"feed": label, "err": str(exc)})
    return out


def _fetch_feed_xml(url: str) -> str:
    status, text = request(
        "GET",
        url,
        headers={
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
            "User-Agent": "Mozilla/5.0 compatible; AIMedicalNewsBot/0.1; +https://aimedical.gr",
        },
        timeout=30,
    )
    if status < 200 or status >= 300:
        raise RuntimeError(f"GET {url} failed: {status} {text}")
    return text


def _parse_rss(xml: str, label: str) -> list[RawArticle]:
    root = ElementTree.fromstring(xml)
    if root.tag.endswith("feed"):
        return [_atom_entry(entry, label) for entry in root.findall("atom:entry", ATOM_NS)]
    return [_rss_item(item, label) for item in _find_all(root, "item")]


def _rss_item(item: ElementTree.Element, label: str) -> RawArticle:
    url = _child_text(item, "link")
    guid = _child_text(item, "guid") or url
    author = _child_text(item, "creator") or _child_text(item, "author")
    return {
        "source": "rss",
        "source_id": f"{label}:{guid}",
        "title": _clean_text(_child_text(item, "title")),
        "abstract": _clean_text(
            _child_text(item, "description") or _child_text(item, "summary") or _child_text(item, "encoded")
        ),
        "authors": [author] if author else [],
        "published_date": _normalize_date(
            _child_text(item, "pubDate") or _child_text(item, "date") or _child_text(item, "publicationDate")
        ),
        "url": url,
    }


def _atom_entry(entry: ElementTree.Element, label: str) -> RawArticle:
    link = _atom_link(entry)
    url = link.attrib.get("href", "") if link is not None else ""
    guid = _text(entry.find("atom:id", ATOM_NS)) or url
    return {
        "source": "rss",
        "source_id": f"{label}:{guid}",
        "title": _clean_text(_text(entry.find("atom:title", ATOM_NS))),
        "abstract": _clean_text(_text(entry.find("atom:summary", ATOM_NS))),
        "authors": [
            author
            for author in (_text(author.find("atom:name", ATOM_NS)).strip() for author in entry.findall("atom:author", ATOM_NS))
            if author
        ],
        "published_date": _normalize_date(_text(entry.find("atom:published", ATOM_NS))),
        "url": url,
    }


def _child_text(node: ElementTree.Element, child_name: str) -> str:
    for child in node:
        if _local_name(child.tag) == child_name:
            return _text(child)
    return ""


def _text(node: ElementTree.Element | None) -> str:
    return "".join(node.itertext()) if node is not None else ""


def _atom_link(entry: ElementTree.Element) -> ElementTree.Element | None:
    links = entry.findall("atom:link", ATOM_NS)
    for link in links:
        if link.attrib.get("rel", "alternate") == "alternate":
            return link
    return links[0] if links else None


def _find_all(node: ElementTree.Element, child_name: str) -> list[ElementTree.Element]:
    return [child for child in node.iter() if _local_name(child.tag) == child_name]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _clean_text(value: str) -> str:
    text = html.unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())


def _normalize_date(value: str) -> str:
    if not value:
        return datetime.now(timezone.utc).date().isoformat()
    if len(value) >= 10 and value[4] == "-":
        return value[:10]
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        return datetime.now(timezone.utc).date().isoformat()
