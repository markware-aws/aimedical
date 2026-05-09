from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def request(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    json_body: Any | None = None,
    timeout: int = 30,
) -> tuple[int, str]:
    if params:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{urlencode(params)}"

    body = None
    request_headers = dict(headers or {})
    if json_body is not None:
        body = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")

    req = Request(url, data=body, headers=request_headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as res:
            return res.status, res.read().decode("utf-8")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def get_text(url: str, *, params: dict[str, Any] | None = None, timeout: int = 30) -> str:
    status, text = request("GET", url, params=params, timeout=timeout)
    if status < 200 or status >= 300:
        raise RuntimeError(f"GET {url} failed: {status} {text}")
    return text


def get_json(url: str, *, params: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    return json.loads(get_text(url, params=params, timeout=timeout))


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    json_body: Any | None = None,
    timeout: int = 30,
) -> Any:
    status, text = request(method, url, headers=headers, json_body=json_body, timeout=timeout)
    if status < 200 or status >= 300:
        raise RuntimeError(f"{method} {url} failed: {status} {text}")
    return json.loads(text) if text else {}
