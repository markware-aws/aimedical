from __future__ import annotations

import os
from typing import Any

from medical_news.util.http import request_json

OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


def chat_json(*, messages: list[dict[str, str]], temperature: float) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("missing env OPENAI_API_KEY")

    payload: dict[str, Any] = request_json(
        "POST",
        OPENAI_CHAT_COMPLETIONS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
        },
        json_body={
            "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "messages": messages,
        },
        timeout=120,
    )
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return "{}"
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    return content if isinstance(content, str) else "{}"
