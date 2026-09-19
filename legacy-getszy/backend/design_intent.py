"""Infer the VISUAL direction a customer is asking for, deterministically.

The builder previously inferred only the business VERTICAL (what the site is
about) and then rendered every vertical through one visual system. This module
adds the missing axis: the ART DIRECTION (what the site should look like).

Two independent signals decide the recipe:

  1. EXPLICIT STYLE LANGUAGE in the prompt -- "cinematic", "glassmorphism",
     "futuristic", "editorial", "minimal". When a customer names a look, that
     look wins; it is the least ambiguous evidence available.
  2. VERTICAL AFFINITY -- a gym leans cinematic, a salon leans glass, a plumber
     leans professional. Used only when style language is absent or tied.

Deterministic and dependency-free on purpose: the same prompt always yields the
same direction, which keeps builds reproducible, makes the choice reviewable in
the attempt ledger, and costs no model call or network round-trip. The registry
it selects from is pre-vetted, so an inference can never introduce unlicensed or
unreviewed design code -- the worst case is a suboptimal but safe direction.

`infer_direction` returns EVIDENCE, not just an id, so the reason a page looks
the way it does is auditable rather than a black box.
"""
from __future__ import annotations

import re

import design_registry as dr

# Weights: naming a style is far stronger evidence than a vertical guess.
_EXPLICIT_WEIGHT = 10
_AFFINITY_WEIGHT = 3
# A style word the customer used verbatim, e.g. "glassmorphism", is decisive.
_STRONG_TERMS = {
    "glassmorphism": "glassmorphism", "glass morphism": "glassmorphism",
    "frosted glass": "glassmorphism",
    "cinematic": "cinematic_luxury", "editorial": "editorial_fashion",
    "futuristic": "futuristic_saas", "brutalist": "editorial_fashion",
    "magazine": "editorial_fashion", "neon": "futuristic_saas",
}

# Asset direction: when a customer asks for illustration we must NOT force
# photography, and vice versa. Default follows the recipe's own policy.
_ILLUSTRATION_TERMS = ("illustration", "illustrated", "cartoon", "hand-drawn", "doodle",
                       "vector art", "mascot", "comic", "anime")
_PHOTO_TERMS = ("photo", "photography", "photographic", "real image", "real photo",
                "lifestyle image", "portraits")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


def infer_direction(prompt: str, brief: dict | None = None, vertical: str | None = None) -> dict:
    """Choose a vetted design recipe. Returns evidence, never just an id.

    The returned dict is safe to store in the attempt ledger and to show a
    reviewer: it records what matched and why, so an unexpected look can be
    explained instead of guessed at.
    """
    brief = brief or {}
    text = _norm(f"{prompt} {brief.get('style') or ''} {brief.get('visual_direction') or ''}")

    scores: dict = {r.id: 0 for r in dr.RECIPES}
    matched: dict = {r.id: [] for r in dr.RECIPES}

    # 1) explicit, verbatim style language
    for term, rid in _STRONG_TERMS.items():
        if term in text:
            scores[rid] += _EXPLICIT_WEIGHT
            matched[rid].append(term)

    # 2) recipe signal vocabulary
    for r in dr.RECIPES:
        for sig in r.signals:
            if sig in text:
                scores[r.id] += _EXPLICIT_WEIGHT if len(sig) > 6 else 4
                matched[r.id].append(sig)

    # 3) vertical affinity (weak tiebreaker only)
    if vertical:
        for r in dr.RECIPES:
            if vertical in r.affinity:
                scores[r.id] += _AFFINITY_WEIGHT
                matched[r.id].append(f"vertical:{vertical}")

    # An explicit customer override always wins outright.
    forced = (brief.get("design_recipe") or "").strip()
    if forced and forced in dr.all_recipe_ids():
        return {
            "recipe_id": forced, "confidence": "explicit",
            "matched": ["brief.design_recipe"], "scores": scores,
            "asset_policy": _asset_policy(text, dr.get_recipe(forced)),
            "reason": "Customer explicitly requested this design recipe.",
        }

    best_id = max(scores, key=lambda k: (scores[k], k == dr.DEFAULT_RECIPE_ID))
    best = scores[best_id]
    if best == 0:
        # No evidence at all -> the safe, trust-first default. Never a random look.
        best_id = dr.DEFAULT_RECIPE_ID
        conf = "default"
        reason = "No visual direction detected; using the safe professional default."
    else:
        runner = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
        conf = "high" if best >= _EXPLICIT_WEIGHT and best > runner else "medium"
        reason = f"Matched {sorted(set(matched[best_id]))[:6]}"

    recipe = dr.get_recipe(best_id)
    return {
        "recipe_id": best_id, "confidence": conf,
        "matched": sorted(set(matched[best_id])), "scores": scores,
        "asset_policy": _asset_policy(text, recipe),
        "reason": reason,
    }


