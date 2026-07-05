# getszy.com — Development Plan (MVP → Platform)

## 1) Objectives
- Deliver a production-ready **women-first commerce platform** (physical + digital products) with **dropshipping ops**.
- Provide a Natural-Language **“AI Admin Chat / Neo”** (talk-to-manage + talk-to-build) that safely executes actions.
- Provide an **AI Learning Academy for women** (courses + progress + certificate) with a context-aware **AI Tutor**.
- Run AI on the user’s own infrastructure: **provider-agnostic LLM layer** with **VPS Ollama** as the primary runtime (free, CPU-only) and hosted fallback.
- Evolve Getszy into a **Universal Builder Studio** where **Neo (AI Assistant) is the OS**:
  - One chat-based front door for creators/founders to orchestrate everything.
  - Role-based surfaces: **Public**, **Customer Workspace** (`/dashboard`), **Admin Ops** (`/admin`), **Founder Labs** (`/labs`).
  - A single **Workspace** view where chat outputs are organized as **Preview / Plan / Tasks / Files / Timeline / Versions / Deploy**.
  - **One-click hosting/deploy loop** for AI-built webapps (preview path-based + production subdomain-ready).
- Build creator growth tools:
  - **Talk-to-Build Studio** (ECC-inspired) — natural language → multi-agent pipeline → deployable artifacts.
  - **Media Studio** (image/logo now; voice/video/mirror next) with subscription quotas.
  - **Faceless Video Studio** + **Publishing** + **Workforce Agents** — all orchestratable via Neo chat.
- Build revenue engines:
  - **Dual dropshipping** (CJ Dropshipping + India fast shipping via Shiprocket + Getszy-branded sourcing layer).
  - **Subscription tiers + quotas** with **Razorpay** (subscriptions only; pricing TBD; unconfigured mode supported).
- Build power-user operations:
  - **AI Ops Dashboard** to monitor agents.
  - **Master Build-&-Deploy Dashboard** (GitHub + VPS) to safely push updates and ship platform changes.
- Launch readiness:
  - **Legal & Compliance**: ToS, Privacy, DPDP/IT Act aligned; data export & deletion request.
  - **Support & Feedback**: FAQ, ticketing, feature voting.
  - **Accessibility (a11y)**: keyboard navigation, focus indicators, reduced-motion support, landmarks.
- Maintain clean ops: secrets in env only, seed data, audit logs, deployment docs, and full end-to-end testing at each phase.
- UX/Speed: Premium “OS-like” feel:
  - Global command palette
  - Skeleton loading
  - Motion transitions
  - Undo/Retry toasts
  - Dual-lane routing (fast lane vs heavy LLM lane)
  - Consistent routing across roles (no accidental navigation to admin routes)

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
- Payments not integrated at this phase.

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

### Phase 6 — Monetization Engine (Plans + Gating + Quotas) ✅ **COMPLETED**
**Goal achieved:** Subscription plans with gating logic shipped (Free/Pro/Elite).

Delivered:
- Free/Pro/Elite plans
- Course gating (Advanced courses locked for Free)
- Studio build quotas by plan
- Admin endpoints for subscription stats and plan grants

Notes:
- Billing provider integration added later (see Phase 21).

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

### Phase 9 — Master Build-&-Deploy Dashboard (GitHub Auto-Deploy + Agent Swarm) ✅ **COMPLETED (Core)**
**Goal achieved:** Admin can orchestrate build→push→deploy for platform changes.

Delivered:
- Backend: `routes_deploy.py` (admin-only)
  - Build job creation + agent outputs
  - Push to GitHub (marker commit)
  - Webhook trigger (when configured)
  - Job list/history
  - **NEW**: `GET /api/admin/deploy/commits` — recent GitHub commits for rollback context (gracefully handles 401/expired token)
- Frontend: `/admin/deploy` dashboard
  - Agent strip (Planner/Designer/Coder/Reviewer)
  - Brief → run swarm → push → trigger webhook
  - Job history
  - **NEW**: Recent commits panel

Notes:
- VPS webhook requires `DEPLOY_WEBHOOK_URL` to be set.
- GitHub integration depends on valid `GITHUB_TOKEN` + `GITHUB_REPO`.

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
**Goal achieved:** All-in-one workflow for Indian content creators — script writing, trend forecasting, hook optimization, viral probability scoring, competitor gap spy, and multi-format repurposing.

Delivered:
- Backend `creator/` package + `routes_creator.py` endpoints
- Skills Marketplace entries
- Frontend `/admin/creator` Creator OS dashboard
- Provider readiness badges + GPU-ready abstractions

Testing:
- `testing_agent_v3` Iteration 12: **100% pass**

---

