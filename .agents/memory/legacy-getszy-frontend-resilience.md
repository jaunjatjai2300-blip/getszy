---
name: Legacy-getszy frontend resilience gaps
description: Baseline frontend robustness issues found and fixed in the Getszy React app (error boundary, 404, data-load error handling)
---

The React app (`legacy-getszy/frontend`) originally had no global crash/error protections:
- No `ErrorBoundary` — any component throw crashed the whole app to a blank screen.
- No catch-all `*` route — unknown URLs showed a blank layout with no content.
- Several `useEffect` data-fetch calls (`Home.jsx`, `Shop.jsx`, `admin/Dashboard.jsx`, `MediaStudio.jsx`, `lib/cart.js`) had no `.catch()`, so a failed API call left the page stuck on "Loading…" forever instead of showing an error state.

**Why:** these are silent-failure classes that are easy to miss in normal dev testing (APIs usually succeed locally) but surface immediately in production under real network/API flakiness — especially relevant here since the app leans on free-tier APIs (Pollinations) that are more failure-prone than paid ones.

**How to apply:** when auditing or extending this app's frontend, check that new pages/hooks doing `api.get(...).then(...)` in a `useEffect` always pair it with `.catch()` that sets an error/empty state — don't assume the request succeeds. `ErrorBoundary.jsx` and `NotFound.jsx` now exist in `components/`/`pages/` and are wired into `App.js`; reuse them rather than re-inventing per-page.

**Follow-up sweep (2026-07-06):** the same silent-failure class was still present across the admin panel — many `catch (e) {}` blocks on one-shot loads (Workforce, Deploy, BuildStudio's hub/projects/channels/agents/starters) and on user-triggered delete/cancel actions (Publishing, BuildStudio). Fixed by adding `toast.error(...)` in each catch so failures are visible instead of silent. When adding new admin CRUD panels, always give the catch block a visible error path — this app's pattern is `toast.error("<Action> failed — please retry")` via `sonner`, consistent with the rest of the UI.
