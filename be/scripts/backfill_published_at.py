#!/usr/bin/env python3
"""Add ``publishedAt`` to article MDX files from git first-commit dates.

New articles get ``publishedAt`` from the pipeline. Existing files only have
``date`` (source publication date from PubMed/RSS/FDA), which makes recently
fetched articles sort incorrectly on the site.

Dry-run::

  python scripts/backfill_published_at.py

Apply::

  python scripts/backfill_published_at.py --apply
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

BE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BE_ROOT.parent
FE_ARTICLES = REPO_ROOT / "fe" / "src" / "content" / "articles"

_PUBLISHED_AT_RE = re.compile(r"(?m)^publishedAt:\s*")
_DATE_LINE_RE = re.compile(r'(?m)^date:\s*["\']?([^"\']+)["\']?\s*$')


def repo_rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def git_first_commit_date(rel_path: str) -> str | None:
    result = subprocess.run(
        [
            "git",
            "log",
            "--follow",
            "--diff-filter=A",
            "--format=%aI",
            "--",
            rel_path,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.strip().splitlines()[-1][:10]


def insert_published_at(content: str, published_at: str) -> str:
    if _PUBLISHED_AT_RE.search(content):
        return content
    match = _DATE_LINE_RE.search(content)
    if not match:
        raise ValueError("frontmatter missing date field")
    insert_at = match.end()
    return content[:insert_at] + f'\npublishedAt: "{published_at}"' + content[insert_at:]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write changes to disk.")
    args = parser.parse_args()

    updated = 0
    skipped = 0
    for path in sorted(FE_ARTICLES.rglob("*.mdx")):
        content = path.read_text(encoding="utf-8")
        if _PUBLISHED_AT_RE.search(content):
            skipped += 1
            continue

        rel = repo_rel(path)
        published_at = git_first_commit_date(rel) or date.today().isoformat()
        new_content = insert_published_at(content, published_at)
        print(f"{'write' if args.apply else 'plan'} {rel} -> publishedAt: {published_at}")
        if args.apply:
            path.write_text(new_content, encoding="utf-8")
        updated += 1

    print(f"\n{'Updated' if args.apply else 'Would update'} {updated} file(s); skipped {skipped} already set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
