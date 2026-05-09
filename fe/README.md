# `fe/` — AI Medical News Greece frontend

Static Greek-language news site about AI in medicine. Astro + Tailwind + MDX, fully static, deployed to S3 behind Cloudflare CDN.

Visual identity is editorial / scientific (think *Nature Medicine* + *MIT Technology Review* + *Apple News*) — never crypto / startup / AI-hype aesthetics. See `../UI_NEW.md` for the full spec.

---

## Quick start

```powershell
npm install
npm run dev      # http://localhost:4321
```

`npm run build` produces `dist/` for S3 sync.

---

## Scripts

| Script | Description |
| --- | --- |
| `npm run dev` | Astro dev server with HMR |
| `npm run build` | Static build → `dist/` |
| `npm run preview` | Preview the built site |
| `npm run check` | `astro check` (TypeScript + content schema) |

---

## Layout

```
fe/
├── src/
│   ├── consts.ts                site name, categories, helpers
│   ├── content/
│   │   ├── config.ts            Zod schema for the articles collection
│   │   └── articles/YYYY/*.mdx  one MDX file per article
│   ├── layouts/
│   │   ├── BaseLayout.astro     html/head/header/footer shell
│   │   └── ArticleLayout.astro  article page (hero, sections, related)
│   ├── components/
│   │   ├── Header.astro · Footer.astro
│   │   ├── CategoryNav.astro · CategoryBadge.astro
│   │   ├── ArticleCard.astro · FeaturedArticle.astro · RelatedArticles.astro
│   │   ├── ArticleSections.astro  Key Findings / Limitations / Clinical Significance blocks
│   │   ├── SourceCitation.astro · Disclaimer.astro
│   │   ├── SearchOverlay.astro    UI-only (cmd/ctrl+K)
│   │   ├── ThemeToggle.astro · ThemeScript.astro  dark mode
│   │   ├── Pagination.astro · NewsletterBox.astro · SEO.astro
│   ├── lib/articles.ts          getPublishedArticles, getFeatured, getByCategory, getRelated
│   ├── pages/
│   │   ├── index.astro
│   │   ├── articles/[...slug].astro · category/[category].astro
│   │   ├── about.astro · editorial-policy.astro · ai-disclosure.astro
│   │   ├── contact.astro · privacy.astro · 404.astro
│   │   └── rss.xml.ts
│   └── styles/global.css
├── public/robots.txt
├── astro.config.mjs · tailwind.config.mjs · tsconfig.json
└── .env.example
```

---

## Adding an article (manual)

Create `src/content/articles/<year>/<slug>.mdx`:

```mdx
---
title: "Greek title here"
subtitle: "Optional subtitle"
date: 2026-05-07
description: "SEO description, 140-160 chars"
category: "oncology"   # see CATEGORIES in src/consts.ts
tags: ["ai", "oncology"]
heroImage: "/images/article.jpg"  # optional
sourceUrl: "https://pubmed.ncbi.nlm.nih.gov/12345/"
doi: "10.0000/example"             # optional
source: "pubmed"                   # optional
keyFindings:                       # optional, renders as a callout
  - "Bullet 1"
  - "Bullet 2"
studyLimitations: "Optional, renders as a callout"
clinicalSignificance: "Optional, renders as a callout"
published: true
generated: false
featured: false
---

## Τι συνέβη

Body in Greek.

## Γιατί έχει σημασία

...
```

Only articles with `published: true` are rendered. The Lambda always writes `published: false` so PR review is the publish gate.

The schema is enforced by Zod in `src/content/config.ts` — `npm run check` will catch frontmatter mistakes.

---

## Design system

Colors (Tailwind tokens, all have a `.dark` variant):

| Token | Light | Use |
| --- | --- | --- |
| `bg` | `#FFFFFF` | page background |
| `surface` | `#FAFAF7` | cards, callouts |
| `ink` | `#1A1A1A` | body text |
| `muted` | `#5C5C5C` | meta, dates |
| `accent` | `#0F4C75` | links, primary accent (deep blue) |
| `teal` | `#2A7F7E` | Key Findings block |
| `med` | `#3D7B5F` | Clinical Significance block |
| `border` | `#E5E5E0` | hairline dividers |

Dark mode: `class` strategy. Anti-FOUC inline script in `<head>` (see `ThemeScript.astro`). Toggle persists to `localStorage`. Dark uses `#16191C` charcoal, never pure black.

Font: Inter (loaded from `rsms.me/inter`). Sans-serif throughout — no serif body.

---

## Deployment

GitHub Actions workflow at `../.github/workflows/deploy.yml` builds and syncs to S3 on push to `main`. Uses OIDC; you must have an `arn:aws:iam::<acct>:role/github-actions-deployer` role configured.

Local dry run:

```powershell
npm run build
# dist/ is what gets synced
```

---

## Editorial requirements surfaced in UI

These are non-negotiable:

- Standing `<Disclaimer>` on every article
- `<SourceCitation>` (sourceUrl + DOI) on every article
- "AI-generated · human-reviewed" badge in article header
- Greek `lang="el"` on `<html>`
- `<Disclaimer>` text: "Δεν αποτελεί ιατρική συμβουλή. Συμβουλευτείτε επαγγελματία υγείας."
