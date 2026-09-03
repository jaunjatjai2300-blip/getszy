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


# ── art direction must be STRUCTURAL, not a recolour ─────────────────────────
SOLAPUR = "premium modern fitness club website for Solapur Fitness Club"
SOLAPUR_BRIEF = {"brand_name": "Solapur Fitness Club", "vertical": "fitness"}


def _page(recipe_id):
    b = dict(SOLAPUR_BRIEF, design_recipe=recipe_id)
    return _premium_template(SOLAPUR, b)


def test_same_business_different_direction_changes_STRUCTURE_not_only_colour():
    """The core claim of the art-direction system: one business rendered in two
    directions must differ in section plan and component vocabulary, not merely
    in palette. Colour-swapping one template is the failure this prevents."""
    cine, edit = _page("cinematic_luxury"), _page("editorial_fashion")
    assert cine != edit

    cine_plan = dr.get_recipe("cinematic_luxury").composition
    edit_plan = dr.get_recipe("editorial_fashion").composition
    assert cine_plan != edit_plan, "section plans must differ"

    # Compare MARKUP, not the whole document: the shared base stylesheet defines
    # every component class, so matching on the full HTML proves nothing about
    # structure.
    strip = lambda h: re.sub(r"<style\b.*?</style>", "", h, flags=re.S | re.I)
    cine_m, edit_m = strip(cine), strip(edit)
    assert cine_m != edit_m, "markup must differ, not only CSS"

    # components unique to each direction actually appear in its MARKUP
    assert "gstrip" in cine_m and "gstrip" not in edit_m      # cinematic gallery strip
    for marker in ("manifesto", "lgrid", "indexlist"):        # editorial-only components
        assert marker in edit_m, marker
        assert marker not in cine_m, marker + " leaked into cinematic"


def test_each_direction_uses_its_own_visual_treatment():
    seen = {}
    for rid, marker in (("cinematic_luxury", "pv-cinematic"), ("glassmorphism", "pv-glass"),
                        ("futuristic_saas", "pv-future"), ("editorial_fashion", "pv-editorial"),
                        ("professional_local", "pv-plain")):
        html = _page(rid)
        assert marker in html, f"{rid} should render its own {marker} treatment"
        seen[rid] = marker
    assert len(set(seen.values())) == 5


# ── the Solapur visual failure, pinned ───────────────────────────────────────
def test_solapur_never_ships_emoji_cartoon_or_svg_human():
    """REGRESSION for the rejected real-world result: the fitness page shipped a
    giant emoji figure over abstract blobs. Any emoji/mascot/cartoon artwork on a
    real-world premium request is a FAILED visual result."""
    for rid in ("cinematic_luxury", "glassmorphism", "professional_local"):
        html = _page(rid)
        emoji = [c for c in html if ord(c) > 0x2500]
        assert not emoji, f"{rid} shipped emoji artwork: {emoji[:5]}"
        low = html.lower()
        for banned in ("cartoon", "mascot", "clipart", "clip-art", "undraw", "storyset"):
            assert banned not in low, f"{rid} contains {banned}"


def test_emoji_artwork_fails_the_gate_outright():
    """Even an otherwise well-formed premium page must fail when its artwork is
    an emoji glyph — the exact shape of the old _svg_panel hero."""
    from tests.test_builder_premium_quality import SELF_CONTAINED_PREMIUM
    emoji_art = SELF_CONTAINED_PREMIUM.replace(
        "<main>",
        '<main><svg viewBox="0 0 400 300"><text x="50%" y="54%" font-size="86">'
        + chr(0x1F3CB) + "</text></svg>")
    report = evaluate_landing_page_quality(emoji_art, {"primary_cta": "Book a session"})
    failed = {c["key"] for c in report["checks"] if not c["passed"]}
    assert "no_placeholder_art" in failed
    assert report["status"] == "needs_work"


# ── governance metadata is mandatory ─────────────────────────────────────────
def test_every_recipe_carries_licence_and_provenance_metadata():
    for r in dr.RECIPES:
        assert r.license, f"{r.id} has no licence statement"
        assert r.provenance.get("author"), f"{r.id} has no provenance author"
        assert r.provenance.get("origin"), f"{r.id} has no provenance origin"
        assert r.security_review, f"{r.id} has no security review note"
        assert "status" in r.render_verification, f"{r.id} has no render-verification record"
        # third-party code must be declared, never implied to be original
        assert isinstance(r.provenance.get("third_party", ()), (tuple, list))


def test_asset_policy_is_declared_per_direction_and_enforceable():
    cine = dr.get_recipe("cinematic_luxury")
    edit = dr.get_recipe("editorial_fashion")
    fut = dr.get_recipe("futuristic_saas")
    assert cine.requires_photography() and cine.forbids_illustration_hero()
    assert edit.requires_photography() and edit.forbids_illustration_hero()
    assert not fut.requires_photography()      # gradient-led direction, honestly declared
    for r in dr.RECIPES:
        assert r.assets.get("photography") in ("required", "preferred", "optional")
        assert r.motion_rules.get("budget") in ("none", "subtle", "expressive")


def test_claiming_a_premium_direction_while_shipping_a_generic_template_fails():
    """The anti-template rule, stated as the directive states it: a page that
    CLAIMS a high-end art direction but delivers a generic 3-4 section template
    is a failed deliverable, even though the same markup is acceptable from a
    page that makes no such claim."""
    from tests.test_builder_premium_quality import SELF_CONTAINED_PREMIUM
    plain_brief = {"primary_cta": "Book a session"}
    claiming = dict(plain_brief, design_recipe="cinematic_luxury")

    # identical HTML, judged differently because of the promise it makes
    assert evaluate_landing_page_quality(SELF_CONTAINED_PREMIUM, plain_brief)["status"] \
        == "ready_for_human_review"
    claimed = evaluate_landing_page_quality(SELF_CONTAINED_PREMIUM, claiming)
    assert claimed["status"] == "needs_work"
    assert "composition_richness" in {c["key"] for c in claimed["checks"] if not c["passed"]}


def test_real_direction_output_satisfies_its_own_claim():
    """And the system's own output must clear the bar it sets for itself."""
    for rid in dr.all_recipe_ids():
        brief = dict(SOLAPUR_BRIEF, design_recipe=rid)
        report = evaluate_landing_page_quality(_page(rid), brief)
        assert report["status"] == "ready_for_human_review", (rid, report["next_actions"])
