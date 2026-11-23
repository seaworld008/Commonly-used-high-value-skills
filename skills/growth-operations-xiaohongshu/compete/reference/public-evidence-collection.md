# Public Competitive Evidence Collection & Teardown Templates

Reference extraction patterns and audit templates preserved from `competitive-teardown` for gathering verifiable public pricing, changelog, app-store review, and hiring signals.

## 1. Public Pricing, Changelog & Sitemap Extraction

- Date-stamp every pricing snapshot (`accessed YYYY-MM-DD`) because tiers and limits change rapidly.
- Extract pricing tiers, per-seat vs usage-based models, free-trial gates, integration logos, and trust/compliance badges from public pricing and changelog pages.
- Use sitemap paths (`sitemap.xml` / `sitemap-posts.xml`) to distinguish product pages, docs, and blog topic cadence.

## 2. App Store Review Sentiment Triage (iOS RSS)

```bash
curl -s "https://itunes.apple.com/rss/customerreviews/id=[APP_ID]/sortBy=mostRecent/json" |   python3 -c "
import sys, json
data = json.load(sys.stdin)
for e in data.get('feed', {}).get('entry', [])[1:]:
    rating = e.get('im:rating', {}).get('label', '?')
    title = e.get('title', {}).get('label', '')
    content = e.get('content', {}).get('label', '')
    print(f'[{rating}] {title}: {content[:200]}')
"
```

Classify customer reviews into: **Praise** (defend), **Feature requests** (opportunity gaps), **Bugs** (reliability signals), and **UX complaints** (onboarding/workflow friction).

## 3. Public Job-Board Hiring Signals (Greenhouse Example)

```python
import requests

def department_counts(company_token: str) -> dict[str, int]:
    jobs = requests.get(
        f"https://boards-api.greenhouse.io/v1/boards/{company_token}/jobs",
        timeout=15,
    ).json().get("jobs", [])
    counts: dict[str, int] = {}
    for job in jobs:
        listed = job.get("departments") or []
        dept = (listed[0].get("name") if listed else None) or "Unknown"
        counts[dept] = counts.get(dept, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))
```

Track engineering vs sales/CS ratio, stack mentions, AI/ML investments, and compliance/security hiring.

## 4. UX Friction & 12-Dimension Scorecard Checklists

- **Onboarding UX audit**: time-to-first-value (TTFV), steps to activation, email/card gating, empty-state quality, mobile parity (iOS vs Android), and IA/searchability.
- **12-dimension scoring (1–5)**: Features, Pricing, UX, Performance, Docs, Support, Integrations (native vs Zapier), Security/Compliance, Scalability, Brand, Community, Innovation.
- **Action roadmap**: separate Quick Wins (0–4 weeks), Medium-Term (1–3 months), and Strategic bets (3–12 months), citing `[N]` URLs and access dates.
