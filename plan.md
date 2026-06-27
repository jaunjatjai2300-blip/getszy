# getszy.com — Development Plan (MVP → Platform)

## 1) Objectives
- Deliver a production-ready **women-first commerce platform** (physical + digital products) with **dropshipping ops**.
- Provide a **Natural-Language “AI Admin Chat”** (talk-to-manage) that safely executes admin actions (already shipped in Phase 1).
- Build the next major growth module: **AI Learning Academy for women** with an **AI Tutor**.
- Introduce a **provider-agnostic LLM layer** so the whole platform can switch from **Emergent LLM → VPS Ollama** by flipping environment variables (no code rewrite).
- Prepare foundations for monetization modules: **AI Studio (fal.ai + subscriptions)** and **ECC-style Talk-to-Build** multi-agent code generation.
- Ensure clean ops: secrets in env only, seed data, audit logs, and full end-to-end testing.

---

## 2) Implementation Steps (Phased)

### Phase 1 — Core POC (Isolation): LLM → Structured Admin Actions ✅ **COMPLETED**
**Goal achieved:** Natural-language admin commands reliably mapped to safe structured actions.

Completed:
1. Built strict JSON intent schema + safety rules.
2. Validated tool outputs and refusal/clarification behavior.
3. Confirmed intent parsing is stable.

Exit criteria met:
- POC succeeded consistently.

---

### Phase 2 — V1 App Development (MVP): Storefront + Dropshipping + Admin Dashboard + AI Chat ✅ **COMPLETED**
**Goal achieved:** Full V1 storefront + admin dashboard + AI Admin Chat shipped.

Delivered:
- Storefront pages: Home, Shop, Category, Product Detail, Cart, Checkout (COD UI), Login/Signup, Account (orders)
- Admin: Dashboard KPIs + charts, Products CRUD, Orders CRUD (status + tracking), Suppliers CRUD, Customers list
- **AI Admin Chat (Hero Feature):** Executes real DB actions; shows result cards; sessions + history
- Seed data: categories, suppliers, demo products, admin + customer
- **testing_agent_v3:** 100% pass

Notes:
- Payments not integrated yet (planned for later).

---

### Phase 3 — Hardening + Dropshipping Workflow Upgrades ✅ **MERGED INTO PHASE 1/2 (DONE)**
Status update:
- Core dropshipping fields (supplier, cost_price, profit) are already implemented in V1.
- Order lifecycle states exist (pending/forwarded/shipped/delivered/cancelled).

Remaining hardening tasks (will be folded into later phases as needed):
1. Stronger AI action confirmations for destructive actions.
2. Expanded audit views (admin activity log UI).

---

### Phase 4 — **AI Learning Academy + LLM Provider Abstraction** ⭐ **CURRENT PHASE (Start now)**
**Goal:** Build the AI Learning Academy for women and make LLM usage provider-agnostic so we can swap **Emergent → VPS Ollama** with env vars.

#### Context updates
- User VPS is upgraded: **8 vCPU, 32GB RAM, 400GB NVMe, AlmaLinux 9**, **no GPU**.
- fal.ai key will be provided later; proceed without it.
- ECC inspiration confirmed for later multi-agent system.

### Phase 4A — LLM Provider Layer (Backend)
1. Add `llm_provider.py` abstraction with two backends:
   - `LLM_PROVIDER=emergent` (default now): uses `emergentintegrations` (`gpt-4o-mini`).
   - `LLM_PROVIDER=ollama` (future): uses HTTP calls to Ollama.
2. Env vars:
   - `LLM_PROVIDER=emergent|ollama`
   - `OLLAMA_BASE_URL=http://localhost:11434`
   - `OLLAMA_MODEL=qwen2.5:7b`
3. Refactor existing `ai_chat.py` to call the abstraction function (no behavior change expected).

**Exit criteria:**
- AI Admin Chat works exactly as before with `LLM_PROVIDER=emergent`.

### Phase 4B — Learning Academy Data Models + APIs (Backend)
Add a new module `routes_learning.py` + collections:
- `Course`: title, slug, level (Beginner/Intermediate/Advanced), description, outcomes, prerequisites, total_duration, thumbnail
- `Module`: course_slug, title, order
- `Lesson`: module_id, title, description, video_url, duration_min, order, resources
- `Enrollment`: user_id, course_slug, enrolled_at
- `LessonProgress`: user_id, lesson_id, completed_at
- `TutorMessage`: session_id, user_id, course_slug, lesson_id (optional), role, text, created_at

Endpoints:
- Public:
  - `GET /api/courses`
  - `GET /api/courses/{slug}`
- Auth (customer):
  - `POST /api/courses/{slug}/enroll` (free for Phase 4)
  - `GET /api/me/enrollments`
  - `GET /api/courses/{slug}/learn` (returns modules/lessons + progress)
  - `POST /api/lessons/{lesson_id}/complete`
  - `POST /api/courses/{slug}/tutor` (context-aware tutor)
  - `GET /api/me/courses/{slug}/certificate` (JSON certificate payload)
- Admin:
  - `POST/PUT/DELETE /api/admin/courses`
  - `POST/PUT/DELETE /api/admin/modules`
  - `POST/PUT/DELETE /api/admin/lessons`

