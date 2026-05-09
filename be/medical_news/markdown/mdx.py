from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from medical_news.normalize.article import slugify
from medical_news.types import ArticleCategory, GreekArticle, RawArticle


@dataclass(frozen=True)
class MdxFile:
    path: str
    slug: str
    content: str


def build_mdx(raw: RawArticle, greek: GreekArticle, category: ArticleCategory) -> MdxFile:
    slug = slugify(greek["title_gr"]) or slugify(raw["title"]) or f"article-{date.today().isoformat()}"
    published_date = raw["published_date"] or date.today().isoformat()
    year = published_date[:4]
    path = f"fe/src/content/articles/{year}/{slug}.mdx"

    lines = [
        "---",
        f"title: {_yaml_string(greek['title_gr'])}",
    ]
    if greek["subtitle_gr"]:
        lines.append(f"subtitle: {_yaml_string(greek['subtitle_gr'])}")
    lines.extend(
        [
            f"date: {_yaml_string(published_date)}",
            f"description: {_yaml_string(greek['description_gr'])}",
            f"category: {_yaml_string(category)}",
            "tags:",
            *[f"  - {_yaml_string(tag)}" for tag in greek["tags"]],
        ]
    )
    if greek["key_findings"]:
        lines.append("keyFindings:")
        lines.extend(f"  - {_yaml_string(finding)}" for finding in greek["key_findings"])
    if greek["limitations"]:
        lines.append(f"studyLimitations: {_yaml_string(greek['limitations'])}")
    if greek["clinical_significance"]:
        lines.append(f"clinicalSignificance: {_yaml_string(greek['clinical_significance'])}")
    lines.extend(
        [
            f"sourceUrl: {_yaml_string(raw['url'])}",
            f"doi: {_yaml_string(raw['doi'])}" if raw.get("doi") else "",
            f"source: {_yaml_string(raw['source'])}",
            "published: false",
            "generated: true",
            "featured: false",
            "---",
            "",
        ]
    )
    frontmatter = "\n".join(line for line in lines if line)
    body = greek["body"].strip() + "\n"
    return MdxFile(path=path, slug=slug, content=f"{frontmatter}\n{body}")


def _yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
