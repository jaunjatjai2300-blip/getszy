---
name: Bash sandbox kills background processes between tool calls
description: mongod/uvicorn (or any daemon) started with &, setsid, disown, or --fork in one bash tool call does not survive into the next bash tool call in this environment.
---

Background processes (even daemonized ones using `--fork`, or shell-backgrounded with `setsid ... & disown`) reliably get reaped once a bash tool call returns. A process that shows up in `ps aux` right after starting will be gone by the next tool call.

**Why:** Observed while testing a local FastAPI+MongoDB backend — `mongod --fork` and `uvicorn &` both showed as running processes immediately, but a follow-up bash tool call found them dead (connection refused / no matching `ps` entry), even though nothing manually killed them.

**How to apply:** For any test that needs a long-running local server/daemon (dev DB, API server, etc.), start the daemon AND run every dependent step (health checks, curl requests, assertions, teardown) inside the *same* bash tool call, chained with `&&`/`;`/backgrounding + `sleep`. Do not assume a background process started in one call will still be alive in a later call — restart it fresh each time you need it.
