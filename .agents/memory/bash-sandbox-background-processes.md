---
name: Bash sandbox kills background processes between tool calls
description: mongod/uvicorn (or any daemon) started with &, setsid, disown, or --fork in one bash tool call does not survive into the next bash tool call in this environment.
---

Background processes (even daemonized ones using `--fork`, or shell-backgrounded with `setsid ... & disown`) reliably get reaped once a bash tool call returns. A process that shows up in `ps aux` right after starting will be gone by the next tool call.

**Why:** Observed while testing a local FastAPI+MongoDB backend — `mongod --fork` and `uvicorn &` both showed as running processes immediately, but a follow-up bash tool call found them dead (connection refused / no matching `ps` entry), even though nothing manually killed them.

**How to apply:** For any test that needs a long-running local server/daemon (dev DB, API server, etc.), start the daemon AND run every dependent step (health checks, curl requests, assertions, teardown) inside the *same* bash tool call, chained with `&&`/`;`/backgrounding + `sleep`. Do not assume a background process started in one call will still be alive in a later call — restart it fresh each time you need it.

**Getszy specifics learned in a later session:** `legacy-getszy/backend/.env` sets `MONGO_URL=mongodb://127.0.0.1:27018` (not the Mongo default 27017) — always start `mongod --port 27018` for this app or the FastAPI startup hangs indefinitely on `db.users.count_documents(...)` inside `seed_if_empty()` with no error until the connection finally times out (~30s) and app startup fails silently. Poll `/tmp/uvicorn.log` for the literal string `Application startup complete` (with a `kill -0 $PID` bail-out check) rather than a fixed `sleep`, since the failure mode is a long hang, not a fast crash. Real routes are `/api/auth/signup` (not `/register`) and `/api/billing/pricing` (not `/plans`) — grep each router's `APIRouter(prefix=...)` before assuming REST-conventional paths. Also, this sandbox occasionally kills bash tool calls outright (exit 137/143 with zero captured output, even from `echo`) under repeated heavy mongod/uvicorn churn — if that happens, wait for a plain `echo` sanity-check call to succeed before retrying the full boot sequence.
