# getszy.com — Development Plan (MVP → Platform)

## 1) Objectives
- Deliver **V1 of getszy.com**: women/girls/kids focused storefront + dropshipping management, with a **natural-language “AI Admin Chat”** that can run core admin actions (talk-to-manage).
- Establish a scalable foundation for future modules: **AI Learning Academy**, **AI Studio (fal.ai)**, **Talk-to-Build App Generator**, **Multi-agent team dashboard**, and final **VPS deployment to getszy.com**.
- Keep secrets/env clean; ship with seed data; ensure end-to-end flows are tested and stable.

---

## 2) Implementation Steps (Phased)

### Phase 1 — Core POC (Isolation): LLM → Structured Admin Actions
**Core risk:** Natural-language commands reliably mapped to safe CRUD operations (LLM integration).  
**Goal:** Prove the AI Admin Chat can execute at least 6 intents end-to-end using Emergent LLM key.

Steps:
1. **Web best-practices check** (short): function-calling / tool-calling patterns, JSON schema validation, safe execution.
2. Create a minimal **Python POC script**:
   - Calls Emergent LLM (via `emergentintegrations`).
   - Uses a strict tool schema for intents: `add_product`, `update_product`, `list_orders`, `update_order_status`, `show_low_stock`, `show_stats`.
   - Validates tool arguments (pydantic) and simulates DB calls (or hits a tiny local FastAPI stub).
3. Iterate prompts/tool schema until:
   - Tool calls are consistent (no free-text when tool expected).
   - Partial info triggers follow-up questions.
   - Unsafe requests are rejected (e.g., deleting everything).

**Phase 1 user stories (POC):**
1. As an admin, I can type “Add product …” and receive a structured action payload.
2. As an admin, I can type “Show low stock” and get a structured query intent.
3. As an admin, I can type “Update order … shipped … tracking …” and get validated fields.
4. As an admin, I can type vague commands and the AI asks clarifying questions.
5. As an admin, I can type unsafe commands and the system refuses safely.

Exit criteria:
- POC script succeeds 10/10 runs on the 6 intents with valid JSON/tool calls.

---

### Phase 2 — V1 App Development (MVP): Storefront + Dropshipping + Admin Dashboard + AI Chat
**Build around proven POC.** Keep payments out (checkout UI only).

Backend (FastAPI + MongoDB/Motor):
1. Project scaffolding + env config (`MONGO_URL`, `JWT_SECRET`, `EMERGENT_LLM_KEY`).
2. Data models: `User(role)`, `Category`, `Supplier`, `Product(dropship fields)`, `Order/OrderItem`, `CartItem`, `AdminChatMessage`.
3. Core APIs (all prefixed `/api`):
   - Auth: `/auth/signup`, `/auth/login`, `/auth/me` (JWT)
   - Catalog: `/categories`, `/products` (list/filter/search), `/products/{id}`
   - Admin CRUD: `/admin/products`, `/admin/categories`, `/admin/suppliers`
   - Cart: `/cart` (get/add/update/remove)
   - Orders: `/orders` (place, list mine), `/admin/orders` (list all, update status + tracking)
   - Admin stats: `/admin/stats`
   - **AI Admin Chat:** `/admin/chat` (tool-calling → executes real DB actions)
4. Seed script: 7 categories + 2 suppliers + ~12 demo products + 1 admin + 1 demo customer.

Frontend (React + Tailwind + shadcn/ui):
1. Design pass (feminine-premium modern): typography, palette, reusable components.
2. Public pages: Home, Shop, Category, Product, Cart, Checkout (UI), Login/Signup.
3. Customer area: Account (profile + orders).
4. Admin area: Dashboard, Products, Orders, Suppliers, Customers, **Admin Chat**.
5. UX states: loading/empty/error, toasts, optimistic updates where safe.

**Phase 2 user stories (V1):**
1. As a visitor, I can browse categories and products with a premium, women-first design.
2. As a shopper, I can add/remove items in cart and reach checkout (payment coming soon).
3. As a user, I can sign up/login and view my profile + order history.
4. As an admin, I can manage products/suppliers/orders via dashboards (manual fallback).
5. As an admin, I can run “talk-to-manage” commands to add/update products and update orders.
6. As an admin, I can see low-stock and revenue/order stats on the dashboard.

End of phase:
- Run **testing_agent_v3**: storefront → cart → checkout UI, admin CRUD, AI chat intents, order status updates.

---

### Phase 3 — Hardening + Dropshipping Workflow Upgrades (Still MVP)
1. Strengthen AI chat safety:
   - Role-guarding (admin-only), allowlist tools, audit logs, confirmations for destructive actions.
