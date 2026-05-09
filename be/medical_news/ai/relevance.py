from __future__ import annotations

import json
from typing import Any

from medical_news.ai.openai_client import chat_json
from medical_news.ai.prompts import RELEVANCE_SYSTEM, relevance_user_prompt
from medical_news.types import RawArticle, RelevanceResult

VALID_CATEGORIES: set[str] = {
    "oncology",
    "cardiology",
    "neurology",
    "hepatology",
    "immunology",
    "diagnostics",
    "radiology",
    "llms",
    "drug-discovery",
    "robotics",
    "digital-health",
    "public-health",
    "women-health",
    "other",
}

def score(article: RawArticle) -> RelevanceResult:
    content = chat_json(
        temperature=0.2,
        messages=[
            {"role": "system", "content": RELEVANCE_SYSTEM},
            {
                "role": "user",
                "content": relevance_user_prompt(article["title"], article["abstract"], article["source"]),
            },
        ],
    )
    parsed: dict[str, Any] = json.loads(content or "{}")
    category = parsed.get("category") if parsed.get("category") in VALID_CATEGORIES else "other"
    raw_score = parsed.get("score")
    return {
        "relevant": bool(parsed.get("relevant")),
        "score": raw_score if isinstance(raw_score, (int, float)) else 0,
        "category": category,  # type: ignore[typeddict-item]
        "reason": parsed.get("reason") if isinstance(parsed.get("reason"), str) else "",
    }
