---
name: Getszy credit system refund-on-failure pattern
description: Every route that deducts credits before doing AI generation work must refund on failure, including background-task routes — this was missing across most routes and caused silent credit loss on failed generations.
---

Getszy's credit system (`legacy-getszy/backend/credits.py`) uses a deduct-then-work pattern: `deduct(user_id, action)` is called before the actual AI generation, and the generation happens after. If the generation throws/fails, the user has already paid but got nothing.

**Why:** An audit found `refund()` was only wired into one of ~11 deduct call sites (`routes_video_factory.py`'s chain endpoint). Everywhere else — `routes_media.py` (image/logo/tryon), `routes_creator.py` (script/repurpose), `routes_builder.py` (website/refine), `routes_video.py` (faceless video) — deducted credits with no refund path, including two files that had `refund` imported but never called (dead import left from earlier partial work). Confirmed via live e2e test: a script-generation call failed with 500 (LLM provider misconfigured) yet silently kept the deducted credit until the fix.

**How to apply:** When adding or reviewing any credit-consuming action:
1. Wrap the post-deduction work in `try/except Exception` and call `await refund(user_id, action, reason='generation_failed')` before re-raising.
2. If the actual work happens in a `BackgroundTasks` job (e.g. `video/pipeline.py::run_job`, `video_factory/renderer.py::generate_all_assets`), the route's try/except won't catch it — the refund must happen inside the background job's own except block / error-return paths instead. Pass `user_id` (and qty, if the action supports batching) into the background job for this purpose.
3. For batch/multi-unit actions (e.g. `repurpose_format` across N formats), refund only the failed-unit count, not the whole batch.