AI Tutor behavior:
- Uses provider layer (`LLM_PROVIDER`) + course/lesson context in system prompt.
- Simple RAG-lite initially: include course outcomes + current lesson summary in prompt.
- Upgrade to real vector RAG in later iteration if needed.

### Phase 4C — Seed Academy Content
Seed 4 courses tailored for women (basic → advanced):
1. **AI Foundations for Women** (Beginner, 5 lessons)
2. **ChatGPT & Prompting Mastery** (Intermediate, 6 lessons)
3. **Build Income with AI — No Code** (Practical, 7 lessons)
4. **Become AI Independent — Career Path** (Advanced, 8 lessons)

Each lesson includes:
- Title, 2–4 line description, YouTube embed URL (placeholder/royalty-safe), duration, order

### Phase 4D — Frontend Learning Academy
New routes/pages:
- `/academy` (catalog)
- `/academy/:slug` (course detail)
- `/academy/:slug/learn` (learning UI: lesson list + video + AI Tutor)

UI requirements:
- Progress bar (X/Y lessons)
- Lesson lock/unlock based on enrollment
- Mark Complete button updates progress
- Certificate view available at 100%

Account updates:
- Add a **Learning** tab: enrolled courses + progress

Admin updates:
- Add `/admin/courses` UI: create/edit courses, modules, lessons

Navigation updates:
- Header: add **Academy** link
- Home: add section for **AI Learning Academy**

### Phase 4E — Extend AI Admin Chat with Learning Intents
Add intents (admin-only):
- `create_course`
- `add_lesson_to_course`
- `list_courses`
- `show_enrollments`

### Phase 4 Testing
- Run `testing_agent_v3` for:
  - Browse academy → enroll → learn → tutor chat → complete lessons → certificate
  - Admin courses CRUD + admin chat intents

**Phase 4 Exit criteria:**
- Academy works end-to-end, tutor responds, progress persists, certificate available.
- AI Admin Chat uses provider layer and remains stable.

---

### Phase 5 — AI Studio (fal.ai) + Subscriptions (Razorpay) ⏳ **NEXT (Waiting for fal.ai key)**
**Trigger to start:** user provides `FAL_KEY` + (optionally) Razorpay test keys.

Planned:
1. fal.ai integration endpoints:
   - Image: Flux
   - Video: Kling/Veo/Luma (short clips)
   - Voice: ElevenLabs (via fal.ai)
2. Credit-based subscription tiers:
   - Starter ₹499, Pro ₹1499, Studio ₹3999, Cinematic ₹9999
3. Razorpay payments + webhooks
4. Usage metering + spend caps + admin cost dashboard

Testing:
- Subscribe (test mode) → generate → credit decrement → gallery/history

---

### Phase 6 — Talk-to-Build App Generator + ECC-Style Multi-Agent Team ⏳
**Goal:** natural-language → multi-agent pipeline generates working apps.

Design:
- Agents: Planner → Coder → Reviewer → Tester → Deployer
- Default models on VPS Ollama (CPU):
  - `qwen2.5-coder:7b` (coding)
  - `qwen2.5:7b` or `llama3.1:8b` (planning/review)
- Outputs:
  - Project templates (React/FastAPI)
  - ZIP download
  - Optional GitHub push
  - Live preview

---

### Phase 7 — Master Multi-Agent Dashboard ⏳
- Job queue, real-time logs, agent status
- Output previews, retry, rollback
- Auditing and cost tracking

---

### Phase 8 — Deployment to User VPS (getszy.com) ⏳
**Target VPS:** AlmaLinux 9, 8 vCPU, 32GB RAM, no GPU.

Deployment stack:
1. Docker + Docker Compose
2. Containers:
   - Frontend (Nginx static)
   - Backend (uvicorn)
   - MongoDB
   - (Optional) Ollama service on host or container
3. Nginx reverse proxy + Let’s Encrypt SSL
4. Domain/DNS: `getszy.com` → VPS IP
5. GitHub push to `jaunjatjai2300-blip/getszy`

LLM swap final:
- Set:
  - `LLM_PROVIDER=ollama`
  - `OLLAMA_BASE_URL=http://localhost:11434`
  - `OLLAMA_MODEL=qwen2.5:7b`

**VPS capability notes:**
- Can run: `llama3.1:8b`, `qwen2.5:7b`, `qwen2.5-coder:7b` (CPU inference)
- Cannot run: image/video/voice generation (no GPU) → keep fal.ai

---

## 3) Next Actions (Immediate)
1. Start **Phase 4A**: implement LLM provider abstraction + refactor AI Admin Chat to use it.
2. Start **Phase 4B–4D**: build Learning Academy backend + frontend.
3. Seed 4 courses + lesson content.
4. Run `testing_agent_v3` and fix until green.
5. In parallel (when user ready): collect fal.ai key for Phase 5.

---

## 4) Success Criteria
- Phase 1–2: ✅ Done — stable V1 commerce + admin + AI Admin Chat.
- Phase 4: Academy shipped with AI Tutor; progress + certificate works; LLM provider can be swapped by env vars.
- Phase 5: fal.ai studio monetization works with spend caps + credit accounting.
- Phase 8: Production deployment to **getszy.com** with SSL, stable uptime, and secrets safe.