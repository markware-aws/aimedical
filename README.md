# AI Medical News

A Greek-language news site about artificial intelligence in medicine, paired with an automated content pipeline that sources, scores, and summarizes medical-AI research into publication-ready articles.

The project has two halves:

| Directory | What it is | Stack |
| --------- | ---------- | ----- |
| [`fe/`](fe/) | Static Greek news site (the public website) | Astro 5 + Tailwind 3 + MDX, deployed to S3 behind Cloudflare |
| [`be/`](be/) | Content pipeline that generates the articles | Python 3.12 AWS Lambda |

## How it works

The backend pipeline:

```
fetch (PubMed + arXiv + RSS + FDA)
  → dedupe (DynamoDB)
  → relevance score (OpenAI)
  → Translate (Deepl)
  → Greek article generation (OpenAI)
  → MDX file
  → GitHub PR (draft)
  → mark processed (DynamoDB)
```

Each run opens a draft GitHub pull request adding new `.mdx` files to `fe/src/content/articles/`. **PR review is the quality gate** — a human reviews the generated content before merging. Once merged to `main`, a GitHub Actions workflow builds the frontend and syncs it to S3.

## Running locally

The two halves run independently. The frontend reads MDX files already committed to the repo, so you can develop the site without running the pipeline.

### Frontend (`fe/`)

```bash
cd fe
npm install
npm run dev      # http://localhost:4321
```

Other scripts: `npm run build` (static build → `dist/`), `npm run preview`, `npm run check` (type + content schema check).

See [`fe/README.md`](fe/README.md) for the layout, design system, and how to add an article by hand.

#### Remove unpublished articles

Articles with `published: false` are not rendered on the site. To find them:

```bash
grep -rl '^published:\s*false' fe/src/content/articles --include='*.mdx'
```

To delete them (preview the list above first):

```bash
grep -rl '^published:\s*false' fe/src/content/articles --include='*.mdx' | xargs rm
```

### Backend (`be/`)

```powershell
cd be
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env   # fill in real values
python scripts/invoke_local.py
```

> [!WARNING]
> There is no mock mode. `python scripts/invoke_local.py` hits **real** PubMed/arXiv, OpenAI, GitHub, and DynamoDB, and will open a real draft PR. Use the `--dry-run` flag on the preview scripts (e.g. `python scripts/invoke_rss.py --dry-run`) to inspect candidates without side effects.

Required environment variables (see `be/.env.example`): `OPENAI_API_KEY`, `OPENAI_MODEL`, `GITHUB_TOKEN`, `REPO_OWNER`, `REPO_NAME`, `REPO_DEFAULT_BRANCH`, `AWS_REGION`, `DYNAMODB_TABLE`.

See [`be/README.md`](be/README.md) for all invoke scripts, the FDA/RSS feeds, deployment, and pipeline invariants.

## Repository layout

```
.
├── fe/      Astro frontend (the website)
├── be/      Python Lambda content pipeline
├── docs/    plan.md, UI spec, ops notes
└── .github/ deploy + scheduling workflows
```
