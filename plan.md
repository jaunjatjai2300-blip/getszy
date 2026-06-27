# getszy.com — Development Plan (MVP → Platform)

## 1) Objectives
- Deliver a production-ready **women-first commerce platform** (physical + digital products) with **dropshipping ops**.
- Provide a Natural-Language **“AI Admin Chat”** (talk-to-manage) that safely executes admin actions.
- Provide an **AI Learning Academy for women** (courses + progress + certificate) with a context-aware **AI Tutor**.
- Run AI on the user’s own infrastructure: **provider-agnostic LLM layer** with **VPS Ollama** as the primary runtime (free, CPU-only).
- Build the next growth engine: **Talk-to-Build Studio** (ECC-inspired) — natural language → AI multi-agent pipeline → website/app artifacts.
- Prepare monetization foundations (later): **Razorpay subscriptions + credit limits**, and then **fal.ai media studio** (image/video/voice) when the user is ready.
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

### Phase 4 — TALK-TO-BUILD Studio (ECC-style Multi-Agent Website Generator) ⭐ **CURRENT PHASE**
**Goal:** Logged-in user describes a website in natural language → AI multi-agent pipeline generates a **single-page website** (one HTML file) → **live preview iframe**, iterative refinements, ZIP download, project history.

#### Context updates
- Production is live at **https://getszy.com**.
- VPS: **8 vCPU, 32GB RAM, 400GB NVMe, AlmaLinux 9**, **no GPU**.
- Ollama is live and reachable from Docker.
- fal.ai will be integrated **last** (user needs time for cost/pricing clarity).

#### Realistic Scope (CPU-only)
- Use **single-file HTML** with inline Tailwind (CDN) + minimal JS for speed.
- Multi-agent UX (Planner → Coder → Reviewer) simulated as stages (all via `chat_completion`).
- Generation timeout: ~5 minutes max.
- Refinement: follow-up prompt passes previous HTML + change request (diff-style guidance).
- Full-stack React/FastAPI generators deferred to later (needs heavier models / more time).

### Phase 4A — Backend: Builder Models + APIs
Add `routes_builder.py` + Mongo collections:
- `BuilderProject`:
  - `id`, `user_id`, `name`, `prompt`
  - `html_content`
  - `history[]` (timestamp, prompt, html_snapshot)
  - `created_at`, `updated_at`

Endpoints (auth required):
- `POST /api/builder/projects` → create project and generate HTML
- `GET /api/builder/projects` → list user projects
- `GET /api/builder/projects/{id}` → fetch project + history
- `POST /api/builder/projects/{id}/refine` → refine current HTML
- `DELETE /api/builder/projects/{id}`
- `GET /api/builder/projects/{id}/download` → ZIP with `index.html`
- `GET /api/builder/projects/{id}/preview` → raw HTML for iframe

LLM usage:
- Uses `chat_completion()` from `llm_provider.py` (currently Ollama qwen2.5:7b).

Safety:
- Sanitize output (no secrets).
- Add guardrails: disallow malicious JS, external POST beacons.
- Ensure preview endpoint sets safe headers; iframe uses sandbox.

### Phase 4B — Frontend: /studio Talk-to-Build UI
New route/pages:
- `/studio`

UI layout (responsive):
- Left sidebar: project list + “New project”
- Middle: chat prompt + stage progress UI (Planning → Coding → Reviewing)
- Right: Live preview iframe + toggle Code/Preview

Core actions:
- Prompt suggestions (portfolio, restaurant, AI tool landing)
- Create project → show build stages → render result in preview
- Refinement chat → updates preview
- Download ZIP button
- Delete project

Navigation:
- Header: add **Studio** link

### Phase 4 Testing
- `testing_agent_v3`:
  - Login → open /studio → generate site → refine → download zip → multiple projects
  - Regression: Phase 1–3 features still work (storefront, admin, academy)

**Phase 4 Exit criteria:**
- User can build/refine/download multiple single-page sites reliably.
- Preview is safe (sandboxed) and fast enough for CPU.
- No regressions.

---

### Phase 5 — Multi-Agent Job Dashboard (visual orchestration UI) ⏳ **NEXT**
- Job queue for long-running generations
- Real-time stage logs and retries
- Audit trail for admin + builder operations

---

### Phase 6 — Razorpay Subscriptions + Credit System (Gating) ⏳
**Goal:** Monetize builder and future AI studio with plans + quotas.
- Razorpay integration + webhooks
- Plans (draft): Starter/Pro/Studio/Cinematic
- Credit ledger + usage caps
- Admin finance dashboard: revenue vs infra cost

---

### Phase 7 — fal.ai AI Studio (Image/Video/Voice) ⏳ **LAST**
**Trigger to start:** user provides `FAL_KEY` + decided pricing/credits.

Planned:
- fal.ai generation endpoints (image/video/voice/music)
- Credit decrement per generation
- Gallery/history + downloads
- Spend caps + abuse prevention

Testing:
- Subscribe → generate → credits decrement → history

---

## 3) Next Actions (Immediate)
1. Start **Phase 4A**: implement `routes_builder.py` + BuilderProject model + preview/download endpoints.
2. Start **Phase 4B**: build `/studio` UI with projects sidebar + chat + iframe preview.
3. Add stage-based multi-agent prompting (planner/coder/reviewer) using `chat_completion`.
4. Run `testing_agent_v3` and fix until green.
5. After Phase 4 stable: proceed Phase 5 (job dashboard) → Phase 6 (Razorpay) → Phase 7 (fal.ai).

---

## 4) Success Criteria
- Phase 1–2: ✅ Done — stable V1 commerce + admin + AI Admin Chat.
- Phase 3: ✅ Done — Academy shipped; provider layer shipped.
- Phase 3B: ✅ Done — Production deploy on **https://getszy.com** with SSL + Docker + Ollama.
- Phase 4: Talk-to-Build Studio shipped (generate/refine/preview/download; multi-project; safe iframe).
- Phase 6: Subscriptions + credits gate usage safely.
- Phase 7: fal.ai AI Studio integrated last with spend caps and profitable pricing.
