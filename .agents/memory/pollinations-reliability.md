---
name: Pollinations free-tier reliability
description: Handling intermittent failures from the free Pollinations.ai image generation API
---

Pollinations.ai's free image endpoint (used for image/logo/try-on tools and per-scene video visuals) occasionally times out or returns error placeholders under load — it has no SLA.

**Why:** this is the only image provider available without a paid key (fal.ai deferred), so reliability work here has outsized impact on perceived app quality.

**How to apply:**
- Wrap fetches in a retry loop (2 attempts) with a different `seed` on each attempt, plus a short sleep (~1.5s) between tries — a single retry fixes most transient failures.
- Treat responses under ~1-2KB as failed placeholders, not real images, even on HTTP 200.
- Keep a final fallback (e.g. Pexels stock or solid-color placeholder) so a tool never hard-fails the user-facing request even if both attempts fail.
- Apply this pattern everywhere Pollinations is called directly: `video/visuals.py` (scene images) and `routes_media.py`'s `_prefetch_and_cache` (image/logo/try-on tools).