### Phase 13 — Faceless Video Studio (10x automation) ✅ **COMPLETED**
**Goal achieved:** Topic → finished MP4 in ~60-120s, fully automated; batch mode for 10 videos.

Delivered:
- Backend `video/` package + `routes_video.py`
- edge-tts Indian voices, Pollinations + Pexels fallback
- FFmpeg pipeline fixes + `imageio-ffmpeg` fallback
- Frontend `/admin/video` Video Studio UI

Testing:
- iteration_13 — backend + frontend pass

---

### Phase 14 — Multi-Platform Publishing ✅ **COMPLETED**
**Goal achieved:** Auto-generate platform-specific captions and schedule across 5 platforms; dry-run preview until credentials added.

Delivered:
- Backend `publishing/` package + `routes_publishing.py`
- Frontend `/admin/publishing`

Testing:
- included in iteration_13

---

### Phase 15 — AI Workforce (10 specialist agents) ✅ **COMPLETED**
**Goal achieved:** 10 named AI personas to automate end-to-end creator operations.

Delivered:
- Backend `workforce/` package + endpoints
- Frontend `/admin/workforce`

Testing:
- included in iteration_13

---

### Phase 16 — Universal Build Studio (Hub) ✅ **COMPLETED**
**Goal achieved:** Unified `/admin/build` hub with 6 categories (web app, channel plan, custom agent factory, mobile starter, full-stack starter, blog starter) reusing existing builders.

Delivered:
- Backend: extended `routes_builder.py` + zip generators
- Frontend: `/admin/build` hub UI
- Admin bypass for quota

Testing:
- iteration_14 — near-full backend + 100% frontend

---

### Phase 17 — Universal AI Chat Builder (Neo as single front door) ✅ **COMPLETED**
**Goal achieved:** Single conversational entry point that dispatches to every existing capability; projects/messages/assets/events stored; streaming via polling.

Delivered:
- Backend `backend/chat_builder/` + `/api/chat/*`
- Frontend `ChatHome.jsx` used as primary chat surface
- Consolidated navigation (Neo as primary)

Testing:
- iteration_15 — **100% pass**

---

### Phase 18 — Neo as GetZzy OS (Role-based routing) ✅ **COMPLETED**
**Goal achieved:** Clear separation of role-based experiences.

Delivered:
- Frontend role routes:
  - `/dashboard` — Customer Neo Workspace
  - `/admin` — Platform Operations
  - `/labs` — Founder experimental zone

---

### Phase A — Dual-Lane LLM Routing (“Fast Lane”) ✅ **COMPLETED**
**Goal achieved:** Simple explicit requests bypass heavy LLM orchestration.

Delivered:
- Backend: `backend/chat_builder/fast_lane.py`
- Latency improvement observed (approx **40s → 16s** for simple turns)

---

### Phase B–E — UX Polish & Premium Feel ✅ **COMPLETED**
**Goal achieved:** OS-like UX polish across Neo workspace.

Delivered:
- Global **Command Palette** (`cmdk`) available across app
- **Skeleton loaders** for perceived performance
- **Framer Motion** transitions for premium feel
- **Undo/Retry toasts** (wired into `ChatHome.jsx`)

Critical Fix (P0):
- Resolved React Router crash: `useNavigate()` used outside router context.
- Fix applied: Moved `<CommandPalette />` **inside** `<BrowserRouter>` in `/app/frontend/src/App.js`.

Additional Fix:
- Session sidebar navigation is now **context-aware** (prevents customer from being redirected to admin routes):
  - `/dashboard/chat/:id` for customers
  - `/admin/chat/:id` for admins
  - `/labs/chat/:id` for labs

---

### Phase 19 — Workspace UI Tabs (Universal Builder Studio UI) ✅ **COMPLETED**
**Goal achieved:** Neo chat now has a true “Workspace OS” right pane with structured tabs.

Delivered:
- Frontend workspace tabs component:
  - File: `/app/frontend/src/components/workspace/WorkspaceTabs.jsx`
  - Tabs implemented: **Preview, Plan, Tasks, Files, Timeline, Versions, Deployments**
- Integrated into the Neo chat workspace:
  - Wired into `/app/frontend/src/pages/admin/ChatHome.jsx` (ChatWorkspace right column)
  - Preview tab uses existing asset rendering (webapp iframe, video player, script, trends, etc.)

---

### Phase 20 — Subdomain Auto-Hosting + One-click Deploy (Workspace Deploy Tab) ✅ **COMPLETED**
**Goal achieved:** Close the build→deploy→live loop for AI-built webapps.

Design note:
- Preview/staging: hosted sites served path-based at `GET /api/host/{slug}/`.
- Production-ready: Caddy wildcard subdomains `*.getszy.com` can reverse-proxy to `/api/host/{slug}/` with on-demand TLS gating.

