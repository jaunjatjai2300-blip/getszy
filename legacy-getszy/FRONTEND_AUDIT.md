# Getszy — Frontend Audit Report

> Scope: production-readiness of the React (CRA/craco) frontend in `legacy-getszy/frontend`.

## Verdict
**Production-ready with two real fixes applied.** The app is env-configurable, uses a
central axios client with auth interception, and ships no hardcoded secrets.

## What was checked
| Area | Finding | Status |
|------|---------|--------|
| Build | `craco build` script present; `package.json` `proxy` (localhost:8000) is **dev-only** and correctly ignored by production builds | ✅ |
| API base URL | Central `src/lib/api.js` builds `API_BASE` from `REACT_APP_BACKEND_URL` (`<url>/api`, else same-origin `/api`) | ✅ |
| Auth | `gs_token` from localStorage; axios interceptor adds `Bearer`; `401` clears token + redirects to `/login` | ✅ |
| Secrets | Sentry DSN via `REACT_APP_SENTRY_DSN` (env). No hardcoded keys found in `src` | ✅ |
| Security headers | Set by backend middleware (HSTS, X-Frame-Options, etc.) for API responses | ➖ (see rec) |

## Fixes applied
1. `src/utils/aiBuilder.js` used a **different** env var (`REACT_APP_API_URL`) and fell
   back to `http://localhost:8001`. In production (where only `REACT_APP_BACKEND_URL`
   is configured) the AI chat would have silently called `localhost:8001`.
   **Changed** to use `REACT_APP_BACKEND_URL` with a same-origin (`''`) fallback,
   matching every other component.
2. `aiBuilder.js` also called a **non-existent** endpoint (`/admin/chat/completions`)
   and parsed an OpenAI-style SSE stream (`choices[0].delta.content`). The real
   customer endpoint is `POST /api/ai-tools/chat/completions` and it returns **plain
   JSON** (`choices[0].message.content`) — the old code therefore returned empty
   output. **Fixed** the path and switched to `res.json()` parsing, which now matches
   `AITools.jsx` (the working customer AI page).

## CI automation added
`.github/workflows/production-hardening.yml` now has a `frontend-build` job:
Node 20 → `npm ci` → `craco build` (with safe placeholder `REACT_APP_*` vars) →
uploads `build/` as an artifact. The frontend now fails CI if it does not compile.

## Recommendations (not blocking)
1. ~~Verify the AI-builder endpoint.~~ **Resolved** (see Fix #2 above).
2. **Add CSP to served HTML.** ✅ Reference config added at `deploy/caddy/Caddyfile`
   (CSP + HSTS + nosniff). Backend security headers cover `/api`, but the
   static `index.html` is served by Caddy — add a `Content-Security-Policy` there.
3. **Add type-check/lint CI** (e.g. `tsc --noEmit` / ESLint) to catch regressions
   earlier than a full build.
