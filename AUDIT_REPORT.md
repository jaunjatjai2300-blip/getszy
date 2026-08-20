# Getszy — Code Audit Report (Accurate)

**Repository:** https://github.com/jaunjatjai2300-blip/getszy.git
**Audit Date:** 2026-08-20
**Auditor:** opencode (CTO review)
**Scope:** Full repository as currently committed on `main`.

> **IMPORTANT — this report supersedes the previous `AUDIT_REPORT.md` (2026-08-17).**
> The prior report described a "modern workspace" with `artifacts/` and `lib/`
> directories and claimed the API had "only a `/healthz` endpoint", an "empty DB
> schema", "no auth", and "No CI". **None of that is true for the current repo.**
> Those directories do not exist. This report reflects the actual codebase.

---

## 1. Executive Summary

Getszy is an **AI-powered business-builder platform** implemented as a single
FastAPI + React monorepo under `legacy-getszy/`, deployed via Docker Compose + Caddy
with a real CI pipeline. The backend is **substantially engineered** (auth,
rate-limiting, migrations, backups, recovery workers, idempotency guards). It is a
**production-grade MVP**, not a skeleton.

The single blocking risk is a **live GitHub Personal Access Token committed to git
history**. Everything else is medium/low priority technical debt.

## 2. Architecture (actual)

| Layer | Stack | Notes |
|-------|-------|-------|
| Backend | FastAPI + Motor (async MongoDB) + Redis | ~210 Python files, ~44k LOC, 72 route modules, 40 test files |
| Frontend | React 19 + react-scripts (CRA) 5.0.1 + Radix + Tailwind + react-query/SWR | Modern component stack, but CRA is deprecated |
| Auth | bcrypt + HS256 JWT, Redis `jti` revocation, role hierarchy | visitor < customer < founder < admin |
| AI | Multi-provider (Groq, OpenRouter, HF, Gemini, Ollama, LM Studio) with fallback chain | Free-only cost guard |
| Media | FFmpeg video pipeline, TTS, image gen, catalog→video sync | |
| Commerce | Products/cart/orders, Razorpay subscriptions, credits, referrals | |
| Deploy | Docker Compose (Mongo, Backend, Frontend, Caddy) + VPS webhook | Caddy auto-TLS via Let's Encrypt |
| CI | GitHub Actions `ci.yml` | pytest + Mongo/Redis services, Bandit + Safety, deploy webhook w/ health verify |

`main.py` at repo root is a thin `uvicorn` shim that imports the FastAPI app from
`legacy-getszy/backend/server.py`. The root `package.json`, `pnpm-workspace.yaml`,
`tsconfig.base.json` are **leftover config from an abandoned TypeScript rewrite** and
do not build or run any application code — they should be removed or clearly archived.

## 3. Security Findings

| # | Issue | Location | Severity | Status |
|---|-------|----------|----------|--------|
| SEC-01 | **Live GitHub PAT committed to git history** (`ghp_[REDACTED]…`) | `attached_assets-security-backup/` (tracked, not gitignored) | **CRITICAL** | MUST FIX |
| SEC-02 | Seed passwords are placeholders in `.env.example` | `.env.example` | LOW | Acceptable (real `.env` must never be committed) |
| SEC-03 | CORS allowlist still includes `localhost:3000/5173` dev origins | `legacy-getszy/backend/server.py:93-98` | MEDIUM | Trim for prod |
| SEC-04 | `/metrics` (Prometheus) unauthenticated by design | `server.py:79-83` | MEDIUM | Block at Caddy edge |
| SEC-05 | Hardcoded YouTube URLs in startup migration | `server.py` startup | LOW | Cosmetic/tech-debt |

### 3.1 SEC-01 — Committed token (do this first)
The token allows force-push to the repository and is present in multiple pasted-text
files inside `attached_assets-security-backup/`. It is **not** covered by `.gitignore`.

**Required actions (see `PURGE_SECRETS.md` for exact commands):**
1. Revoke/rotate the token in GitHub **before** doing anything else.
2. Purge `attached_assets-security-backup/` (and any `attached_assets/`) from git history with `git filter-repo` or BFG.
3. Force-push the cleaned history.
4. Add `attached_assets*` to `.gitignore`.
5. Audit other clones on the machine (`getszy`, `getszy-repo`, `getszy-check`, the `.zip`) so the secret isn't re-pushed.

