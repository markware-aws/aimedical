from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

from medical_news.types import RawArticle
from medical_news.util.http import get_text
from medical_news.util import logger

FEEDS: list[dict[str, str]] = []
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_rss() -> list[RawArticle]:
    if not FEEDS:
        return []
    out: list[RawArticle] = []
    for feed in FEEDS:
        try:
            xml = get_text(feed["url"], timeout=30)
            out.extend(_parse_rss(xml, feed["label"]))
        except Exception as exc:
            logger.warn("rss feed failed", {"feed": feed["label"], "err": str(exc)})
    return out


def _parse_rss(xml: str, label: str) -> list[RawArticle]:
    root = ElementTree.fromstring(xml)
    if root.tag.endswith("feed"):
        return [_atom_entry(entry, label) for entry in root.findall("atom:entry", ATOM_NS)]
    return [_rss_item(item, label) for item in root.findall(".//item")]


def _rss_item(item: ElementTree.Element, label: str) -> RawArticle:
    url = _child_text(item, "link")
    guid = _child_text(item, "guid") or url
    return {
        "source": "rss",
        "source_id": f"{label}:{guid}",
        "title": _child_text(item, "title").strip(),
        "abstract": (_child_text(item, "description") or _child_text(item, "summary")).strip(),
        "authors": [],
        "published_date": _normalize_date(_child_text(item, "pubDate")),
        "url": url,
    }


def _atom_entry(entry: ElementTree.Element, label: str) -> RawArticle:
    link = entry.find("atom:link", ATOM_NS)
    url = link.attrib.get("href", "") if link is not None else ""
    guid = _text(entry.find("atom:id", ATOM_NS)) or url
    return {
        "source": "rss",
        "source_id": f"{label}:{guid}",
        "title": _text(entry.find("atom:title", ATOM_NS)).strip(),
        "abstract": _text(entry.find("atom:summary", ATOM_NS)).strip(),
        "authors": [],
        "published_date": _normalize_date(_text(entry.find("atom:published", ATOM_NS))),
        "url": url,
    }


def _child_text(node: ElementTree.Element, child_name: str) -> str:
    return _text(node.find(child_name))


def _text(node: ElementTree.Element | None) -> str:
    return "".join(node.itertext()) if node is not None else ""


def _normalize_date(value: str) -> str:
    if not value:
        return datetime.now(timezone.utc).date().isoformat()
    if len(value) >= 10 and value[4] == "-":
        return value[:10]
    try:
        return parsedate_to_datetime(value).date().isoformat()
    except (TypeError, ValueError):
        return datetime.now(timezone.utc).date().isoformat()
