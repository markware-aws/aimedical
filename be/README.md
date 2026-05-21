# `be/` - AI Medical News Greece backend

Single Python AWS Lambda that runs the full content pipeline:

```
fetch (PubMed + arXiv + RSS)
  → dedupe (DynamoDB)
  → relevance score (OpenAI)
  → Greek article generation (OpenAI)
  → MDX file
  → GitHub PR (draft, published: true)
  → mark processed (DynamoDB)
```

PR review is the quality gate before merge; generated articles are visible after deployment once merged.

---

## Quick Start

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env   # fill in real values
python scripts/invoke_local.py
```

`python scripts/invoke_local.py` will hit real PubMed, real OpenAI, real GitHub, and real DynamoDB. There is no mock mode.

---

## Scripts

| Script                                                                                                    | Description                                                                  |
| --------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `python scripts/invoke_local.py`                                                                          | Runs the orchestrator locally end-to-end                                     |
| `python scripts/invoke_topic.py --query "2025 AI breakthroughs in medicine" --year 2025 --max-articles 3` | Runs a one-off sourced topic query through the same pipeline                 |
| `python scripts/invoke_rss.py --dry-run`                                                                  | Previews recent articles from curated RSS sources only, without side effects |
| `python scripts/invoke_rss.py --max-per-source 3 --max-articles 3`                                        | Runs recent curated RSS articles through the same pipeline                   |
| `python scripts/invoke_disease_advances.py --dry-run --max-per-source 3`       | Preview manual “society/disease breakthrough” feeds (RSS list in `medical_news/feeds/disease_advances.py`) |
| `python scripts/invoke_fda_drugs.py --dry-run --days 365 --max-results 15`                                       | Preview recent FDA **Drugs@FDA** originals (openFDA); default=NME (**Type 1**) only                              |
| `python scripts/invoke_fda_drugs.py --batch-pr --since 20260101 --until 20260520 --max-articles 3`                 | Same pipeline via openFDA approvals (skips relevance scoring; **`source: fda`**, **`category: drug-discovery`**)                                      |
| `python scripts/backfill_fda_article_frontmatter.py`                                                        | Preview **FDA** Astro MDX frontmatter refresh (**no OpenAI**: openFDA SPL excerpt + Wikidata Greek when available); add `--apply` to write (`PyYAML` is in requirements) |
| `python -m compileall medical_news scripts`                                                               | Syntax/import-path smoke check                                               |
| `bash scripts/package.sh`                                                                                 | compile check + dependency install into `dist/` + `function.zip`             |
| `bash scripts/deploy.sh`                                                                                  | package + Lambda upload                                                      |
| `bash scripts/provision.sh`                                                                               | one-shot AWS CLI provisioning (S3, DynamoDB, IAM, Lambda, EventBridge cron)  |

`deploy.sh` and `provision.sh` use `AWS_PROFILE=aimedical-user` by default; override via env.

Topic runs hit real PubMed/arXiv, OpenAI, GitHub, and DynamoDB. They create draft PRs just like the scheduled Lambda:

```powershell
python scripts/invoke_topic.py --query "2025 AI breakthroughs in medicine" --year 2025 --max-per-source 10 --max-articles 3
```

Use `--source pubmed` or `--source arxiv` to limit the query while testing.

RSS-only runs use the curated journal feeds in `medical_news/feeds/rss.py`. Preview candidates first:

```powershell
python scripts/invoke_rss.py --dry-run --max-per-source 5
```

Then run the recent RSS candidates through the full pipeline:

```powershell
python scripts/invoke_rss.py --max-per-source 3 --max-articles 3
```

### Manual disease‑breakthrough feeds

Edit `ADVANCE_FEEDS` in [`medical_news/feeds/disease_advances.py`](medical_news/feeds/disease_advances.py): add oncology / autoimmune / advocacy RSS URLs plus an optional Astro `category` per feed. This batch **skips relevance scoring** so non‑AI medical news can be summarized, sets **`featured: true`** by default for the carousel, and notes that in the PR body. Use **`--no-featured`** if you only want summaries without homepage promotion.

```powershell
python scripts/invoke_disease_advances.py --dry-run --max-per-source 3
python scripts/invoke_disease_advances.py --source who-news --max-per-source 5 --max-articles 5
python scripts/invoke_disease_advances.py --batch-pr --max-articles 5
python scripts/invoke_disease_advances.py --no-featured --max-articles 5
```

### FDA Drugs@FDA (new molecular entities)

[`medical_news/feeds/fda_drugsfda.py`](medical_news/feeds/fda_drugsfda.py) queries **[openFDA `drugsfda`](https://open.fda.gov/apis/drug/drugsfda/)** for approved **ORIG** submissions in a date window, then attaches a short **INDICATIONS AND USAGE** excerpt from **[openFDA `drug/label`](https://open.fda.gov/apis/drug/label/)** when available so prompts can steer Greek titles/tags toward the labelled condition. **`--days`** (default 90) resolves to `{today-days … today}`; or pass **`--since`/`--until`** as `YYYYMMDD`.

Relevance scoring is **skipped** (like disease-advance batches); metadata uses **`fda`** plus Astro category **`drug-discovery`**.

```powershell
python scripts/invoke_fda_drugs.py --dry-run --days 180 --max-results 20
python scripts/invoke_fda_drugs.py --all-original-types --days 365 --batch-pr --max-articles 3
```

Optional `.env`: `OPENFDA_API_KEY=` for elevated rate limits.

## Environment

See `.env.example`. Required at runtime:

- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `GITHUB_TOKEN`, `REPO_OWNER`, `REPO_NAME`, `REPO_DEFAULT_BRANCH`
- `AWS_REGION`, `DYNAMODB_TABLE`
- `RELEVANCE_MIN_SCORE` (default 7), `MAX_ARTICLES_PER_RUN` (default 10)
- `GITHUB_BATCH_PR` (optional; values `1`, `true`, `yes`, or `on`): after a run completes, GitHub receives **one** draft PR listing every new MDX file instead of opening a PR per article. Local/script runs can pass **`--batch-pr`** on `invoke_local.py`, `invoke_rss.py`, `invoke_topic.py`, `invoke_disease_advances.py`, or `invoke_fda_drugs.py` (same effect). With batch mode enabled, DynamoDB rows are written only **after** the batch PR succeeds, so failures before that do not dedupe prematurely.
- `OPENFDA_API_KEY` (optional): FDA openFDA key for [`invoke_fda_drugs.py`](scripts/invoke_fda_drugs.py); higher quotas per [FDA authentication](https://open.fda.gov/apis/authentication/).

Generated article PRs target `REPO_DEFAULT_BRANCH`, which defaults to `dev`. Review generated PRs there, then merge `dev` into `main` when you want the frontend deployment workflow to run.

---

## Layout

```
be/
├── medical_news/
│   ├── handlers/orchestrator.py   Lambda entry, runs the pipeline
│   ├── feeds/                     pubmed.py, arxiv.py, rss.py, fda_drugsfda.py (manual invoke)
│   ├── normalize/article.py       dedup_key() + Greek-aware slugify()
│   ├── db/dynamodb.py             exists(), put() on aimedical_articles
│   ├── ai/
│   │   ├── prompts.py             editorial guardrails live here
│   │   ├── relevance.py           returns { relevant, score, category, reason }
│   │   └── generator.py           returns full GreekArticle JSON
│   ├── markdown/mdx.py            builds the MDX file the PR will commit
│   ├── github/pr.py               branch + commit + draft PR via GitHub API
│   ├── util/                      logger.py (JSON), hash.py
│   └── types.py
└── scripts/
    ├── invoke_local.py            local end-to-end run
    ├── deploy.sh                  package + upload
    └── provision.sh               idempotent AWS CLI provisioning
```

The Lambda handler is `medical_news.handlers.orchestrator.handler`.

---

## Editorial Guardrails

These are enforced in `medical_news/ai/prompts.py`. Don't dilute them when editing prompts:

- Avoid sensationalism, hype, "miracle" language
- Always mention study limitations
- Never generate medical advice
- Distinguish peer-reviewed from preprints
- Don't fabricate findings, statistics, or quotes
- Write naturally in Greek, not as a translation

---

## Pipeline Invariants

- **Order matters (single-article PRs):** the PR is opened **before** each DynamoDB write. If the PR succeeds and the DB write fails later, dedup may double-process; acceptable. If the DB write happened first and the PR failed instead, content could be lost; current ordering avoids that.
- **Batch PRs (`GITHUB_BATCH_PR`):** all MDX commits land on one branch, one draft PR opens, then each article gets a DynamoDB row with that shared PR URL.
- **Dedup key:** prefer DOI (`ARTICLE#10.xxx/...`), fall back to `ARTICLE#<source>#<sourceId>`.
- **All generated articles ship with `published: true` and `featured: false`** in frontmatter. PR review is the quality gate before deployment.
- **Slug:** Greek titles are transliterated to ASCII before slugifying (see `medical_news/normalize/article.py`).
