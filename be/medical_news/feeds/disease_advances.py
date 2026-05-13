"""RSS/Atom feeds for curated disease breakthroughs — low-frequency sources you run manually.

Edit ``ADVANCE_FEEDS`` with society / foundation URLs that expose RSS (see each site's feed link).
Optional ``category`` must match Astro frontmatter categories (see ``ArticleCategory`` in types).

**Verified recently** with ``_fetch_feed_xml`` + ``_parse_rss`` in this repo: NCI syndication URLs (official
[Cancer.gov RSS listings](https://www.cancer.gov/syndication/rss)), WHO English news,
`Nature Medicine` ToC RSS, Crohn's & Colitis Foundation, JDRF.

Many US federal ``.gov`` sites fail TLS verification behind some corporate proxies; if that happens locally,
omit those feeds or fix the Python trust store—the same URLs often work from Lambda/Linux CI.
"""

from __future__ import annotations

from typing import cast

from medical_news.ai.relevance import VALID_CATEGORIES
from medical_news.feeds.rss import fetch_labeled_feeds
from medical_news.types import ArticleCategory, RawArticle


def _coerce_category(raw: str | None) -> ArticleCategory:
    v = raw or "other"
    return cast(ArticleCategory, v) if v in VALID_CATEGORIES else "other"


# Curated defaults (good signal / official or major journal; tune ``--max-per-source`` when running).
ADVANCE_FEEDS: list[dict[str, str]] = [
    {
        "label": "who-news",
        "url": "https://www.who.int/rss-feeds/news-english.xml",
        "category": "public-health",
    },
    {
        "label": "nci-news-releases",
        "url": "https://www.cancer.gov/publishedcontent/rss/syndication/rss/ncinewsreleases.rss",
        "category": "oncology",
    },
    {
        "label": "nci-cancer-currents",
        "url": "https://www.cancer.gov/publishedcontent/rss/news-events/cancer-currents-blog.rss",
        "category": "oncology",
    },
    {
        "label": "jdrf",
        "url": "https://www.jdrf.org/rss/",
        "category": "immunology",
    },
    {
        "label": "nature-medicine",
        "url": "https://www.nature.com/nm.rss",
        "category": "other",
    },
]


def fetch_disease_advance_candidates(
    *,
    featured: bool = True,
) -> list[RawArticle]:
    """Fetch curated feeds and mark items for bypass-relevance pipeline + optional auto-feature."""
    feeds = [{"label": entry["label"], "url": entry["url"]} for entry in ADVANCE_FEEDS]
    articles = fetch_labeled_feeds(feeds)
    label_category = _label_to_category_map()
    for article in articles:
        label = article["source_id"].split(":", 1)[0]
        cat = label_category.get(label, "other")
        article["bypass_relevance"] = True
        article["category_override"] = cat
        if featured:
            article["featured"] = True
    return articles


def _label_to_category_map() -> dict[str, ArticleCategory]:
    mapping: dict[str, ArticleCategory] = {}
    for entry in ADVANCE_FEEDS:
        label = entry["label"]
        mapping[label] = _coerce_category(entry.get("category"))
    return mapping
