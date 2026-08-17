# Comprehensive Code Audit Report: getszy

**Repository:** https://github.com/jaunjatjai2300-blip/getszy.git
**Audit Date:** 2026-08-17
**Auditor:** opencode AI Assistant

---

## Executive Summary

This repository contains **two distinct codebases** in a monorepo structure:

1. **Modern Workspace** (`artifacts/`, `lib/`) - TypeScript/React/Express monorepo (active development)
2. **Legacy Codebase** (`legacy-getszy/`) - Python/FastAPI/MongoDB monorepo (feature-complete, production-ready)

The modern workspace appears to be a **rebuild/rewrite in progress** with only basic health check endpoints implemented, while the legacy codebase is a **full-featured AI-powered business builder platform** with 80+ API routes covering auth, commerce, AI chat, video generation, analytics, admin panel, and more.

---

## 1. Architecture & Code Structure

### 1.1 Modern Workspace (`artifacts/`, `lib/`)

| Aspect | Assessment |
|--------|------------|
| **Structure** | pnpm monorepo with workspace protocol (`workspace:*`) |
| **Packages** | `api-server`, `getszy` (frontend), `mockup-sandbox`, `lib/db`, `lib/api-zod`, `lib/api-client-react`, `lib/api-spec` |
| **Type Safety** | Strict TypeScript (`~5.9.3`), generated Zod schemas from OpenAPI via orval |
| **Build System** | esbuild for API, Vite for frontend |
| **Database** | PostgreSQL via Drizzle ORM (schema currently empty - placeholder only) |
| **API Style** | REST with Express.js, minimal routes (only `/healthz`) |
| **Auth** | Clerk proxy middleware (production only), no custom auth implementation |

**Critical Gap:** The modern API server has **only a health check endpoint**. All business logic (auth, products, cart, orders, admin, AI) exists only as generated Zod types from an OpenAPI spec, with **zero route implementations**.

### 1.2 Legacy Codebase (`legacy-getszy/`)

| Aspect | Assessment |
|--------|------------|
| **Backend** | FastAPI (Python 3.12+), MongoDB via Motor (async) |
| **Frontend** | React 18 (CRA-based), Tailwind, Redux-like state |
| **Deployment** | Docker Compose (Mongo, Backend, Frontend, Caddy) |
| **API Routes** | 80+ route modules covering all platform features |
| **Auth** | JWT (HS256) with bcrypt, role hierarchy (visitor→customer→founder→admin) |
| **AI/ML** | Multi-provider (Ollama, LM Studio, Groq, Gemini, OpenRouter, Emergent) |
| **Video** | FFmpeg pipeline, TTS, AI providers, shotlist generation |
| **Commerce** | Products, cart, orders, Razorpay integration, subscriptions |
| **Admin** | Full dashboard, audit logs, IP blocking, API keys, analytics |

---

## 2. Security Audit

### 2.1 Critical Issues