2. Dropshipping management:
   - Supplier-level defaults (shipping time, contact, notes)
   - Order “Forwarded to supplier” state + supplier notes + tracking updates
   - Profit reporting per order (cost vs selling)
3. Basic media handling:
   - Product images via URL (V1) + optional upload support later
4. Refactor into modular services + validation improvements.

**Phase 3 user stories:**
1. As an admin, I can forward an order to a supplier and track its lifecycle.
2. As an admin, I can see profit per order and overall profit summaries.
3. As an admin, I can confirm risky AI actions before they execute.
4. As a shopper, I can see order status updates in my account.
5. As an admin, I can audit what the AI changed (chat action log).

End of phase:
- Run **testing_agent_v3** again (focus: order lifecycle + AI safety + stats correctness).

---

### Phase 4 — AI Learning Academy + VPS LLM Swap
1. Add course models: `Course/Module/Lesson`, enrollments, progress.
2. AI Tutor:
   - RAG over lesson content (MVP: vector store + citations).
3. **LLM adapter layer**:
   - Switch from Emergent → user’s VPS endpoint (Ollama/vLLM) via env flag.

**Phase 4 user stories:**
1. As a learner, I can browse courses and enroll.
2. As a learner, I can track progress and resume lessons.
3. As a learner, I can ask the AI tutor questions with references.
4. As an admin, I can create/edit courses and lessons.
5. As the owner, I can switch AI provider (Emergent ↔ VPS) without code changes.

End of phase:
- testing_agent_v3: enroll → progress → tutor Q&A → admin course CRUD.

---

### Phase 5 — AI Studio (fal.ai) + Subscriptions (Razorpay)
1. fal.ai integration POC (single endpoint each): image + short video + voice.
2. Subscription plans (Basic/Pro/Premium) + credits.
3. Razorpay integration (payments + webhook POC first), then wire into app.

**Phase 5 user stories:**
1. As a user, I can subscribe and receive monthly generation credits.
2. As a user, I can generate images from prompts and download/share results.
3. As a user, I can generate short cinematic clips (reels-style) with limits.
4. As an admin, I can view usage and cost metrics.
5. As the owner, I can cap per-user spend to protect margins.

End of phase:
- testing_agent_v3: subscribe (test mode) → generate → gallery → credit decrement.

---

### Phase 6 — Talk-to-Build App Generator + Multi-Agent Team
1. Code-gen templates (React/FastAPI) + ZIP export + optional GitHub push.
2. Multi-agent orchestration (planner/coder/reviewer/tester) with job queue + logs.

**Phase 6 user stories:**
1. As a user, I can describe an app and receive a runnable codebase.
2. As a user, I can preview the generated app and download ZIP.
3. As a user, I can request fixes in chat and regenerate incrementally.
4. As an admin, I can monitor generation jobs and failures.
5. As the owner, I can plug in better coder models on VPS.

---

### Phase 7 — Deployment to User VPS (getszy.com)
1. Dockerize: frontend + backend + nginx; choose MongoDB Atlas or self-host.
2. Provision on VPS: nginx reverse proxy, SSL (Let’s Encrypt), systemd/docker compose.
3. Push code to GitHub repo `jaunjatjai2300-blip/getszy` + optional CI/CD.
4. Final smoke test on domain.

**Phase 7 user stories:**
1. As the owner, I can deploy the platform to getszy.com reliably.
2. As a user, the site loads fast with SSL and correct routing.
3. As an admin, I can log in and manage store from production.
4. As a customer, I can browse/shop without broken links.
5. As the owner, I can update via git pull + redeploy with minimal downtime.

---

## 3) Next Actions (Immediate)
1. Start Phase 1 POC: implement tool schema + Python test script for Emergent LLM function-calling.
2. After POC passes, proceed to Phase 2 V1 build (backend+frontend in one cohesive pass).
3. Run testing_agent_v3 and fix until green.
4. Confirm VPS deployment details (SSH access, domain DNS, Mongo choice) before Phase 7.

---

## 4) Success Criteria
- Phase 1: LLM tool-calling POC is stable (consistent, validated, safe) across core intents.
- Phase 2: End-to-end V1 works: browse → cart → checkout UI; admin CRUD; AI admin chat executes real DB actions.
- Phase 3+: Dropshipping lifecycle + auditability + safety improvements verified.
- Phase 7: Production deployment on **getszy.com** with SSL, stable uptime, and no secrets in repo.
