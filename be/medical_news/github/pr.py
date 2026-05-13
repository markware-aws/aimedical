from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from typing import Any

from medical_news.markdown.mdx import MdxFile
from medical_news.util.http import request, request_json

GITHUB_API = "https://api.github.com"


@dataclass(frozen=True)
class PrResult:
    url: str
    number: int
    branch: str


def open_pr(
    file: MdxFile,
    title_gr: str,
    source_url: str,
    *,
    pipeline_note: str | None = None,
) -> PrResult:
    branch = f"auto/{file.slug}"
    base_sha = _request("GET", f"/git/ref/heads/{_base_branch()}")["object"]["sha"]
    _create_ref_if_needed(branch, base_sha)

    _request(
        "PUT",
        f"/contents/{file.path}",
        json_body={
            "branch": branch,
            "message": f"auto: add {file.slug}",
            "content": base64.b64encode(file.content.encode("utf-8")).decode("ascii"),
        },
    )

    pr = _request(
        "POST",
        "/pulls",
        json_body={
            "head": branch,
            "base": _base_branch(),
            "title": f"[auto] {title_gr}",
            "body": _pr_body(source_url, pipeline_note=pipeline_note),
            "draft": True,
        },
    )
    return PrResult(url=pr["html_url"], number=pr["number"], branch=branch)


type BatchArticleEntry = tuple[MdxFile, str, str | None]


def open_batch_pr(entries: list[BatchArticleEntry]) -> PrResult:
    """Push several new MDX files on one branch and open a single draft PR.

    Each entry is ``(mdx_file, source_url, pipeline_note)`` where ``pipeline_note`` may be ``None``.
    """
    if not entries:
        raise ValueError("open_batch_pr requires at least one entry")

    branch = f"auto/batch-{int(time.time())}"
    base_sha = _request("GET", f"/git/ref/heads/{_base_branch()}")["object"]["sha"]
    _create_ref_if_needed(branch, base_sha)

    for idx, entry in enumerate(entries, start=1):
        file, slug = entry[0], entry[0].slug
        _request(
            "PUT",
            f"/contents/{file.path}",
            json_body={
                "branch": branch,
                "message": f"auto ({idx}/{len(entries)}): add {slug}",
                "content": base64.b64encode(file.content.encode("utf-8")).decode("ascii"),
            },
        )

    pr = _request(
        "POST",
        "/pulls",
        json_body={
            "head": branch,
            "base": _base_branch(),
            "title": f"[auto] Batch: {len(entries)} articles",
            "body": _multi_pr_body(entries),
            "draft": True,
        },
    )
    return PrResult(url=pr["html_url"], number=pr["number"], branch=branch)

def _multi_pr_body(entries: list[BatchArticleEntry]) -> str:
    lines: list[str] = [
        "Auto-generated draft articles — **review before merging**.",
        "",
        f"This PR adds **{len(entries)}** articles in one branch.",
        "",
        "## Sources",
        "",
    ]
    for idx, entry in enumerate(entries, start=1):
        file, url, note = entry[0], entry[1], entry[2]
        lines.append(f"{idx}. ``{file.path}`` ({file.slug})")
        lines.append(f"   - {url}")
        if note:
            lines.extend(["", f"   **Note:** {note}", ""])
        else:
            lines.append("")
    lines.extend(
        [
            "## Reviewer checklist",
            "- [ ] Greek titles accurate, no hype",
            "- [ ] Medical terminology is correct",
            "- [ ] Limitations sections are honest",
            "- [ ] No medical advice given",
            "- [ ] Source links work",
            "- [ ] Leave `published: true` unless an article should be hidden",
            "- [ ] `featured:` flags match homepage intent",
        ]
    )
    return "\n".join(lines)


def _create_ref_if_needed(branch: str, base_sha: str) -> None:
    status, text = request(
        "POST",
        _repo_url("/git/refs"),
        headers=_headers(),
        json_body={"ref": f"refs/heads/{branch}", "sha": base_sha},
        timeout=30,
    )
    if status == 422 and "Reference already exists" in text:
        return
    if status < 200 or status >= 300:
        raise RuntimeError(f"github POST /git/refs failed: {status} {text}")


def _request(method: str, path: str, **kwargs: Any) -> Any:
    try:
        return request_json(method, _repo_url(path), headers=_headers(), timeout=30, **kwargs)
    except RuntimeError as exc:
        raise RuntimeError(f"github {method} {path} failed: {exc}") from exc


def _repo_url(path: str) -> str:
    return f"{GITHUB_API}/repos/{_required('REPO_OWNER')}/{_required('REPO_NAME')}{path}"


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {_required('GITHUB_TOKEN')}",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _base_branch() -> str:
    return os.environ.get("REPO_DEFAULT_BRANCH", "dev")


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing env {name}")
    return value


def _pr_body(source_url: str, *, pipeline_note: str | None = None) -> str:
    blocks = [
            "Auto-generated draft article - **review before merging**.",
            "",
            f"Original source: {source_url}",
        ]
    if pipeline_note:
        blocks.extend(["", pipeline_note.strip()])
    blocks.extend(
        [
            "",
            "## Reviewer checklist",
            "- [ ] Greek title is accurate, no hype",
            "- [ ] Medical terminology is correct",
            "- [ ] Limitations section is honest",
            "- [ ] No medical advice given",
            "- [ ] Source link works",
            "- [ ] Leave `published: true` unless this article should be hidden",
        ]
    )
    return "\n".join(blocks)
