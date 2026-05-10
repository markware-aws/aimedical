# `be/` — AI Medical News Greece backend

Single Python AWS Lambda that runs the full content pipeline:

```
fetch (PubMed + arXiv + RSS)
  → dedupe (DynamoDB)
  → relevance score (OpenAI)
  → Greek article generation (OpenAI)
  → MDX file
  → GitHub PR (draft, published: false)
  → mark processed (DynamoDB)
```

PRs are the publish gate. Humans review and flip `published: true` in the article frontmatter.

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

| Script                                      | Description                                                                 |
| ------------------------------------------- | --------------------------------------------------------------------------- |
| `python scripts/invoke_local.py`            | Runs the orchestrator locally end-to-end                                    |
| `python scripts/invoke_topic.py --query "2025 AI breakthroughs in medicine" --year 2025 --max-articles 3` | Runs a one-off sourced topic query through the same pipeline |
| `python scripts/invoke_rss.py --dry-run`    | Previews recent articles from curated RSS sources only, without side effects |
| `python scripts/invoke_rss.py --max-per-source 3 --max-articles 3` | Runs recent curated RSS articles through the same pipeline |
| `python -m compileall medical_news scripts` | Syntax/import-path smoke check                                              |
| `bash scripts/package.sh`                   | compile check + dependency install into `dist/` + `function.zip`            |
| `bash scripts/deploy.sh`                    | package + Lambda upload                                                     |
| `bash scripts/provision.sh`                 | one-shot AWS CLI provisioning (S3, DynamoDB, IAM, Lambda, EventBridge cron) |

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

---

## Environment

See `.env.example`. Required at runtime:

- `OPENAI_API_KEY`, `OPENAI_MODEL`
- `GITHUB_TOKEN`, `REPO_OWNER`, `REPO_NAME`, `REPO_DEFAULT_BRANCH`
- `AWS_REGION`, `DYNAMODB_TABLE`
- `RELEVANCE_MIN_SCORE` (default 7), `MAX_ARTICLES_PER_RUN` (default 10)

Generated article PRs target `REPO_DEFAULT_BRANCH`, which defaults to `dev`. Merge generated PRs into `dev`, review/publish there, then merge `dev` into `main` when you want the frontend deployment workflow to run.

---

## Layout

```
be/
├── medical_news/
│   ├── handlers/orchestrator.py   Lambda entry, runs the pipeline
│   ├── feeds/                     pubmed.py, arxiv.py, rss.py
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

- **Order matters:** the PR is opened **before** the DynamoDB write. If the PR succeeds and the DB write fails, dedup may double-process — acceptable. If the DB write happens first and the PR fails, the article is permanently lost — not acceptable.
- **Dedup key:** prefer DOI (`ARTICLE#10.xxx/...`), fall back to `ARTICLE#<source>#<sourceId>`.
- **All generated articles ship with `published: false` and `featured: false`** in frontmatter. Human review is the gate.
- **Slug:** Greek titles are transliterated to ASCII before slugifying (see `medical_news/normalize/article.py`).
