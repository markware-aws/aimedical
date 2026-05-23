# Newsletter implementation plan

Status: **not implemented** — homepage signup shows “Σύντομα” until this work is done.

This document is the checklist for wiring up the weekly Greek digest for [aimedical.gr](https://aimedical.gr).

---

## Current state

| Piece | Status |
|-------|--------|
| UI (`NewsletterBox.astro` on homepage) | Placeholder — “Σύντομα” |
| Backend / API | None |
| Email provider account | None |
| Privacy / legal copy | Partially drafted in `/privacy/` (provider TBD) |
| Weekly send workflow | None |
| RSS feed for content | Live at `/rss.xml` (sorted by `publishedAt`) |

The form previously used `onsubmit="event.preventDefault()"` and collected nothing.

---

## Goals

1. Collect email addresses with **explicit GDPR consent**.
2. Send a **weekly Greek digest** of new / featured AI-in-medicine articles.
3. Keep the **static S3 + Cloudflare** architecture (no server required for page views).
4. Minimize operational burden for a solo/small editorial team.

---

## Recommended approach: hosted ESP (phase 1)

Use a **hosted email service provider (ESP)** instead of building subscribe/send infrastructure on AWS first.

### Provider shortlist

| Provider | Pros | Cons |
|----------|------|------|
| **MailerLite** | Free tier, EU-friendly, forms + automation, RSS campaigns | UI can feel busy |
| **Buttondown** | Simple, writer-focused, markdown emails | Smaller feature set |
| **Beehiiv** | Growth tools, RSS-to-email | Heavier / more “creator” oriented |
| **ConvertKit** | Good automations | Pricier at scale |

**Pick one** before implementation. MailerLite or Buttondown is enough for phase 1.

### Why not AWS-first?

Lambda + SES + DynamoDB + double opt-in tokens is doable but adds:

- API Gateway or Cloudflare Worker
- Token storage, confirmation emails, bounce handling
- Weekly HTML generation job
- Ongoing security and deliverability work

Defer unless you outgrow the ESP or need full data ownership.

---

## Phase 1 — Signup (estimate: 2–4 hours)

### 1. ESP setup

- [ ] Create account; choose **EU data region** if offered.
- [ ] Create audience/list: e.g. `Medical AI Breakthroughs – Weekly`.
- [ ] Enable **double opt-in** (confirmation email before active subscription).
- [ ] Configure sender domain:
  - [ ] Add DNS records (SPF, DKIM, DMARC) for `aimedical.gr` or a subdomain like `news.aimedical.gr`.
  - [ ] Verify domain in ESP.
- [ ] Set From name/address: e.g. `Medical AI Breakthroughs <newsletter@aimedical.gr>`.
- [ ] Sign **DPA** (Data Processing Agreement) with provider for GDPR.

### 2. Frontend (`NewsletterBox.astro`)

- [ ] Remove “Σύντομα” placeholder.
- [ ] Wire form to ESP:
  - **Option A:** official embed snippet (iframe or hosted form).
  - **Option B:** `POST` to ESP form endpoint with hidden `list_id` / `api_key` fields (prefer Worker proxy if API key must stay secret).
- [ ] Add **required consent checkbox** (unchecked by default):

  > Συμφωνώ να λαμβάνω το εβδομαδιαίο newsletter και έχω διαβάσει την [Πολιτική απορρήτου](/privacy/).

- [ ] Success state: “Ελέγξτε το email σας για επιβεβαίωση” (double opt-in).
- [ ] Error state: generic Greek message + link to `info@aimedical.gr`.
- [ ] Disable submit until consent is checked.
- [ ] Keep form accessible (`label`, `aria-live` for messages).

### 3. Legal pages

Update `fe/src/pages/privacy.astro`:

- [ ] Replace “Πάροχος newsletter (εάν εγγραφείτε)” with **actual provider name** and link to their privacy/DPA.
- [ ] Note double opt-in and retention (“until unsubscribe”).
- [ ] Update `lastUpdated` date.

Optional: one line in `fe/src/pages/cookie-policy.astro` if ESP sets cookies on redirect (usually none for simple POST).

### 4. Testing

- [ ] Test signup with real email — confirm double opt-in flow.
- [ ] Test unsubscribe link from confirmation/welcome email.
- [ ] Test on mobile + dark mode.
- [ ] Verify no PII in browser console or public repo (API keys in env / Worker secrets only).

---

## Phase 2 — Weekly send (estimate: 2–6 hours)

### Content source

Articles are already available:

- **Site RSS:** `https://aimedical.gr/rss.xml` (published articles, `publishedAt` order).
- **Editorial pick:** mark `featured: true` in MDX for hero stories.

### Send options

| Method | Effort | Notes |
|--------|--------|-------|
| **Manual weekly email** in ESP | Low | Copy 3–5 links + blurbs; full editorial control |
| **RSS-to-email** (ESP automation) | Low | Auto-pull RSS; less curated |
| **Custom template + manual send** | Medium | Branded HTML; paste RSS items |
| **Lambda cron → ESP API** | High | Auto-build from MDX/git; only if volume justifies it |

**Recommendation for launch:** manual or RSS-assisted weekly send. Automate later if needed.

### Email template checklist

- [ ] Greek subject line pattern: e.g. `Medical AI Breakthroughs — εβδομάδα 23–29 Μαΐου`.
- [ ] 3–5 article cards: title, one-line description, link.
- [ ] Link to site homepage and `/rss.xml`.
- [ ] Footer: physical/editorial contact, unsubscribe (ESP merge tag), link to `/privacy/`.
- [ ] Plain-text alternative (ESP usually auto-generates).
- [ ] “AI-generated · human-reviewed” disclosure if quoting article summaries.

### Schedule

- [ ] Pick send day/time (e.g. Friday 09:00 Europe/Athens).
- [ ] ESP automation or calendar reminder for manual send.

---

## Phase 3 — Optional enhancements

- [ ] **Cloudflare Worker** proxy for subscribe API (hide secrets, rate-limit, honeypot).
- [ ] **Welcome email** in Greek after confirmation.
- [ ] **Segmentation** by category (oncology, radiology, …) — only if list grows.
- [ ] **Plausible/GA event** on successful signup (only with cookie consent if applicable).
- [ ] **Admin script** in `be/scripts/` to draft weekly HTML from latest MDX (for paste into ESP).

---

## Alternative: AWS-native stack (phase 2+ only)

If you later move off a hosted ESP:

```
Browser POST → Cloudflare Worker → Lambda → DynamoDB (subscribers)
                      ↓
              SES or Resend (confirm + weekly send)
                      ↑
         EventBridge cron (weekly) → Lambda reads fe content / RSS
```

Additional work:

- Confirmation token table + expiry
- `GET /confirm?token=` static page or Worker route
- Bounce/complaint handling via SNS
- List hygiene and suppression list

Document this path only if ESP costs or compliance require self-hosting.

---

## Files to touch when implementing

| File | Change |
|------|--------|
| `fe/src/components/NewsletterBox.astro` | Wire form, consent, states |
| `fe/src/pages/privacy.astro` | Name ESP, update dates |
| `fe/docs/newsletter-plan.md` | Mark checklist items done |
| `.github/workflows/deploy.yml` | Only if adding Worker or env-based embed IDs |
| Cloudflare dashboard | DNS for email domain, optional Worker |

No changes required in `be/` for phase 1 ESP embed.

---

## Secrets & config

Store outside git:

| Secret | Where |
|--------|--------|
| ESP form ID / API key | Cloudflare Worker secret or GitHub Actions env |
| ESP list/audience ID | Same |
| Sender domain verification | DNS only |

Do **not** commit API keys in `NewsletterBox.astro`. For public form endpoints that use only a public form hash (some ESPs), confirm with provider docs.

---

## Launch checklist

- [ ] Domain email authentication (SPF/DKIM/DMARC) passing
- [ ] Double opt-in tested end-to-end
- [ ] Privacy policy names provider
- [ ] First weekly issue sent to a test segment
- [ ] Unsubscribe tested
- [ ] Remove “Σύντομα” from UI
- [ ] Update this doc status to **implemented**

---

## References

- Site RSS: `/rss.xml`
- Privacy (GDPR baseline): `/privacy/`
- Homepage component: `fe/src/components/NewsletterBox.astro`
- Article sort date for “what’s new”: `publishedAt` in MDX frontmatter
