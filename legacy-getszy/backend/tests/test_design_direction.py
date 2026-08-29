"""Art-direction system: the builder is no longer one template in new colours.

These tests pin the behaviour that matters commercially: a cinematic gym, a
glass salon, a futuristic SaaS, an editorial boutique and a local trade business
must receive GENUINELY DIFFERENT visual systems, every one of which still clears
the unmodified premium gate -- and the gate must remain just as hostile to basic
and CDN-dependent output as it was before.
"""
import re

import pytest

import design_intent as di
import design_registry as dr
from builder_agents import _premium_template
from builder_quality import evaluate_landing_page_quality

# The five directions this system exists to serve.
CASES = [
    ("cinematic luxury fitness club, dramatic dark visuals",
     {"brand_name": "Iron Vault", "vertical": "fitness"}, "cinematic_luxury"),
    ("glassmorphism beauty salon, soft frosted translucent look",
     {"brand_name": "Luxe Glow"}, "glassmorphism"),
    ("futuristic AI SaaS analytics platform",
     {"brand_name": "Nexus AI", "vertical": "saas"}, "futuristic_saas"),
    ("premium editorial fashion boutique, magazine minimal",
     {"brand_name": "Maison Ora", "vertical": "ecommerce"}, "editorial_fashion"),
    ("trusted local plumber, book an appointment near me",
     {"brand_name": "RapidFix", "vertical": "service"}, "professional_local"),
]


# ── intent inference ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("prompt,brief,expected", CASES)
def test_visual_direction_is_inferred_from_the_customer_words(prompt, brief, expected):
    d = di.infer_direction(prompt, brief, brief.get("vertical"))
    assert d["recipe_id"] == expected, d
    assert d["confidence"] in ("high", "medium", "explicit")
    assert d["matched"], "a selection must carry the evidence that produced it"


def test_no_visual_signal_falls_back_to_the_safe_default_never_random():
    d = di.infer_direction("a website for my business", {}, None)
    assert d["recipe_id"] == dr.DEFAULT_RECIPE_ID
    assert d["confidence"] == "default"


def test_customer_can_pin_a_recipe_explicitly():
    d = di.infer_direction("anything at all", {"design_recipe": "editorial_fashion"}, "saas")
    assert d["recipe_id"] == "editorial_fashion" and d["confidence"] == "explicit"


def test_illustration_only_when_actually_requested():
    """Cartoon/illustrated filler must never appear unless asked for -- real
    businesses expect real photography."""
    assert di.infer_direction("cartoon illustrated mascot site", {}, "saas")["asset_policy"] == "illustration"
    # a photo-led direction stays photographic when nothing is said
    assert di.infer_direction("luxury gym", {}, "fitness")["asset_policy"] == "photo"


# ── the registry itself ──────────────────────────────────────────────────────
def test_every_recipe_is_self_contained_with_no_runtime_dependency():
    for r in dr.RECIPES:
        css = dr.stylesheet(r)
        assert "cdn.tailwindcss.com" not in css
        assert "@import" not in css          # no external stylesheet pull
        assert "url(http" not in css         # no remote asset fetched from CSS
        assert len(css) > 3000, f"{r.id} is too thin to be a real design system"


def test_recipes_are_actually_different_visual_systems():
    sheets = {r.id: dr.stylesheet(r) for r in dr.RECIPES}
    assert len(set(sheets.values())) == len(sheets), "recipes must not collapse to one system"


def test_unknown_recipe_falls_back_safely():
    assert dr.get_recipe("does_not_exist").id == dr.DEFAULT_RECIPE_ID
    assert dr.get_recipe("").id == dr.DEFAULT_RECIPE_ID


# ── rendered output ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("prompt,brief,expected", CASES)
def test_each_direction_renders_a_premium_page_that_passes_the_gate(prompt, brief, expected):
    html = _premium_template(prompt, brief)
    report = evaluate_landing_page_quality(html, brief)
    low = html.lower()
    assert report["status"] == "ready_for_human_review", (expected, report["next_actions"])
    assert "<style" in low and "cdn.tailwindcss.com" not in html   # self-contained
    assert low.count("<h1") == 1
    assert len(re.findall(r"<section", low)) >= 6                  # not a 3-4 section stub
    assert brief["brand_name"] in html                            # customer content survives
    assert "trusted by" not in low and "5-star" not in low        # no fabricated proof


def test_the_five_directions_produce_five_different_pages():
    pages = {exp: _premium_template(p, b) for p, b, exp in CASES}
    assert len(set(pages.values())) == len(CASES)
    # and the difference is in the DESIGN, not merely the copy: each recipe's
    # own palette token must appear in its page.
    for rid, html in pages.items():
        assert dr.get_recipe(rid).palette["p"] in html, rid


# ── the gate must NOT have been weakened to achieve the above ────────────────
def test_gate_still_rejects_basic_and_cdn_dependent_output():
    """Regression guard for the whole exercise: art-direction awareness must not
    have opened a door for flat or Tailwind-CDN-only pages."""
    from tests.test_builder_premium_quality import BASIC_PAGE, PREMIUM_TAILWIND, BRIEF
    assert evaluate_landing_page_quality(BASIC_PAGE, BRIEF)["status"] == "needs_work"
    assert evaluate_landing_page_quality(PREMIUM_TAILWIND, {"primary_cta": "Join now"})["status"] == "needs_work"


def test_editorial_depth_requires_systematic_use_not_one_stray_border():
    """The editorial depth vocabulary was added so genuinely flat premium design
    passes. It must still demand a SYSTEM -- a single border or one letter-spacing
    declaration is not craft and must not count."""
    stray = (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Flat Co — services</title><meta name="description" content="We do things.">'
        '<style>body{font-family:system-ui}h1{font-size:40px}'
        '.x{border-top:1px solid #ccc}.y{letter-spacing:.1em}'
        '@media(max-width:640px){body{font-size:15px}}</style></head><body>'
        '<header><a href="#a">Go</a></header><main>'
        '<section><h1>Flat</h1><p>Text.</p><a href="#a">Go</a></section></main>'
        '<footer>Flat Co</footer></body></html>'
    )
    r = evaluate_landing_page_quality(stray, {"primary_cta": "Go"})
    failed = {c["key"] for c in r["checks"] if not c["passed"]}
    assert "visual_depth" in failed          # one border + one tracking != depth
    assert r["status"] == "needs_work"
