from __future__ import annotations

import json
from typing import Any

from medical_news.ai.deepl_client import translate_title_to_greek
from medical_news.ai.openai_client import chat_json
from medical_news.ai.prompts import GENERATOR_SYSTEM, generator_user_prompt
from medical_news.types import GreekArticle, RawArticle
from medical_news.util import logger


def generate_greek(article: RawArticle) -> GreekArticle:
    content = chat_json(
        temperature=0.5,
        messages=[
            {"role": "system", "content": GENERATOR_SYSTEM},
            {"role": "user", "content": generator_user_prompt(article)},
        ],
    )
    parsed: dict[str, Any] = json.loads(content or "{}")

    title = parsed.get("titleGr")
    body = parsed.get("body")
    if not title or not body:
        raise ValueError("generator returned incomplete article")

    deepl_title = _translate_title(article["title"])

    return {
        "title_gr": deepl_title or str(title),
        "subtitle_gr": str(parsed.get("subtitleGr") or ""),
        "description_gr": str(parsed.get("descriptionGr") or ""),
        "body": str(body),
        "tags": [str(tag) for tag in parsed.get("tags", [])] if isinstance(parsed.get("tags"), list) else [],
        "conditions": [str(item) for item in parsed.get("conditions", [])]
        if isinstance(parsed.get("conditions"), list)
        else [],
        "key_findings": [str(item) for item in parsed.get("keyFindings", [])]
        if isinstance(parsed.get("keyFindings"), list)
        else [],
        "limitations": str(parsed.get("limitations") or ""),
        "clinical_significance": str(parsed.get("clinicalSignificance") or ""),
    }


def _translate_title(title: str) -> str | None:
    try:
        return translate_title_to_greek(title)
    except Exception as exc:
        logger.warn("deepl title translation failed", {"err": str(exc)})
        return None
