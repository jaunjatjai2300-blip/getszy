"""Bridge between an art direction's asset policy and the media sourcing layer.

Keeps two concerns apart:
  * design_intent/design_registry decide WHAT imagery a direction wants
    (photography required/preferred/optional, orientation, minimum width);
  * media_sourcing decides WHETHER a specific image may be used at all.

This module asks for the right pictures and hands back only assets that are
actually publishable. It never raises: media is an enhancement, and a provider
outage must never stop a customer's website being generated.

Nothing here publishes anything. Until a secure delivery layer assigns a
`public_url`, `MediaAsset.publishable()` is False and the builder falls back to
the direction's designed non-photographic composition -- which is why sourcing
can be enabled safely before public delivery exists.
"""
from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger(__name__)

# Sourcing is OFF by default: it makes outbound calls, and no delivery layer
# exists yet to serve what it fetches. Turning it on changes nothing a customer
# sees until delivery is built -- it only warms the local store and proves the
# pipeline end to end.
ENABLED = os.environ.get("MEDIA_SOURCING_ENABLED", "false").strip().lower() in ("1", "true", "yes")
# Hard ceiling per build so a slow provider cannot stretch a customer's build.
BUDGET_SECONDS = float(os.environ.get("MEDIA_SOURCING_BUDGET", 12))
MAX_IMAGES = int(os.environ.get("MEDIA_SOURCING_MAX", 3))


async def gather_assets(prompt: str, brief: dict | None, vertical: str | None,
                        recipe) -> list:
    """Best-effort list of publishable MediaAssets for this page.

    Returns [] whenever sourcing is disabled, unsupported, out of budget, or
    unable to find anything licence-clean. The caller must treat [] as normal.
    """
    if not ENABLED or recipe is None:
        return []
    policy = (recipe.assets or {}).get("photography", "optional")
    if policy == "optional":
        return []                      # this direction does not want photography

    try:
        import design_intent as di
        import media_sourcing as ms
    except Exception:
        return []

    queries = di.image_queries(prompt, brief, vertical, limit=MAX_IMAGES)
    orientation = (recipe.assets or {}).get("orientation", "landscape")
    min_width = int((recipe.assets or {}).get("min_width", 1200))

    async def one(q):
        try:
            return await ms.source_image(q, orientation=orientation, min_width=min_width)
        except Exception as e:
            logger.info("media sourcing failed for %r: %s", q, type(e).__name__)
            return None

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*(one(q) for q in queries), return_exceptions=True),
            timeout=BUDGET_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.info("media sourcing exceeded its %ss budget; continuing without photos",
                    BUDGET_SECONDS)
        return []
    except Exception:
        return []

    assets = []
    for r in results:
        if isinstance(r, Exception) or r is None:
            continue
        # Bytes on disk are not permission to publish.
        if getattr(r, "publishable", lambda: False)():
            assets.append(r)
    return assets


__all__ = ["gather_assets", "ENABLED"]
