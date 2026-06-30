# getszy.com — Development Plan (MVP → Platform)

## 1) Objectives
- Deliver a production-ready **women-first commerce platform** (physical + digital products) with **dropshipping ops**.
- Provide a Natural-Language **“AI Admin Chat”** (talk-to-manage) that safely executes admin actions.
- Provide an **AI Learning Academy for women** (courses + progress + certificate) with a context-aware **AI Tutor**.
- Run AI on the user’s own infrastructure: **provider-agnostic LLM layer** with **VPS Ollama** as the primary runtime (free, CPU-only) and hosted fallback.
- Build creator growth tools:
  - **Talk-to-Build Studio** (ECC-inspired) — natural language → multi-agent pipeline → deployable artifacts.
  - **Media Studio** (image/logo now; voice/video/mirror next) with subscription quotas.
- Build revenue engines:
  - **Dual dropshipping** (CJ Dropshipping + India fast shipping via Shiprocket + Getszy-branded sourcing layer).
  - **Subscription tiers + quotas** (Razorpay later when keys are provided).
- Build power-user operations:
  - **AI Ops Dashboard** to monitor agents.
  - **Master Build-&-Deploy Dashboard** to safely push updates to GitHub and deploy to VPS.
- Maintain clean ops: secrets in env only, seed data, audit logs, deployment docs, and full end-to-end testing at each phase.

---

## 2) Implementation Steps (Phased)

### Phase 1 — Core POC (Isolation): LLM → Structured Admin Actions ✅ **COMPLETED**
**Goal achieved:** Natural-language admin commands reliably mapped to safe structured actions.

Completed:
1. Strict JSON intent schema + safety rules.
2. Validated tool outputs and refusal/clarification behavior.
3. Confirmed intent parsing stability.

Exit criteria met:
- POC succeeded consistently.

---

### Phase 2 — V1 App Development (MVP): Storefront + Dropshipping + Admin Dashboard + AI Chat ✅ **COMPLETED**
**Goal achieved:** Full V1 storefront + admin dashboard + AI Admin Chat shipped.

Delivered:
- Storefront pages: Home, Shop, Category, Product Detail, Cart, Checkout (COD UI), Login/Signup, Account (orders)
- Admin: Dashboard KPIs + charts, Products CRUD, Orders CRUD (status + tracking), Suppliers CRUD, Customers list
- **AI Admin Chat (Hero Feature):** Executes DB actions; sessions + history; result cards
- Seed data: categories, suppliers, demo products, admin + customer
- **testing_agent_v3:** 100% pass

Notes:
- Payments not integrated yet.

---

### Phase 3 — AI Learning Academy + LLM Provider Abstraction ✅ **COMPLETED**
**Goal achieved:** Academy shipped end-to-end and LLM runtime abstracted.

Delivered:
- `/academy` catalog + filters
- `/academy/:slug` course detail + curriculum
- `/academy/:slug/learn` learning UI (lesson list + video + AI tutor)
- Progress tracking + certificate JSON payload
- Account “Learning” tab
- Admin Courses manager `/admin/courses` (course CRUD + lesson CRUD)
- AI Admin Chat extended intents (create_course, list_courses, show_enrollments)

LLM provider layer:
- Added `llm_provider.py` with env-driven provider swap:
  - `LLM_PROVIDER=emergent` (initial)
  - `LLM_PROVIDER=ollama` (VPS)

Testing:
- Backend: 55/55 passed in staging.
- Frontend: verified working.

---

### Phase 3B — Production Deployment to getszy.com + VPS Ollama ✅ **COMPLETED**
**Goal achieved:** Live production deployment on user VPS with SSL, Docker, and Ollama.

Delivered:
- Domain live: **https://getszy.com**
- Docker stack: MongoDB + FastAPI backend + React frontend + Caddy SSL proxy
- VPS bootstrap script + compose files added
- Fixed deployment issues:
  - Private repo access (made public for deploy)
  - `.env.example` omitted by GitHub sync → created `.env` manually
  - `yarn.lock` missing → patched Dockerfile.frontend to not require it
  - `emergentintegrations` install in Docker → added `--extra-index-url`
  - Ollama binding issue (127.0.0.1) → set `OLLAMA_HOST=0.0.0.0:11434`

Current runtime:
- `LLM_PROVIDER=ollama`
- `OLLAMA_MODEL=qwen2.5:7b`
- AI Admin Chat and AI Tutor working on VPS (free).

---

### Phase 4 — TALK-TO-BUILD Studio (ECC-style Multi-Agent Website Generator) ✅ **COMPLETED**
**Goal achieved:** Logged-in user describes a website in natural language → multi-agent pipeline generates a **single-page website** with preview, refinement, download.

Delivered:
- Backend `routes_builder.py` with project CRUD, refine flow, preview, ZIP download
- Frontend `/studio` with stage progress (Planner → Coder → Reviewer), live preview, project history
- Subscription gating integrated (Free blocked, Pro/Elite allowed)