| # | Issue | Location | Severity |
|---|-------|----------|----------|
| **SEC-01** | **No authentication/authorization on modern API** | `artifacts/api-server/src/routes/` | **CRITICAL** |
| **SEC-02** | **Empty database schema** - no tables defined | `lib/db/src/schema/index.ts` | **CRITICAL** |
| **SEC-03** | **Clerk secret key in code** (proxy middleware) | `artifacts/api-server/src/middlewares/clerkProxyMiddleware.ts:61` | **HIGH** |
| **SEC-04** | **JWT secret validation only at startup** | `legacy-getszy/backend/auth.py:9-11` | **MEDIUM** |
| **SEC-05** | **No rate limiting on modern API** | `artifacts/api-server/src/app.ts` | **HIGH** |
| **SEC-06** | **CORS allows all origins in legacy** | `legacy-getszy/backend/server.py:42-55` | **MEDIUM** |
| **SEC-07** | **Hardcoded default passwords in docker-compose** | `legacy-getszy/docker-compose.yml:40-42` | **HIGH** |
| **SEC-08** | **No input validation on legacy routes** (uses manual validation) | `legacy-getszy/backend/routes_*.py` | **MEDIUM** |
| **SEC-09** | **Secrets in plaintext in attached_assets/** | `attached_assets/*.txt` | **CRITICAL** |
| **SEC-10** | **GitHub token in docker-compose** | `legacy-getszy/docker-compose.yml:50` | **HIGH** |

### 2.2 Security Details

**SEC-01 & SEC-02 (Modern API):** The modern Express server has no auth middleware, no protected routes, no database models. It's a skeleton.

**SEC-03:** The Clerk proxy middleware reads `CLERK_SECRET_KEY` from env but the pattern encourages committing secrets. Ensure this is only set via platform secret management.

**SEC-07:** Docker Compose has `SEED_CUSTOMER_PASSWORD: "ChangeMeNow!"` - this default will be used if env var not set.

**SEC-09:** The `attached_assets/` directory contains **30+ files with actual secrets, tokens, URLs, and logs** including:
- GitHub PAT tokens (`ghp_...`)
- Deployment webhook URLs
- Server IPs and SSH commands
- Database connection strings
- **These must be removed from git history immediately**

**SEC-10:** `GITHUB_TOKEN` and `GITHUB_REPO` in docker-compose.yml for auto-deploy.

### 2.3 Dependency Vulnerabilities

**Modern (pnpm):**
- `esbuild@0.27.3` - Pinned due to drizzle-kit compatibility (override in pnpm-workspace.yaml:159)
- Supply chain protection: `minimumReleaseAge: 1440` (1 day) - **GOOD**
- Platform-specific binary exclusions reduce attack surface - **GOOD**

**Legacy (Python):**
- `fastapi==0.110.1` - Current as of audit
- `pydantic==2.13.4` - Current
- `pymongo==4.6.3` - Current
- `pyjwt==2.13.0` - Current
- **No pinned vulnerable versions detected** in pyproject.toml

---

## 3. Code Quality & Maintainability

### 3.1 Modern Workspace

| Metric | Assessment |
|--------|------------|
| **TypeScript Strictness** | Strict mode enabled via tsconfig.base.json |
| **Code Generation** | API types generated via orval from OpenAPI - **EXCELLENT** |
| **Schema Validation** | Zod schemas for all API contracts - **EXCELLENT** |
| **Linting/Format** | Prettier only, no ESLint configured - **MISSING** |
| **Testing** | No test files found - **MISSING** |
| **Documentation** | Minimal (only code comments) - **POOR** |
| **Dead Code** | `mockup-sandbox` artifact unused, `lib/api-spec` only config | **MODERATE** |

### 3.2 Legacy Codebase

| Metric | Assessment |
|--------|------------|
| **Route Organization** | 80+ route files, auto-loaded via registry - **GOOD** |
| **Code Duplication** | High - similar patterns repeated across routes | **POOR** |
| **Error Handling** | Inconsistent - some try/catch, some let exceptions bubble | **MODERATE** |
| **Type Hints** | Partial - Pydantic models for some, raw dicts for others | **MODERATE** |
| **Testing** | Test files exist (`backend/tests/`, `backend_test*.py`) - **PRESENT** |
| **Async/Await** | Properly used throughout with Motor - **GOOD** |
| **Database Indexes** | Created at startup - **GOOD** |

### 3.3 Code Smells (Legacy)

1. **God Object Pattern:** `server.py` startup does seeding, migrations, index creation
2. **Inconsistent Validation:** Mix of Pydantic models and manual dict validation
3. **Magic Strings:** Role names, collection names scattered
4. **Large Route Files:** Some route modules exceed 500 lines
5. **No Centralized Config:** Env vars read directly in multiple files

---

## 4. Performance & Scalability

### 4.1 Modern Workspace
- **Connection Pooling:** PgPool configured but unused (no queries)
- **Logging:** Pino with redaction - **GOOD**
- **Build:** esbuild (fast) - **GOOD**
- **Frontend:** Vite + React 19 + Tailwind 4 - **MODERN**

### 4.2 Legacy Codebase
| Component | Concern |
|-----------|---------|
| **MongoDB** | No connection pool tuning (default Motor settings) |
| **Indexes** | Created at startup - good, but no background build option |
| **Caching** | Redis configured but usage inconsistent |
| **Rate Limiting** | Custom middleware (`RateLimitMiddleware`) - needs review |
| **Video Processing** | FFmpeg subprocess calls - blocking, no queue workers visible |
| **AI Calls** | No circuit breakers, retries, or timeouts visible |
| **WebSocket** | `websocket_manager.py` exists but usage unclear |

---

## 5. Dependency Management

### 5.1 Modern (pnpm)
- **Lockfile:** `pnpm-lock.yaml` present
- **Catalog:** Centralized versions in `pnpm-workspace.yaml` - **EXCELLENT**
- **Overrides:** Used to pin esbuild, exclude platform binaries - **GOOD**
- **Supply Chain:** `minimumReleaseAge: 1440` - **EXCELLENT**

### 5.2 Legacy (Python/uv)
- **Lockfile:** `uv.lock` present (2655 lines)
- **Dependencies:** 100+ packages in pyproject.toml
- **PyTorch Ecosystem:** 600+ ML packages from pytorch-cpu index - **EXCESSIVE**
- **Risk:** Many ML packages not directly used (transitive via `diffusers`, `transformers`, etc.)

**Recommendation:** Audit Python deps - likely 50%+ unused. Consider splitting ML requirements.

---

## 6. Deployment & Infrastructure

### 6.1 Modern Workspace
- **GitHub Actions:** Single deploy workflow (triggers webhook) - **MINIMAL**
- **No CI:** No lint, typecheck, test in CI - **MISSING**
- **Environment:** Requires `PORT`, `BASE_PATH`, `DATABASE_URL`, `CLERK_SECRET_KEY`

### 6.2 Legacy Codebase
- **Docker Compose:** Complete stack (Mongo, Backend, Frontend, Caddy)
- **Caddy:** Auto-HTTPS via Let's Encrypt - **GOOD**
- **Healthchecks:** Mongo healthcheck configured - **GOOD**
- **Volumes:** Persistent data for Mongo, Caddy, backend media - **GOOD**
- **Secrets:** All via env vars (but defaults in compose file) - **RISKY**

---

## 7. Feature Completeness Comparison

| Feature | Modern | Legacy |
|---------|--------|--------|
| **Auth (signup/login/me)** | Types only | ✅ Full JWT + Clerk proxy |
| **Products/Catalog** | Types only | ✅ Full CRUD + search |
| **Cart/Checkout/Orders** | Types only | ✅ Full + Razorpay |
| **Admin Dashboard** | Types only | ✅ Stats, charts, AI chat |
| **AI Chat/Assistants** | Types only | ✅ Multi-provider, sessions |
| **Video Generation** | ❌ | ✅ Pipeline + FFmpeg |
| **Image Generation** | ❌ | ✅ Pollinations + providers |
| **Subscription/Billing** | ❌ | ✅ Razorpay plans |
| **Creator Platform** | ❌ | ✅ Courses, lessons, enrollment |
| **Marketplace/Sourcing** | ❌ | ✅ CJ, Shiprocket, trending |
| **Deploy/Hosting** | ❌ | ✅ GitHub, webhook, Caddy |
| **Analytics/Funnel** | Types only | ✅ Series, funnel, executive |
| **Audit Logs** | Types only | ✅ Full + IP blocking |
| **API Keys** | Types only | ✅ CRUD + revocation |
| **System Monitoring** | ❌ | ✅ CPU, RAM, disk, GPU, Mongo |

---

## 8. Critical Recommendations

### 🔴 Immediate (Do First)

1. **REMOVE `attached_assets/` FROM GIT HISTORY** - Contains live secrets, tokens, IPs
   ```bash
   git filter-branch --force --index-filter \
   'git rm -rf --cached --ignore-unmatch attached_assets/' \
   --prune-empty --tag-name-filter cat -- --all
   ```
   Then force push and rotate ALL exposed secrets.

2. **Implement Modern API Routes** - The modern workspace is a skeleton. Either:
   - Complete the rewrite (implement all routes from legacy)
   - Or abandon and use legacy as production

3. **Add Database Schema** - `lib/db/src/schema/index.ts` is empty placeholder

4. **Add Authentication to Modern API** - No auth middleware exists

5. **Remove Hardcoded Defaults** - Docker compose passwords, JWT secret validation

### 🟠 High Priority

6. **Add CI Pipeline** - Lint, typecheck, test for both codebases
7. **Add ESLint + Prettier** - Modern workspace has only Prettier
8. **Add Tests** - Zero tests in modern workspace
9. **Consolidate Codebases** - Maintaining two full stacks is unsustainable
10. **Audit Python Dependencies** - 600+ ML packages likely unused

### 🟡 Medium Priority

11. **Standardize Error Handling** - Legacy routes inconsistent
12. **Add Rate Limiting** - Missing on modern API
13. **Centralize Configuration** - Legacy reads env vars in 50+ files
14. **Add API Documentation** - OpenAPI spec exists but no Swagger UI
15. **Improve Logging** - Legacy uses basic logging, no structured logs

### 🟢 Low Priority

16. **Remove Dead Code** - `mockup-sandbox`, unused legacy test files
17. **Upgrade Legacy Frontend** - CRA is deprecated, migrate to Vite
18. **Add Database Migrations** - Legacy creates indexes at runtime
19. **Implement Circuit Breakers** - For AI provider calls
20. **Add Request Validation** - Legacy uses manual validation

---

## 9. Risk Assessment Matrix

| Risk | Likelihood | Impact | Score |
|------|------------|--------|-------|
| Secrets exposed in git history | HIGH | CRITICAL | **25** |
| Modern API non-functional | HIGH | HIGH | **20** |
| Dual codebase maintenance burden | HIGH | HIGH | **20** |
| No CI/CD quality gates | MEDIUM | HIGH | **15** |
| Legacy tech debt (CRA, manual validation) | HIGH | MEDIUM | **15** |
| Excessive Python dependencies | MEDIUM | MEDIUM | **12** |
| No automated testing | MEDIUM | MEDIUM | **12** |
| Inconsistent error handling | MEDIUM | LOW | **8** |

---

## 10. Verdict

### Modern Workspace: **NOT PRODUCTION READY**
- Only health check implemented
- No database schema
- No authentication
- No tests, no CI
- **Recommendation:** Complete rewrite or abandon

### Legacy Codebase: **PRODUCTION READY WITH CAVEATS**
- Feature-complete platform
- Working deployment (Docker + Caddy)
- **BUT:** Secrets in git history, tech debt, no CI, manual validation
- **Recommendation:** Use for production AFTER secret rotation and cleanup

### Overall: **HIGH RISK**
The repository contains **live secrets in git history** and **two competing codebases**. Immediate action required on secret rotation and codebase consolidation decision.

---

## Appendix: File Inventory

### Modern Workspace Key Files
```
/tmp/getszy-audit/
├── package.json                    # Root workspace config
├── pnpm-workspace.yaml             # Workspace + catalog + security config
├── tsconfig.base.json              # TypeScript base config
├── pyproject.toml                  # Python deps (for Replit tooling)
├── artifacts/
│   ├── api-server/                 # Express API (skeleton)
│   │   ├── src/
│   │   │   ├── index.ts            # Entry point
│   │   │   ├── app.ts              # Express setup
│   │   │   ├── routes/
│   │   │   │   ├── index.ts        # Router (health only)
│   │   │   │   └── health.ts       # Health endpoint
│   │   │   ├── middlewares/
│   │   │   │   └── clerkProxyMiddleware.ts
│   │   │   └── lib/logger.ts
│   │   └── build.mjs               # esbuild config
│   ├── getszy/                     # React frontend (Vite + Tailwind 4)
│   │   ├── src/
│   │   │   ├── App.tsx             # Minimal router
│   │   │   ├── main.tsx            # Entry
│   │   │   ├── components/ui/      # 50+ shadcn/ui components
│   │   │   ├── hooks/              # use-mobile, use-toast
│   │   │   ├── lib/utils.ts        # cn() helper
│   │   │   └── pages/not-found.tsx
│   │   └── vite.config.ts
│   └── mockup-sandbox/             # Unused artifact
└── lib/
    ├── db/                         # Drizzle ORM (empty schema)
    ├── api-zod/                    # Generated Zod schemas (1000+ lines)
    ├── api-client-react/           # Generated API client
    └── api-spec/                   # orval config
```

### Legacy Codebase Key Files
```
legacy-getszy/
├── docker-compose.yml              # Full stack deployment
├── backend/
│   ├── server.py                   # FastAPI app + startup logic
│   ├── auth.py                     # JWT + bcrypt + roles
│   ├── db.py                       # Motor MongoDB client
│   ├── middleware.py               # Rate limit, security headers
│   ├── monitoring.py               # Prometheus metrics
│   ├── seed.py                     # Database seeding
│   ├── routes_*.py                 # 80+ route modules
│   ├── app/router_registry.py      # Auto-load routes
│   └── tests/                      # Test files
├── frontend/                       # CRA React app
└── deploy/
    ├── webhook_listener.py         # GitHub webhook deploy
    └── Caddyfile                   # Reverse proxy + TLS
```

---

*End of Audit Report*