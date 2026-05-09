from __future__ import annotations

import re
import unicodedata

from medical_news.types import RawArticle


GREEK_MAP = {
    "α": "a",
    "β": "v",
    "γ": "g",
    "δ": "d",
    "ε": "e",
    "ζ": "z",
    "η": "i",
    "θ": "th",
    "ι": "i",
    "κ": "k",
    "λ": "l",
    "μ": "m",
    "ν": "n",
    "ξ": "x",
    "ο": "o",
    "π": "p",
    "ρ": "r",
    "σ": "s",
    "ς": "s",
    "τ": "t",
    "υ": "y",
    "φ": "f",
    "χ": "ch",
    "ψ": "ps",
    "ω": "o",
    "ά": "a",
    "έ": "e",
    "ή": "i",
    "ί": "i",
    "ό": "o",
    "ύ": "y",
    "ώ": "o",
    "ϊ": "i",
    "ϋ": "y",
    "ΐ": "i",
    "ΰ": "y",
}


def dedup_key(article: RawArticle) -> str:
    doi = article.get("doi")
    if doi:
        return f"ARTICLE#{doi.lower()}"
    return f"ARTICLE#{article['source']}#{article['source_id']}"


def slugify(title: str) -> str:
    transliterated = "".join(GREEK_MAP.get(char, char) for char in title.lower())
    normalized = unicodedata.normalize("NFKD", transliterated)
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    slug = re.sub(r"[^a-z0-9]+", "-", without_marks.lower()).strip("-")
    return slug[:80]
