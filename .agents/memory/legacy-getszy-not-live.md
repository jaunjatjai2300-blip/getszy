---
name: Legacy-getszy is not a running artifact
description: legacy-getszy/ is a standalone folder, not wired into the Replit artifact/workflow/proxy system
---

`legacy-getszy/` (Python/FastAPI/MongoDB) is a real, substantial codebase in this workspace, but it is **not** registered as an artifact and has no workflow bound to it. Confirmed by:
- Registered artifacts are only `api-server`, `mockup-sandbox`, and `getszy` (the Node/React storefront) — no `legacy-getszy` entry.
- `ps aux` shows no `uvicorn`/`mongod` process running anywhere in the sandbox.

**Why:** this matters because it means the app cannot be reached via the preview pane, `localhost:80`, or a browser session — attempts to use `runTest()` (Playwright e2e) or curl-based smoke tests against it will fail or hang, not because of a bug but because nothing is serving it.

**How to apply:** when working on `legacy-getszy`, verify changes statically only — `python3 -m py_compile <files>`, `python3 -c "import server"` from `legacy-getszy/backend/`, and `yarn build` from `legacy-getszy/frontend/`. Do not attempt live boot/e2e testing unless the user has explicitly set up a workflow for it first.