Testing:
- `testing_agent_v3` passed and regressions clear.

---

### Phase 5 — Multi-Agent AI Operations Dashboard (`/admin/ai-ops`) ✅ **COMPLETED**
**Goal achieved:** Admin can monitor live agent activity, stats, intents, and activity feeds.

Delivered:
- Backend: `routes_ai_ops.py`
- Frontend: `AiOps.jsx`
- Admin-only access control

Testing:
- `testing_agent_v3` **100% pass** (Iteration 5) including regressions.

---

### Phase 6 — Monetization Engine (Plans + Gating + Quotas, Razorpay Stub) ✅ **COMPLETED**
**Goal achieved:** Subscription plans with gating logic shipped; Razorpay remains stubbed until keys provided.

Delivered:
- Free/Pro/Elite plans
- Course gating (Advanced courses locked for Free)
- Studio build quotas by plan
- Admin endpoints for subscription stats and plan grants

Notes:
- Razorpay real payment integration deferred until user shares keys.

---

### Phase 7 — Dual Dropshipping (CJ + Shiprocket + Getszy Source) ✅ **COMPLETED**
**Goal achieved:** A CJ-style dropshipping ops layer + India 5–6 day shipping readiness + automated trending discovery.

Delivered:
- **Admin Sourcing dashboard** `/admin/sourcing`
- **Getszy Source (India)**: AI-curated trending products feed + 1-click import
- **CJ Dropshipping scaffolding** (key-gated): safe “not_configured” responses until env keys provided
- **Shiprocket scaffolding** (key-gated): safe “not_configured” responses until env keys provided
- **Margin Guard**:
  - Physical products enforce **true 40% margin floor**
  - Digital products enforce **70%+ margin floor**

Critical Fix (during testing):
- Margin math bug fixed:
  - Physical markup **1.40 → 1.6667** (true 40% margin)
  - Digital markup **3.50 → 3.333** (true 70% margin)

Testing:
- `testing_agent_v3` **100% pass** (Iteration 6: 45/45 backend + full frontend)

---

### Phase 8 — Open-Source Media Studio (Pollinations + Scaffolding for HF/fal.ai) ✅ **COMPLETED**
**Goal achieved:** Production-ready Media Studio page with quotas and gallery; image + logo generation live (no API key).

Delivered:
- Frontend: **Media Studio** `/studio/media`
- Backend: `/api/media/*`
  - `GET /media/tools`, `GET /media/quota`, `GET /media/history`
  - `POST /media/image` (Pollinations.ai, no key)
  - `POST /media/logo` (Pollinations.ai, 4 variants)
  - `POST /media/voice|video|mirror` return **pending_provider** until HF_TOKEN or FAL_KEY is configured
- **Per-plan daily quotas** integrated (Free/Pro/Elite)

Notes:
- fal.ai integration remains planned upgrade (Phase 11) once user shares `FAL_KEY`.

Testing:
- Included in Iteration 6 (100% pass).

---

### Phase 9 — Master Build-&-Deploy Dashboard (GitHub Auto-Deploy + Agent Swarm) ⭐ **NEXT**
**Goal:** From admin dashboard, run multi-agent orchestration to:
1) plan/code/review changes, 2) commit/push to GitHub, 3) deploy safely to VPS.

User-provided deployment info:
- Repo: `https://github.com/jaunjatjai2300-blip/getszy`
- GitHub PAT: provided (must be stored in env; user should rotate after setup)

Scope:
- **Agent Swarm Orchestrator**:
  - Orchestrator → Planner → Coder → Designer → Reviewer → Deployer
  - Live logs to AI Ops (reuse activity feed patterns)
- **Safe auto-deploy**:
  - GitHub commit with clear message + change summary
  - VPS deploy trigger (webhook endpoint or SSH pull script)
  - Rollback strategy (keep last known good commit hash)

Deliverables:
- Backend:
  - `routes_deploy.py` (admin-only)
  - Secure secrets via `.env` (GITHUB_TOKEN, REPO_URL, DEPLOY_STRATEGY)
  - Optional: signed deploy webhook secret
- Frontend:
  - `/admin/deploy` (or `/admin/swarm`) dashboard
  - “Build → Review → Deploy” pipeline UI
  - Deploy history + status

Testing:
- `testing_agent_v3`:
  - non-admin blocked
  - build dry-run
  - successful GitHub push (mock in test)
  - deploy endpoint smoke test

---

### Phase 10 — Auto-Marketing Engine (YouTube/Instagram/Facebook Automation) ⏳ **PLANNED**
**Goal:** Automate content creation + posting + basic ad workflows to maximize earnings.

Planned features:
- Trending product → auto-generate:
  - Product creatives (images/videos) using Media Studio
  - Captions, hashtags, hooks
  - Posting schedule (reels/shorts/carousels)
