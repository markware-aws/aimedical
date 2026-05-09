from __future__ import annotations

from hashlib import sha256


def content_hash(*parts: str) -> str:
    h = sha256()
    for part in parts:
        h.update(part.encode("utf-8"))
    return h.hexdigest()[:16]