Delivered:
- Backend: `/app/backend/routes_hosting.py`
- Frontend: Workspace → Deploy tab enhanced with deploy form + live sites + Caddy snippet.

---

### Phase 21 — Billing (Razorpay) + Onboarding + Compliance + Support + Accessibility ✅ **COMPLETED (Skeleton/Launch Readiness)**
**Goal achieved:** Emergent-level “launch readiness” layers shipped.

#### 21A — Razorpay Billing (subscriptions-only; pricing TBD) ✅
- Backend: `/app/backend/routes_razorpay.py`
  - `GET /api/billing/status`, `GET /api/billing/pricing`
  - `POST /api/billing/subscribe`, `POST /api/billing/verify`
  - `POST /api/billing/webhook`, `POST /api/billing/cancel`
  - Admin bootstrap: `POST /api/billing/admin/create-plans` (once final INR pricing is decided)
  - Works in **unconfigured mode** when Razorpay keys are missing (graceful responses).
- Frontend: `/pricing` updated
  - Monthly-only, INR, GST note
  - Shows “Payments not enabled” banner when unconfigured
  - Razorpay checkout script loads only when configured

#### 21B — Customer Onboarding Tour ✅
- Frontend: `/app/frontend/src/components/onboarding/OnboardingTour.jsx`
  - 4-step modal tour
  - Remembers completion via `localStorage.getszy.onboarding.v1`

#### 21C — Legal & Compliance ✅
- Frontend pages:
  - `/terms` — Terms of Service (IT Act 2000 + DPDP Act 2023 aligned)
  - `/privacy` — Privacy Policy + “Download my data” + “Request deletion” tools
- Backend: `/app/backend/routes_legal.py`
  - `GET /api/legal/data-export` — ZIP export (GDPR/DPDP style)
  - `POST /api/legal/data-delete` + status tracking
- Footer wired with links to Terms/Privacy/Support.

#### 21D — Support & Feedback ✅
- Backend: `/app/backend/routes_support.py`
  - `/api/support/faq`
  - Support tickets: create/list + admin update
  - Feature requests: create/list + vote (Canny-like)
- Frontend: `/support` page with tabs:
  - FAQ, Contact Ticket, Feature Requests + voting

#### 21E — Accessibility (a11y) ✅
- Global focus-visible outline across interactive elements.
- Skip-to-content link.
- Landmarks: `main#main-content` + `tabIndex={-1}` across layouts.
- Reduced-motion support via `prefers-reduced-motion`.
- Contrast improvement: `--gs-muted` darkened.
- Screen-reader utility `.sr-only`.

---

## 3) Next Actions (Immediate)
Now that the platform is “launch-ready” at the UX/compliance/support baseline, next priorities:

### Option 22A (P0) — Razorpay Activation (when account is created)
- Create Razorpay account + fetch keys
- Decide Pro/Elite INR monthly pricing
- Run `POST /api/billing/admin/create-plans` and set env:
  - `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`
  - `RAZORPAY_PLAN_PRO`, `RAZORPAY_PLAN_ELITE`
- Add webhook in Razorpay dashboard → `/api/billing/webhook`

### Option 22B (P0) — Workspace Deepening (remaining A2 items)
- Neo auto-writes **tasks** based on conversation (similar to plan generation)
- Richer **versions** (snapshot full state, not counts-only)
- Inline editing for scripts/HTML + re-deploy

### Option 22C (P1) — Crisp/Intercom-style Live Chat Widget
- Replace/augment ticketing with live chat (requires third-party keys)

### Option 22D (P1) — Real Social OAuth Posting
- Replace dry-run publishing with OAuth (YouTube/Meta/X/LinkedIn)

Operational note:
- Re-run frontend + backend smoke tests after enabling payments.

---

## 4) Success Criteria
- Phase 1–8: ✅ Done — stable V1 commerce + academy + media + sourcing.
- Phase 12–17: ✅ Done — Creator OS + Video + Publishing + Workforce + Universal Build + Universal Chat.
- Phase 18: ✅ Done — Role-based OS routing (`/dashboard`, `/admin`, `/labs`).
- Phase A–E: ✅ Done — Fast Lane routing + UX polish + router crash fixed + context-aware navigation.
- Phase 19: ✅ Done — Workspace tabs integrated and verified.
- Phase 20: ✅ Done — `/api/host/{slug}` hosting + deploy UI + Caddy snippet.
- Phase 21: ✅ Done — Razorpay skeleton + onboarding + legal + support + accessibility.
- Remaining external dependencies:
  - Razorpay account/keys (to activate billing)
  - Social OAuth keys (to enable real posting)
  - fal.ai key + GPU readiness (premium video/mirror)
