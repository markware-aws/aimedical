from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


FeedSource = Literal["pubmed", "arxiv", "rss", "fda"]
ArticleCategory = Literal[
    "oncology",
    "cardiology",
    "neurology",
    "hepatology",
    "immunology",
    "diagnostics",
    "radiology",
    "llms",
    "drug-discovery",
    "robotics",
    "digital-health",
    "public-health",
    "women-health",
    "other",
]


class RawArticle(TypedDict):
    source: FeedSource
    source_id: str
    title: str
    abstract: str
    authors: list[str]
    published_date: str
    doi: NotRequired[str]
    url: str
    # Optional pipeline hints (manual / curated batches e.g. disease-advance feeds)
    featured: NotRequired[bool]
    category_override: NotRequired[ArticleCategory]
    bypass_relevance: NotRequired[bool]


class RelevanceResult(TypedDict):
    relevant: bool
    score: float
    category: ArticleCategory
    reason: str


class GreekArticle(TypedDict):
    title_gr: str
    subtitle_gr: str
    description_gr: str
    body: str
    tags: list[str]
    conditions: list[str]
    key_findings: list[str]
    limitations: str
    clinical_significance: str


class ProcessedRecord(TypedDict):
    pk: str
    title: str
    source: FeedSource
    url: str
    hash: str
    status: Literal["pr-open", "skipped-low-score", "error"]
    slug: str
    createdAt: str
    processedAt: str
    doi: NotRequired[str]
    prUrl: NotRequired[str]


class RunError(TypedDict):
    sourceId: str
    message: str


class RunSummary(TypedDict):
    fetched: int
    alreadyProcessed: int
    skippedLowScore: int
    generated: int
    prsOpened: int
    errors: list[RunError]