def _asset_policy(text: str, recipe: "dr.DesignRecipe") -> str:
    """Photography by default for photo-led recipes; illustration ONLY when the
    customer actually asks for it. This is the rule that stops cartoon filler
    appearing on a business that wanted real imagery."""
    if any(t in text for t in _ILLUSTRATION_TERMS):
        return "illustration"
    if any(t in text for t in _PHOTO_TERMS):
        return "photo"
    return recipe.asset_policy


# Each art direction wants a different KIND of photograph, not the same stock
# image recoloured. These modifiers are appended to the subject query so a
# cinematic gym asks for dramatic, high-contrast frames while a local trade
# business asks for authentic on-site work.
_DIRECTION_LOOK = {
    "cinematic_luxury": ("dramatic lighting", "high contrast", "moody"),
    "glassmorphism": ("bright airy", "clean minimal", "soft light"),
    "futuristic_saas": ("technology", "modern workspace", "abstract tech"),
    "editorial_fashion": ("editorial fashion", "studio portrait", "minimal styling"),
    "professional_local": ("at work", "local business", "candid"),
}

_SUBJECTS = {
    "fitness": ("gym strength training", "athlete workout", "fitness coach"),
    "salon": ("hair salon interior", "beauty treatment", "salon styling"),
    "restaurant": ("restaurant food plating", "chef cooking", "restaurant interior"),
    "health": ("wellness therapy", "clinic care", "yoga wellness"),
    "ecommerce": ("retail boutique interior", "product photography studio", "shopping display"),
    "saas": ("server data center", "computer circuit technology", "developer coding screen"),
    "consultant": ("business meeting", "consulting office", "team strategy"),
    # "technician" alone also describes nail/lab technicians, so trade queries
    # name the trade explicitly.
    "service": ("plumbing repair", "handyman tools", "electrician wiring"),
    "education": ("students learning", "classroom teaching", "study workspace"),
    "portfolio": ("creative studio", "designer working", "artist workspace"),
}


# Subjects a direction names better than the vertical does. Only directions
# whose whole identity IS a subject belong here; everything else defers to the
# business vertical.
_DIRECTION_SUBJECTS = {
    "editorial_fashion": ("fashion model portrait", "clothing boutique",
                          "fashion editorial studio"),
}


def image_queries(prompt: str, brief: dict | None = None, vertical: str | None = None,
                  limit: int = 3, recipe_id: str | None = None) -> list:
    """Ordered search attempts: art-direction flavour first, plain subject after.

    A generic query ("business", "office") returns generic stock and the page
    looks like every other template, so the direction's visual language is tried
    FIRST. But a heavily-qualified query ("gym strength training dramatic
    lighting") frequently returns nothing at all on openly-licensed catalogues,
    and silently ending up with no photography is a worse outcome than a slightly
    less stylised photograph. So every flavoured query is followed by its plain
    subject as a fallback, and callers try the list in order.
    """
    brief = brief or {}
    subjects = list(_DIRECTION_SUBJECTS.get(recipe_id or "", ())
                    or _SUBJECTS.get(vertical or "", ("professional workspace",)))
    looks = _DIRECTION_LOOK.get(recipe_id or "", ())
    city = str(brief.get("city") or brief.get("location") or "").strip()

    chain = []
    for i, subject in enumerate(subjects[:max(1, limit)]):
        if looks:
            chain.append(f"{subject} {looks[i % len(looks)]}")
        chain.append(subject)
    if city:
        chain.append(f"{subjects[0]} {city}")
    # de-duplicate, preserving order
    seen, out = set(), []
    for q in chain:
        if q not in seen:
            seen.add(q)
            out.append(q)
    return out


__all__ = ["infer_direction", "image_queries"]
