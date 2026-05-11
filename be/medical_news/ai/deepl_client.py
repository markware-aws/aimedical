from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEEPL_FREE_URL = "https://api-free.deepl.com/v2/translate"
DEEPL_PRO_URL = "https://api.deepl.com/v2/translate"


def translate_title_to_greek(title: str) -> str | None:
    api_key = os.environ.get("DEEPL_API_KEY")
    if not api_key:
        return None

    text = title.strip()
    if not text:
        return None

    payload = urlencode(
        {
            "text": text,
            "source_lang": "EN",
            "target_lang": "EL",
            "preserve_formatting": "1",
        }
    ).encode("utf-8")

    req = Request(
        _deepl_url(api_key),
        data=payload,
        headers={
            "Authorization": f"DeepL-Auth-Key {api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=30) as res:
            body = res.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepL title translation failed: {exc.code} {detail}") from exc

    data = json.loads(body)
    translations = data.get("translations")
    if not isinstance(translations, list) or not translations:
        return None

    translated = translations[0].get("text") if isinstance(translations[0], dict) else None
    return _clean_title(_restore_common_terms(translated, text)) if isinstance(translated, str) else None


def _deepl_url(api_key: str) -> str:
    if os.environ.get("DEEPL_API_URL"):
        return os.environ["DEEPL_API_URL"]
    return DEEPL_FREE_URL if api_key.endswith(":fx") else DEEPL_PRO_URL


def _clean_title(title: str) -> str:
    cleaned = " ".join(title.strip().strip('"').split())
    return cleaned[:-1] if cleaned.endswith(".") else cleaned


def _restore_common_terms(translated: str, source: str) -> str:
    source_lower = source.lower()
    restored = translated

    if "conversational ai" in source_lower:
        restored = re.sub(
            r"διαλογικό σύστημα τεχνητής νοημοσύνης",
            "σύστημα Conversational AI",
            restored,
            flags=re.IGNORECASE,
        )
        restored = re.sub(r"διαλογική τεχνητή νοημοσύνη", "Conversational AI", restored, flags=re.IGNORECASE)

    if "large language models" in source_lower or "llms" in source_lower:
        restored = re.sub(
            r"(?:μεγάλων|μεγάλα|μεγάλου|μεγάλο)\s+γλωσσικ\w+\s+μοντέλ\w+",
            "LLMs",
            restored,
            flags=re.IGNORECASE,
        )
    elif "large language model" in source_lower or "llm" in source_lower:
        restored = re.sub(
            r"(?:μεγάλου|μεγάλο)\s+γλωσσικ\w+\s+μοντέλ\w+",
            "LLM",
            restored,
            flags=re.IGNORECASE,
        )

    if "artificial intelligence" in source_lower or re.search(r"(?<![a-z])ai(?![a-z])", source_lower):
        restored = re.sub(r"\bΤεχνητή νοημοσύνη\b", "AI", restored)
        restored = re.sub(r"\bτεχνητή νοημοσύνη\b", "AI", restored)
        restored = re.sub(r"\bτεχνητής νοημοσύνης\b", "AI", restored)

    return restored
