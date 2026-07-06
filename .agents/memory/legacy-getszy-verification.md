---
name: Legacy-getszy backend verification
description: How to verify Python/FastAPI backend changes when live process boot is unreliable in this sandbox
---

Booting mongod/uvicorn directly in this sandbox is unreliable (see also bash-sandbox-background-processes.md) — do not rely on live server hits to validate backend changes.

**How to apply:** after any backend edit, run in one bash call from `legacy-getszy/backend/`:
1. `python3 -m py_compile <changed files>` — catches syntax errors.
2. `python3 -c "import server"` — catches import-time errors (missing imports, bad module-level code).
3. `cd legacy-getszy/frontend && yarn build` — catches any frontend breakage from API/contract changes.

This combination has reliably caught real bugs (e.g. missing `import asyncio`) without needing a live server.