- Integrations (when user provides keys):
  - Meta Business API (FB + Instagram)
  - YouTube Data API
- ROI dashboard:
  - Track clicks/leads/orders (UTM tagging)

Testing:
- Dry-run mode first (no posting) → then gated live mode.

---

### Phase 11 — fal.ai Premium Media Studio (4K Video + Mirror + Voice) ⏳ **DEFERRED until GPU phase**
**Trigger to start:** user provides `FAL_KEY` and finalizes pricing/credits.

Planned:
- Replace pending_provider stubs with fal.ai calls
- Credit decrement per generation
- Spend caps + abuse prevention

---

### Phase 12 — Creator OS (Indian Creators) ✅ **COMPLETED**
**Goal achieved:** All-in-one workflow for Indian content creators — script writing, trend forecasting, hook optimization, viral probability scoring, competitor gap spy, and multi-format repurposing — all powered by the existing LLM provider abstraction (Emergent / Ollama) and ready for GPU swap-in via `creator/providers.py`.

Delivered:
- Backend `creator/` package: `scripts.py`, `trends.py`, `providers.py`
- Backend `routes_creator.py` (auth-gated REST):
  - `GET /api/creator/formats` — 7 supported formats
  - `GET /api/creator/providers` — readiness map across image/video/voice/mirror/music/upscale
  - `POST /api/creator/script` — multi-format script generator (Hinglish/Hindi/English)
  - `POST /api/creator/score-hook` — first-3-seconds hook scoring (0-100) + rewrite
  - `POST /api/creator/viral-score` — pre-publish viral probability + drivers/risks
  - `POST /api/creator/trends` — 8 trending topics for next 14 days in any niche
  - `POST /api/creator/competitor-gap` — 5 content gaps to exploit
  - `POST /api/creator/repurpose` — one topic → multiple formats
  - `GET /api/creator/history` — recent creator assets
- 4 new Skills Marketplace entries (`write_script`, `predict_trends`, `hook_optimizer`, `viral_score`)
- Frontend `/admin/creator` Creator OS dashboard with 6 tabs (Script, Trends, Hook, Viral, Repurpose, Spy)
- Sidebar nav entry "Creator OS"
- Provider readiness badges visible in dashboard header
- GPU-ready abstraction (`creator/providers.py`) so fal.ai / Replicate / self-hosted GPU can be swapped in via `MEDIA_PROVIDER` env when user migrates VPS → GPU.

Testing:
- `testing_agent_v3` Iteration 12: **100% pass** — 13/13 backend endpoints + all frontend tabs verified end-to-end.

---

### Phase 13 — Faceless Video Maker MVP ⭐ **NEXT**
**Goal:** Script → Voice → Stock visuals → Auto-edited video pipeline.

### Phase 14 — Multi-Platform Publishing
YouTube + Instagram + Facebook scheduled auto-post (when API keys provided).

### Phase 15 — Creator Business OS
Sponsorship CRM, invoicing, affiliate hub.

### Phase 16 — AI Workforce
10 specialist agents (editor, designer, SEO, thumbnail, captions, …).

---

## 3) Next Actions (Immediate)
1. **Deploy current Phase 7 + 8 changes to VPS**:
   - User clicks **Save to GitHub (Force Push)** in Emergent UI
   - VPS:
     ```bash
     cd /opt/getszy
     git pull
     docker compose up -d --build
     ```
2. Confirm on production:
   - `/admin/sourcing` works (admin)
   - `/studio/media` works (customer)
3. Start **Phase 9**:
   - Decide deploy strategy: webhook vs SSH pull
   - Store GitHub PAT securely in `.env` and add repo URL
   - Build `/admin/deploy` (agent swarm + build/review/deploy)
4. Security cleanup:
   - Ask user to **rotate GitHub PAT** after Phase 9 is stable

---

## 4) Success Criteria
- Phase 1–2: ✅ Done — stable V1 commerce + admin + AI Admin Chat.
- Phase 3: ✅ Done — Academy shipped; provider layer shipped.
- Phase 3B: ✅ Done — Production deploy on **https://getszy.com** with SSL + Docker + Ollama.
- Phase 4: ✅ Done — Talk-to-Build Studio shipped (generate/refine/preview/download; safe iframe).
- Phase 5: ✅ Done — AI Ops Dashboard shipped and verified.
- Phase 6: ✅ Done — Plans/Quotas shipped; Razorpay still stubbed.
- Phase 7: ✅ Done — Dual dropshipping foundation + sourcing automation + margin guard.
- Phase 8: ✅ Done — Media Studio shipped (image/logo live; voice/video/mirror pending provider).
- Phase 9: Master Build-&-Deploy shipped (agent swarm + safe deploy + rollback).
- Phase 10: Auto-marketing shipped with dry-run then live posting.
- Phase 11: fal.ai premium media tools integrated last with spend caps and profitable pricing.
