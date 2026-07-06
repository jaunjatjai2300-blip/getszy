---
name: Legacy-getszy live-testing setup
description: How legacy-getszy (Python/FastAPI/MongoDB) got wired up for live boot/testing in the sandbox, and the pitfall that blocked it
---

`legacy-getszy/` is not part of the pnpm-workspace artifact system (no `createArtifact` type fits a raw FastAPI+CRA+Mongo stack), so it can't get a proxy path via `artifact.toml`. It was made live-testable instead via three plain `configureWorkflow` processes: `Legacy Mongo` (`mongod --dbpath /tmp/mongo-data --port 27017`), `Legacy Backend` (`uvicorn server:app --port 8000`), `Legacy Frontend` (`PORT=3000 yarn start`, CRA `"proxy": "http://localhost:8000"` in package.json + `REACT_APP_BACKEND_URL=` empty in frontend `.env` so `axios` calls are relative `/api/...` and ride CRA's dev-server proxy — avoids needing the backend on the shared proxy at all).

**Why it hung at first:** backend appeared to hang forever at "Waiting for application startup" — root cause was `backend/.env` `MONGO_URL` pointing at port `27018` while `mongod` was actually started on `27017` (stale/mismatched value, not a code bug). Always diff the `.env` Mongo port against whatever port you actually start `mongod` on before assuming a boot hang is a code problem.

**Gotcha:** `configureWorkflow` for a brand-new workflow name can silently rewrite the `Project` run-button's parallel task list to only the newly-added workflows, dropping pre-existing artifact workflows (`api-server`, `getszy`, `mockup-sandbox`) from `Project`. Direct edits to `.replit` are blocked by the sandbox, so this can't be patched by hand — the previously-running workflows keep running in the current session, but re-verify `listWorkflows()` includes them after adding new workflows, since a future full restart of "Project" may not relaunch them.

**How to apply:** since `legacy-getszy` has no browser-preview artifact, use `restartWorkflow()`'s returned `screenshotUrl` (download + read as an image) as the way to visually verify the frontend — the `screenshot` tool's `app_preview` type only works for registered artifacts, and `external_url` can't render a raw `.jpg` URL from Firecrawl.
