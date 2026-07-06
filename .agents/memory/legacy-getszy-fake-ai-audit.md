---
name: Legacy-getszy fake-AI-output audit
description: User explicitly rejects randomized/templated data presented as "AI analysis"; checklist and precedent for auditing this in future sweeps.
---

The user (Getszy owner) explicitly and repeatedly rejects "hallucinations" — meaning any feature that *looks* like it did real AI/data analysis but actually returns randomized or hardcoded values. This is a higher bar than just "no mock API responses" — it also covers real, wired-up features that fake the *quality* of their output.

**Why:** found in `sourcing/trending.py` — `trend_score` was `random.randint(72, 98)` and `sources` was a hardcoded `['Google Trends IN', 'AI Niche Match', 'Audience Fit']` list, both presented in the admin UI as if they came from real trend analysis. This is exactly the category of bug the user calls out, distinct from "coming soon" placeholders (which are fine if honestly labeled) or the Razorpay/fal.ai deferred scope (fine, explicitly out of scope).

**How to apply:** when auditing this app (or building similar AI-feature products) for "no hallucination":
1. Grep for `random.randint`/`random.choice`/`random.uniform` near fields with names like `score`, `trend`, `rating`, `confidence`, `demand` — these are the highest-risk spots for fake-precision output.
2. Distinguish: random values used for realistic *ranges* (e.g. sourcing cost estimates within a curated niche's known price band) are acceptable — they're not claiming to be an analysis result. Random values standing in for an *analysis/score* that the UI presents as AI-derived are not acceptable.
3. Fix pattern used: replace the random score with a real `chat_completion` call asking the LLM to output a genuine JSON-scored assessment, with a clearly-labelled neutral fallback (not a random fallback) if the LLM call fails — see `_llm_demand_score` in `sourcing/trending.py`.
4. Honest "dry-run"/"coming soon" states (e.g. `publishing/adapters.py`, `routes_deploy.py` GITHUB_TOKEN missing) are NOT hallucinations as long as the UI clearly labels them (amber "dry-run" badge, explicit "not configured" message) — no fix needed there, don't waste time re-litigating already-labeled honesty.
