"""Recent human drug approvals via openFDA Drugs@FDA (drugsfda dataset).

Fetches ORIG (original application) approvals in a date window. Defaults to Type 1
(New Molecular Entity) submissions — use ``nme_only=False`` for every original approval.
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

from medical_news.types import RawArticle
from medical_news.util import logger

OPENFDA_ENDPOINT = "https://api.fda.gov/drug/drugsfda.json"
OPENFDA_LABEL_ENDPOINT = "https://api.fda.gov/drug/label.json"


def fetch_recent_drug_approvals(
    *,
    since_yyyymmdd: str | None,
    until_yyyymmdd: str | None,
    days: int | None,
    max_results: int,
    nme_only: bool = True,
) -> list[RawArticle]:
    start, end = _resolve_range(since_yyyymmdd, until_yyyymmdd, days)
    out: list[RawArticle] = []
    skip = 0

    api_key = (os.environ.get("OPENFDA_API_KEY") or "").strip() or None

    while len(out) < max_results:
        chunk = min(100, max(1, max_results - len(out)))
        params = _search_params(start, end, nme_only, limit=chunk, skip=skip, api_key=api_key)
        payload = _openfda_json(params)

        hits = payload.get("results") or []
        meta = payload.get("meta") or {}
        info = meta.get("results") or {}
        total = info.get("total") or 0

        if not hits:
            break

        for rec in hits:
            if len(out) >= max_results:
                break
            raw = _record_to_article(rec, start, end, nme_only)
            if raw is None:
                continue
            out.append(raw)

        skip += chunk
        if skip >= total or not hits:
            break

    out.sort(key=lambda a: a["published_date"], reverse=True)
    return out


def _resolve_range(
    since: str | None,
    until: str | None,
    days: int | None,
) -> tuple[str, str]:
    if since or until:
        if not since or not until:
            raise ValueError("Either pass both --since and --until, or omit them and use --days.")
        if len(since) != 8 or len(until) != 8 or not since.isdigit() or not until.isdigit():
            raise ValueError("--since/--until must be YYYYMMDD (FDA openFDA date format).")
        return since, until

    n = days if days is not None else 90
    end_d = date.today()
    start_d = end_d - timedelta(days=n)
    return start_d.strftime("%Y%m%d"), end_d.strftime("%Y%m%d")


def _search_params(
    since: str,
    until: str,
    nme_only: bool,
    *,
    limit: int,
    skip: int,
    api_key: str | None,
) -> dict[str, Any]:
    date_range = f"submissions.submission_status_date:[{since} TO {until}]"
    clauses = [
        "submissions.submission_type:ORIG",
        "submissions.submission_status:AP",
        date_range,
    ]
    if nme_only:
        clauses.append('submissions.submission_class_code:"TYPE 1"')
    params: dict[str, Any] = {
        "search": " AND ".join(clauses),
        "limit": limit,
        "skip": skip,
    }
    if api_key:
        params["api_key"] = api_key
    return params


def _openfda_json(params: dict[str, Any]) -> dict[str, Any]:
    from medical_news.util.http import get_json

    try:
        payload = get_json(OPENFDA_ENDPOINT, params=params, timeout=45)
    except Exception as exc:
        logger.warn("openFDA request failed", {"err": str(exc)})
        raise

    err = payload.get("error") if isinstance(payload, dict) else None
    if err:
        raise RuntimeError(str(err))
    return payload


def resolve_drugsfda_application_full_id(application_digits: str, *, api_key: str | None = None) -> str | None:
    """Map Drugs@FDA ``ApplNo`` digits (URL) → ``NDA``/``BLA``/… id via drugsfda wildcard search."""

    digits = "".join(ch for ch in application_digits if ch.isdigit())
    if not digits:
        return None
    params: dict[str, Any] = {"search": f"application_number:*{digits}*", "limit": 1}
    if api_key := (api_key if api_key is not None else (os.environ.get("OPENFDA_API_KEY") or "").strip() or None):
        params["api_key"] = api_key
    try:
        payload = _openfda_json(params)
    except Exception:
        return None
    hits = payload.get("results") or []
    if not hits or not isinstance(hits[0], dict):
        return None
    return _str_or_empty(hits[0].get("application_number")) or None


def fetch_label_indication_excerpt(application_full_id: str, *, api_key: str | None = None) -> str:
    """Public wrapper for SPL ``INDICATIONS AND USAGE`` excerpt (english)."""

    ak = api_key if api_key is not None else (os.environ.get("OPENFDA_API_KEY") or "").strip() or None
    return _fetch_label_indication_excerpt(application_full_id, ak)


def _application_digits(application_number: str) -> str:
    digits = "".join(ch for ch in application_number if ch.isdigit())
    return digits.strip()


def _label_search_clauses(application_number: str) -> list[str]:
    """openFDA labeling index quirks: try full id then digits-only and wildcards."""

    normalized = "".join(application_number.upper().split())
    digs = _application_digits(normalized)

    clauses: list[str] = []
    seen: set[str] = set()

    def add(clause: str) -> None:
        if clause and clause not in seen:
            seen.add(clause)
            clauses.append(clause)

    if normalized.startswith(("NDA", "BLA", "ANDA")) and digs:
        add(f"openfda.application_number:{normalized}")
        add(f"(openfda.application_number:{normalized})")
        add(f"(openfda.application_number:{normalized} OR application_number:{digs})")

    # Some labels index only numeric portion
    if digs:
        add(f"openfda.application_number:{digs}")
        add(f"openfda.application_number:*{digs}*")
        add(f"{digs}")  # default field search fallback

    if not clauses:
        add(f'openfda.application_number:"{_str_or_empty(application_number)}"')
    return clauses


def _label_json_to_excerpt(payload: dict[str, Any]) -> str:
    results = payload.get("results") or []
    if not results or not isinstance(results[0], dict):
        return ""
    iu = results[0].get("indications_and_usage")
    if not iu or not isinstance(iu, list) or not iu:
        return ""
    squished = _squish_whitespace(_str_or_empty(iu[0]))
    max_chars = 1100
    if len(squished) > max_chars:
        squished = squished[: max_chars - 3].rstrip() + "..."
    return squished


def _fetch_label_indication_excerpt(application_number: str, api_key: str | None) -> str:
    """Best-effort: pull INDICATIONS AND USAGE from openFDA SPL (drug/label.json)."""

    import re

    from medical_news.util.http import get_json

    from_num = "".join(application_number.upper().split())
    m = re.match(r"^(NDA|BLA|ANDA)(\d{4,})$", from_num, re.IGNORECASE)
    if not m:
        digs = _application_digits(from_num)
        from_num = f"NDA{digs}" if digs else from_num

    last_error: dict[str, Any] | None = None
    for clause in _label_search_clauses(from_num):
        params: dict[str, Any] = {"search": clause, "limit": 1}
        if api_key:
            params["api_key"] = api_key

        try:
            payload = get_json(OPENFDA_LABEL_ENDPOINT, params=params, timeout=45)
        except Exception as exc:
            logger.warn(
                "openFDA label lookup request failed",
                {"applicationNumber": application_number, "search": clause, "err": str(exc)},
            )
            continue

        err = payload.get("error") if isinstance(payload, dict) else None
        if err:
            last_error = err if isinstance(err, dict) else {"detail": err}
            continue

        excerpt = _label_json_to_excerpt(payload)
        if excerpt:
            return excerpt

    if last_error:
        logger.warn(
            "openFDA label lookup returned error (after retries)",
            {"applicationNumber": application_number, "err": last_error},
        )

    return ""


def _squish_whitespace(text: str) -> str:
    return " ".join(text.split())


def _record_to_article(
    rec: dict[str, Any],
    range_start_yyyymmdd: str,
    range_end_yyyymmdd: str,
    nme_only: bool,
) -> RawArticle | None:
    appl = _str_or_empty(rec.get("application_number"))
    if not appl:
        return None

    sub = _matching_submission(rec, range_start_yyyymmdd, range_end_yyyymmdd, nme_only)
    if sub is None:
        return None

    status_dt = sub.get("submission_status_date") or ""
    if len(status_dt) == 8 and status_dt.isdigit():
        published_date = f"{status_dt[:4]}-{status_dt[4:6]}-{status_dt[6:]}"
    else:
        published_date = date.today().isoformat()

    sponsor = _str_or_empty(rec.get("sponsor_name"))

    brands, generics = _product_summaries(rec.get("products") or [])
    brand0 = brands.split(",")[0].strip() if brands else ""
    gen0 = generics.split(",")[0].strip() if generics else ""

    api_key = (os.environ.get("OPENFDA_API_KEY") or "").strip() or None
    label_excerpt = _fetch_label_indication_excerpt(appl, api_key)

    class_desc = _str_or_empty(sub.get("submission_class_code_description"))
    letter_url = _first_doc_url(sub.get("application_docs") or [])

    titles: list[str] = ["FDA Drugs@FDA", "ORIG approval", appl]
    if brand0:
        titles.append(brand0)
    if gen0 and gen0.casefold() != brand0.casefold():
        titles.append(f"({gen0})")

    url = drugsatfda_application_url(appl)

    letters = f"Approval-letter URL: {letter_url}\n\n" if letter_url else ""

    abstract = (
        "This summary is sourced from FDA openFDA Drugs@FDA metadata (daily JSON export); "
        "it is administrative approval information, not a peer-reviewed publication.\n\n"
        f"Application number: {appl}\n"
        f"Sponsor: {sponsor or 'unknown'}\n"
        f"Original submission classification: {class_desc or 'not specified'}\n"
        f"Submission status-date (FDA): {status_dt}\n"
        + (f"{letters}")
        + f"Brands/products: {brands or 'unknown'}\n"
        + f"Active ingredients / generic names: {generics or 'unknown'}\n\n"
        f"Publication window queried: {_fmt_range_label(range_start_yyyymmdd, range_end_yyyymmdd)}.\n\n"
        f"Preferred canonical reference for readers: Drugs@FDA application overview ({url})."
    )
    if label_excerpt:
        abstract += (
            "\n\nFDA SPL label — INDICATIONS AND USAGE (English excerpt; confirm full prescribing information):\n"
            + label_excerpt
        )

    return {
        "source": "fda",
        "source_id": f"{appl}:{status_dt}",
        "title": " ".join(titles),
        "abstract": abstract,
        "authors": [sponsor] if sponsor else [],
        "published_date": published_date,
        "url": url,
        "bypass_relevance": True,
        "category_override": "drug-discovery",
    }


def _matching_submission(
    rec: dict[str, Any],
    range_start: str,
    range_end: str,
    nme_only: bool,
) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_date = ""

    for sub in rec.get("submissions") or []:
        if not isinstance(sub, dict):
            continue
        if sub.get("submission_type") != "ORIG" or sub.get("submission_status") != "AP":
            continue
        if nme_only and sub.get("submission_class_code") != "TYPE 1":
            continue
        sd = sub.get("submission_status_date") or ""
        if not sd or len(sd) != 8:
            continue
        if sd < range_start or sd > range_end:
            continue
        if sd > best_date:
            best_date = sd
            best = sub

    return best


def _product_summaries(products: list[Any]) -> tuple[str, str]:
    brands: list[str] = []
    gens: list[str] = []

    for p in products:
        if not isinstance(p, dict):
            continue
        b = _str_or_empty(p.get("brand_name"))
        if b:
            brands.append(b)
        for ai in p.get("active_ingredients") or []:
            if isinstance(ai, dict):
                nm = _str_or_empty(ai.get("name"))
                if nm:
                    gens.append(nm)

    return _uniq_join(brands), _uniq_join(gens)


def _uniq_join(vals: list[str]) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for v in vals:
        key = v.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return ", ".join(out)


def _first_doc_url(docs: list[Any]) -> str:
    preferred = ""
    fallback = ""
    for d in docs:
        if not isinstance(d, dict):
            continue
        url = _str_or_empty(d.get("url"))
        if not url:
            continue
        if not fallback:
            fallback = url
        dtype = _str_or_empty(d.get("type")).lower()
        if dtype == "letter":
            preferred = url
            break
    return preferred or fallback


def _fmt_range_label(a: str, b: str) -> str:
    if len(a) == 8 and len(b) == 8:
        return f"{a[:4]}-{a[4:6]}-{a[6:]} to {b[:4]}-{b[4:6]}-{b[6:]}"
    return f"{a}–{b}"


def drugsatfda_application_url(application_number: str) -> str:
    digits = "".join(ch for ch in application_number if ch.isdigit())
    if not digits:
        digits = application_number.strip()
    return (
        "https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?"
        f"event=overview.process&ApplNo={digits}"
    )


def _str_or_empty(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()

