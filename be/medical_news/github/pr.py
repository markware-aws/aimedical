from __future__ import annotations

import base64
import os
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


def open_pr(file: MdxFile, title_gr: str, source_url: str) -> PrResult:
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
            "body": _pr_body(source_url),
            "draft": True,
        },
    )
    return PrResult(url=pr["html_url"], number=pr["number"], branch=branch)


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
    return os.environ.get("REPO_DEFAULT_BRANCH", "main")


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"missing env {name}")
    return value


def _pr_body(source_url: str) -> str:
    return "\n".join(
        [
            "Auto-generated draft article — **review before publishing**.",
            "",
            f"Original source: {source_url}",
            "",
            "## Reviewer checklist",
            "- [ ] Greek title is accurate, no hype",
            "- [ ] Medical terminology is correct",
            "- [ ] Limitations section is honest",
            "- [ ] No medical advice given",
            "- [ ] Source link works",
            "- [ ] Set `published: true` in frontmatter when ready",
        ]
    )
