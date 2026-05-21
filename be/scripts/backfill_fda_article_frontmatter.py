#!/usr/bin/env python3
"""Refresh ``source: fda`` MDX frontmatter using openFDA + Wikidata (no OpenAI).

Updates ``title`` (pattern: ``{lead} - Έγκριση BRAND (INNs) από τον FDA`` where ``lead``
preferentially uses a Wikidata Greek label of the heuristic indication phrase),

``tags`` (English condition phrase first),

``conditions`` (Greek Wikidata hint when possible),

plus one ``keyFindings`` SPL summary line—while keeping the Markdown body unchanged.

Dry-run::

  PYTHONIOENCODING=utf-8 python scripts/backfill_fda_article_frontmatter.py

Apply::

  PYTHONIOENCODING=utf-8 python scripts/backfill_fda_article_frontmatter.py --apply
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import OrderedDict
from pathlib import Path
from typing import Any

import yaml

BE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BE_ROOT.parent
FE_ARTICLES = REPO_ROOT / "fe" / "src" / "content" / "articles"

_APPRO_RE = re.compile(r"\b(NDA\d+|BLA\d+|ANDA\d+)\b", re.IGNORECASE)
_APPL_FROM_URL_RE = re.compile(r"ApplNo=(\d+)", re.IGNORECASE)
_SOURCE_FDA = re.compile(r"(?m)^source:\s*[\"']fda[\"']\s*$")
_ORIG_LINE_RE = re.compile(
    r"FDA Drugs@FDA ORIG approval (?:NDA|BLA|ANDA)(\d+)\s+([^\s]+)\s+\(([^)]*)\)",
    re.IGNORECASE | re.DOTALL,
)


def repo_rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def inject_syspath() -> None:
    if str(BE_ROOT) not in sys.path:
        sys.path.insert(0, str(BE_ROOT))


def split_fm(raw_text: str) -> tuple[str, str]:
    text = raw_text.lstrip("\ufeff")
    if not text.startswith("---"):
        raise ValueError("needs --- frontmatter")
    divider = "\n---\n"
    close = text.find(divider, 4)
    if close == -1:
        raise ValueError("closing --- missing")
    inner = text[4:close].strip("\n") + "\n"
    body = text[close + len(divider) :]
    return inner, body


def squish(txt: str) -> str:
    return " ".join(txt.split())


def extract_application(full_fm: dict[str, Any], api_key: str | None) -> str | None:
    inject_syspath()
    from medical_news.feeds.fda_drugsfda import resolve_drugsfda_application_full_id

    english = str(full_fm.get("originalTitle") or "")
    probe = _APPRO_RE.search(english)
    if probe:
        return probe.group(1).upper()
    for bullet in full_fm.get("keyFindings") or []:
        line = str(bullet)
        hit = _APPRO_RE.search(line)
        if hit:
            return hit.group(1).upper()
        if "αίτησης:" not in line.lower():
            continue
        tail = line.split(":", 1)[1].strip()
        digits_only = "".join(ch for ch in tail if ch.isdigit())
        if digits_only:
            resolved = resolve_drugsfda_application_full_id(digits_only, api_key=api_key)
            if resolved:
                return resolved
        hit = _APPRO_RE.search(tail)
        if hit:
            return hit.group(1).upper()

    mn = _APPL_FROM_URL_RE.search(str(full_fm.get("sourceUrl") or ""))
    if mn:
        return resolve_drugsfda_application_full_id(mn.group(1), api_key=api_key) or None
    return None


def parse_brand_inn(original_title: str) -> tuple[str, str]:
    mc = _ORIG_LINE_RE.search(original_title.strip())
    if not mc:
        return "", ""
    brand_token = mc.group(2).strip().upper()
    inn_chunk = squish(mc.group(3))
    inn_chunk = inn_chunk.replace("\n", " ").strip(",").strip(";")
    return brand_token, inn_chunk


def shorten_words(text: str, limit: int) -> str:
    words = text.split()
    out: list[str] = []
    for w in words:
        tentative = squish(" ".join(out + [w]))
        if len(tentative) <= limit:
            out.append(w)
        else:
            break
    return squish(" ".join(out))


def shorten_clause(text: str, limit: int = 118) -> str:
    clipped = squish(text)
    clipped = clipped.rstrip(",; ").strip('"').strip("'")
    if len(clipped) <= limit:
        return clipped
    cutoff = clipped.rfind(",", 40, limit + 48)
    if cutoff > 12:
        return squish(clipped[:cutoff]).rstrip(", ")
    return shorten_words(clipped, limit)


def isolate_indicated_fragment(text: str) -> str:
    """Prefer the clinician-facing clause (after INDICATION header noise)."""
    s = squish(text)
    lower = s.lower()
    anchors = ("is indicated for ", "are indicated for ", "is indicated ", "are indicated ")
    best = len(s)
    for needle in anchors:
        idx = lower.find(needle)
        if idx != -1 and idx < best:
            best = idx
    return s[best:].strip() if best < len(s) else s


def core_indication_sentence(blob: str) -> str:
    cleaned = isolate_indicated_fragment(blob.strip())
    lowered = cleaned.lower()
    prefixes = (
        "is indicated for the treatment of ",
        "indicated for the treatment of ",
        "is indicated for ",
        "indicated for ",
    )
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return squish(cleaned[len(prefix) :]).split(".")[0]
    snippet = cleaned.lstrip()
    snippet = re.sub(r"^[0-9IVX\.\)\s\-]+", "", snippet)
    return squish(snippet.split(".")[0])


def tag_from_indication_sentence(sentence: str) -> str:
    clipped = shorten_clause(sentence, limit=420)
    for marker in (
        " in adults",
        " in pediatric patients",
        " in pediatrics",
        " in children",
        " when ",
        " with ",
        " followed by ",
    ):
        pos = clipped.lower().find(marker)
        if pos != -1:
            clipped = clipped[:pos]
            break
    tag = clipped.lower().strip(";,. ")
    if len(tag) > 98:
        tag = tag[:96].rsplit(",", 1)[0]
    tag = shorten_words(tag.replace(",", " "), limit=94)
    return tag


def wikidata_greek(first_pass: str) -> str | None:
    clipped = shorten_clause(first_pass.split(".")[0], limit=360)
    queue: list[str] = []
    for candidate in (clipped, " ".join(first_pass.split()[:10]), " ".join(first_pass.split()[:6])):
        cand = squish(candidate).strip()
        if len(cand) < 10:
            continue
        lowered = cand.lower()
        if not any(existing.lower() == lowered for existing in queue):
            queue.append(cand)

    seen_entities: set[str] = set()
    for needle in queue:
        data: dict[str, Any] = {}
        try:
            raw = urllib.request.Request(
                "https://www.wikidata.org/w/api.php?"
                + urllib.parse.urlencode(
                    {
                        "action": "wbsearchentities",
                        "format": "json",
                        "limit": "5",
                        "language": "en",
                        "search": needle[:200],
                        "origin": "*",
                    }
                ),
                headers={
                    "User-Agent": random.choice(
                        ("AIMEDICALFDAfrontfill/1.0 (local script)",),
                    ),
                },
            )
            with urllib.request.urlopen(raw, timeout=25) as response:
                data = json.loads(response.read())
        except Exception:
            time.sleep(0.2)
            continue

        time.sleep(0.3)
        for hit in data.get("search") or []:
            qid = hit.get("id")
            if not qid or qid in seen_entities:
                continue
            seen_entities.add(qid)

            lbl_req = urllib.request.Request(
                "https://www.wikidata.org/w/api.php?"
                + urllib.parse.urlencode(
                    {
                        "action": "wbgetentities",
                        "format": "json",
                        "ids": qid,
                        "props": "labels",
                        "languages": "el|en",
                        "origin": "*",
                    }
                ),
                headers={
                    "User-Agent": random.choice(
                        ("AIMEDICALFDAfrontfill/1.0 (local script)",),
                    ),
                },
            )
            try:
                with urllib.request.urlopen(lbl_req, timeout=25) as response:
                    ent = json.loads(response.read())
                block = (((ent.get("entities") or {}).get(qid) or {}).get("labels")) or {}
                label = ""
                if "el" in block:
                    label = squish(block["el"].get("value") or "").strip()

                time.sleep(0.25)

                if label:
                    return label
            except Exception:
                continue
    return None


_FM_SEQUENCE = (
    "title",
    "originalTitle",
    "subtitle",
    "date",
    "description",
    "category",
    "tags",
    "conditions",
    "keyFindings",
    "studyLimitations",
    "clinicalSignificance",
    "sourceUrl",
    "doi",
    "source",
    "published",
    "generated",
    "featured",
    "heroImage",
)


def reorder(data: dict[str, Any]) -> OrderedDict[str, Any]:
    out: OrderedDict[str, Any] = OrderedDict()
    for field in _FM_SEQUENCE:
        if field in data:
            out[field] = data[field]
    for leftover in data:
        if leftover not in out:
            out[leftover] = data[leftover]
    return out


def dedupe(lst: list[str], *, lowercase: bool) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in lst:
        token = squish(item)
        checker = token.lower() if lowercase else token
        if checker and checker not in seen:
            seen.add(checker)
            result.append(token)
    return result


def remove_old_spl_bullets(findings: list[str]) -> list[str]:
    keeper: list[str] = []
    for line in findings:
        s = str(line)
        if s.startswith(
            ("Ένδειξη (FDA SPL",),
        ):
            continue
        keeper.append(line)
    return keeper


def build_frontmatter(
    base: OrderedDict[str, Any],
    *,
    lead: str,
    brand: str,
    inn_piece: str,
    tag_piece: str,
    greek_label: str | None,
    spl_summary: str,
) -> OrderedDict[str, Any]:
    inn_trim = inn_piece.strip() if inn_piece.strip() else brand.strip()

    mutated = reorder(dict(base.items()))
    mutated["title"] = f"{squish(lead)} - Έγκριση {brand.strip()} ({inn_trim}) από τον FDA"

    old_tags = list(mutated.get("tags") or [])
    mutated["tags"] = dedupe([tag_piece, *old_tags], lowercase=True)

    old_conditions = list(mutated.get("conditions") or [])
    merged_conditions = [greek_label.strip(), *old_conditions] if greek_label else old_conditions

    mutated["conditions"] = dedupe([c for c in merged_conditions if c], lowercase=False)

    findings_list = remove_old_spl_bullets(list(mutated.get("keyFindings") or []))
    clipped_spl = squish(spl_summary)
    if len(clipped_spl) > 470:
        clipped_spl = clipped_spl[:467].rstrip() + "..."
    findings_list.insert(
        0,

        f"Ένδειξη (FDA SPL summary, Αγγλικά): {clipped_spl}",
    )


    mutated["keyFindings"] = findings_list
    return reorder(dict(mutated.items()))


def render_front_yaml(fm: OrderedDict[str, Any]) -> str:
    dumped = yaml.safe_dump(dict(fm), allow_unicode=True, sort_keys=False, default_flow_style=False, width=116)
    if not dumped.endswith("\n"):
        dumped += "\n"
    return dumped


def iterate_files(single: Path | None, limit: int | None) -> list[Path]:
    if single:
        resolved = single.expanduser().resolve()
        return [resolved]
    picks: list[Path] = []
    for md_path in sorted(FE_ARTICLES.rglob("*.mdx"), key=lambda fp: fp.as_posix().lower()):
        text = md_path.read_text(encoding="utf-8")
        if not _SOURCE_FDA.search(text):
            continue

        picks.append(md_path)


    return picks if limit is None else picks[:limit]


def run(path: Path, *, apply_writes: bool, openfda_api_key: str | None) -> str:
    full_text = path.read_text(encoding="utf-8")
    fm_yaml, body = split_fm(full_text)
    fm_plain = yaml.safe_load(fm_yaml) or {}

    fm = reorder(fm_plain)
    meta_english = str(fm.get("originalTitle") or "").strip()

    meta_english = meta_english or str(fm.get("title") or "").strip()


    appl = extract_application(dict(fm), openfda_api_key)

    brand, inn_chunk = parse_brand_inn(meta_english)



    if not brand or not appl:

        sys.stderr.write(f"{repo_rel(path)}\tSKIP\tmissing brand or application token\n")


        return f"SKIP\t{repo_rel(path)}"


    inject_syspath()
    from medical_news.feeds.fda_drugsfda import fetch_label_indication_excerpt

    spl_blob = fetch_label_indication_excerpt(appl, api_key=openfda_api_key).strip()


    indication_sentence = core_indication_sentence(spl_blob) if spl_blob else ""


    if not indication_sentence:

        sys.stderr.write(f"{repo_rel(path)}\tSKIP\tmissing SPL excerpt\n")


        return f"SKIP\t{repo_rel(path)}"


    greek_lead = wikidata_greek(indication_sentence)
    english_lead = shorten_clause(indication_sentence, limit=118)
    headline_lead = greek_lead or english_lead
    english_tag_piece = tag_from_indication_sentence(indication_sentence)

    mutated = build_frontmatter(
        fm,
        lead=headline_lead,
        brand=brand,
        inn_piece=inn_chunk,
        tag_piece=english_tag_piece,
        greek_label=greek_lead,
        spl_summary=spl_blob[:900],
    )

    rebuilt = "---\n" + render_front_yaml(mutated) + "---\n" + body

    banner = (
        f"{repo_rel(path)}\tlead={'greek' if greek_lead else 'english'}\ttag_preview={english_tag_piece[:96]}"
    )

    if not apply_writes:

        return banner

    original_bytes = path.read_bytes()

    bak = path.with_suffix(path.suffix + ".spl-backfill.bak")


    bak.write_bytes(original_bytes)

    try:


        path.write_text(rebuilt, encoding="utf-8")


    except Exception:


        path.write_bytes(original_bytes)


        bak.unlink(missing_ok=True)



        raise


    bak.unlink(missing_ok=True)

    return f"WRITE\t{repo_rel(path)}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Overwrite MDX frontmatter.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only", type=Path, default=None)
    args = parser.parse_args()

    try:
        import os

        from dotenv import load_dotenv

        load_dotenv(BE_ROOT / ".env")

        openfda = (os.environ.get("OPENFDA_API_KEY") or "").strip() or None
    except Exception:
        openfda = (__import__("os").environ.get("OPENFDA_API_KEY") or "").strip() or None

    files = iterate_files(args.only, args.limit)
    summaries = [run(fl, apply_writes=args.apply, openfda_api_key=openfda) for fl in files]
    sys.stdout.write("\n".join(summaries) + ("\n" if summaries else ""))


if __name__ == "__main__":
    main()
