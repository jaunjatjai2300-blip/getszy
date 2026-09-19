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

    queries = di.image_queries(prompt, brief, vertical, limit=MAX_IMAGES,
                               recipe_id=recipe.id)
    orientation = (recipe.assets or {}).get("orientation", "landscape")
    # Openly-licensed catalogues routinely top out near 1024px on the direct
    # URL. Demanding the recipe's aspirational min_width would reject almost
    # everything and silently yield no photography at all.
    min_width = int(os.environ.get("MEDIA_MIN_WIDTH", 900))

    async def collect():
        """Try queries IN ORDER (flavoured first, plain fallback after) and stop
        as soon as we have enough distinct images."""
        assets, seen = [], set()
        for q in queries:
            if len(assets) >= MAX_IMAGES:
                break
            try:
                asset = await ms.source_image(q, orientation=orientation,
                                              min_width=min_width)
            except Exception as e:
                logger.info("media sourcing failed for %r: %s", q, type(e).__name__)
                continue
            if asset is None:
                continue
            # never show the same photograph twice on one page
            if asset.content_sha256 and asset.content_sha256 in seen:
                continue
            seen.add(asset.content_sha256)
            if getattr(asset, "publishable", lambda: False)():
                assets.append(asset)
        return assets

    try:
        return await asyncio.wait_for(collect(), timeout=BUDGET_SECONDS)
    except asyncio.TimeoutError:
        logger.info("media sourcing exceeded its %ss budget; continuing without photos",
                    BUDGET_SECONDS)
        return []
    except Exception:
        return []


__all__ = ["gather_assets", "ENABLED"]