### 3.2 What is actually good
- JWT secret validated at startup (refuses default values) — `auth.py:11-13`.
- Constant-time login dummy hash + per-email/per-IP Redis throttling — `routes_auth.py`.
- CORS is a **restricted allowlist**, not `*`.
- Centralized exception handlers, structured logging, graceful LLM/Redis degradation.
- CI runs Bandit (high-sev) + Safety (CVE) and fails loudly on deploy failure.

## 4. Code Quality

**Backend — GOOD.**
- `auth.py`: proper hashing, revocation, role hierarchy, optional/required deps.
- `server.py`: migrations, TTL + unique + idempotency indexes, backup scheduler,
  stuck-job recovery, DPDP deletion worker — thoughtful production hardening.
- 40 test files present; CI runs the non-integration suite.
- Inconsistencies: some routes use Pydantic models, some manual dict validation; a
  few route files exceed 500 lines (refactor candidates, not blockers).

**Frontend — MODERN STACK, DEPRECATED TOOLING.**
- React 19 + Radix + Tailwind is current, but pinned to **CRA (`react-scripts`)**,
  which is deprecated and slow. Plan a Vite migration.
- `package.json` lists `lodash 4.18.1` — that version does not exist on npm
  (real latest is `4.17.21`). Fix the pin or remove lodash.

**Root config — DEAD/LEFT-OVER.**
- `package.json`, `pnpm-workspace.yaml`, `tsconfig.base.json`, `tsconfig.json`,
  `replit.md` describe an abandoned TS rewrite. `scripts/` is the only real workspace
  member. Either delete these or commit to the rewrite; don't carry both silently.

## 5. Dependency Management
- Python: `uv.lock` present, CI installs minus the private `emergentintegrations`
  index. `safety check` is gated in CI (ecdsa advisory ignored with rationale).
- Node: only the dead root workspace uses pnpm; frontend uses yarn/CRA.
- No evidence of the "600+ ML packages" claimed in the old audit; the backend keeps a
  reasonable dependency set.

## 6. Deployment & Infrastructure
- Docker Compose + Caddy (auto-HTTPS) + `deploy-vps.sh` + GitHub deploy webhook.
- CI post-deploy step verifies `/api/health` before marking green — good.
- Secrets are env-driven (good), but defaults in compose/`.env.example` must never
  reach production; verify `legacy-getszy/backend/.env` is gitignored.

## 7. Feature Completeness
Auth, products, cart, orders, Razorpay billing/credits, admin dashboard, AI chat
(multi-provider), video generation (FFmpeg), image generation, creator courses,
marketplace/sourcing, deploy/hosting, analytics, audit logs + IP blocking, API keys,
and system monitoring are **all implemented** in the legacy backend.

## 8. Recommendations

### 🔴 P0 — Immediate
1. **Rotate the committed GitHub PAT** and purge it from git history (`PURGE_SECRETS.md`).
2. **Rewrite this audit** (done) — retire the false 2026-08-17 report.

### 🟠 P1 — High
3. Remove dev CORS origins in production; block `/metrics` at the Caddy edge.
4. Migrate frontend CRA → Vite; fix/remove the `lodash 4.18.1` pin.
5. Delete or archive the abandoned-TS-rewrite root config (`package.json`, `pnpm-*`,
   `tsconfig*`, `replit*`) to avoid confusion.

### 🟡 P2 — Medium
6. Standardize request validation (Pydantic everywhere) and break up 500+ line routes.
7. Add Swagger/OpenAPI UI (spec exists).
8. Consolidate the multiple local repo clones on the dev machine.

## 9. Verdict
- **Backend: PRODUCTION-GRADE MVP.** Well-architected, tested, CI-gated.
- **Frontend: FUNCTIONAL, NEEDS MODERNIZATION** (CRA → Vite).
- **Overall risk: HIGH until SEC-01 (committed token) is resolved.** After the token
  is rotated and purged, risk drops to LOW-MEDIUM and the platform is shippable.

---

*End of Audit Report (rewritten 2026-08-20 to match the actual repository.)*
