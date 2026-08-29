"""Premium-output architecture: the gate now rejects basic-but-valid pages, the
deterministic premium floor passes the SAME gate, and Policy A delivers a
verified-premium floor instead of a sub-premium page — never shipping a page
that fails verification just to avoid a refund.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017/test")
os.environ.setdefault("JWT_SECRET", "review-only-secret-32-characters-long!!")

from builder_quality import evaluate_landing_page_quality  # noqa: E402
from builder_agents import _premium_template  # noqa: E402
import routes_builder  # noqa: E402

BRIEF = {"primary_goal": "Book a class", "primary_cta": "Book a class", "audience": "busy professionals"}

# Structurally valid but visually FLAT — passes truthfulness/structure, no polish.
BASIC_PAGE = """<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Acme Yoga Studio</title><meta name="description" content="Yoga for busy people.">
<style>@media (max-width:640px){body{font-size:15px}}</style></head>
<body><header><a href="#book">Book a class</a></header>
<main><section class="hero"><h1>Calm for busy people</h1><p>Weekly classes near you.</p>
<a href="#book">Book a class</a></section></main>
<footer>Acme Yoga</footer></body></html>"""

PREMIUM_TAILWIND = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nova Fitness — Train smarter</title><meta name="description" content="Coaching for women.">
<script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-white text-slate-900">
<header class="p-6"><a href="#join" class="bg-indigo-600 text-white rounded-full px-6 py-3 shadow-lg">Join now</a></header>
<main>
<section class="bg-gradient-to-br from-indigo-50 to-white py-24 px-6"><h1 class="text-6xl font-extrabold tracking-tight">Train smarter, not harder</h1><p class="mt-4">Personal coaching for women.</p><a href="#join" class="bg-indigo-600 text-white rounded-full px-6 py-3 shadow-lg transition">Join now</a></section>
<section class="py-20 px-6"><h2 class="text-4xl font-bold">How it works</h2><div class="grid md:grid-cols-3 gap-6"><div class="rounded-2xl shadow-xl p-8">Plan</div><div class="rounded-2xl shadow-xl p-8">Train</div><div class="rounded-2xl shadow-xl p-8">Progress</div></div></section>
<section class="py-20 px-6"><h2 class="text-4xl font-bold">Built for you</h2><p>Flexible sessions that fit your week.</p></section>
<section id="join" class="py-20 px-6"><h2 class="text-4xl font-bold">Ready?</h2><a href="#start" class="bg-indigo-600 text-white rounded-full px-6 py-3 shadow-lg">Join now</a></section>
</main><footer class="p-6">Nova Fitness</footer></body></html>"""


def _failed(report):
    return {c["key"] for c in report["checks"] if not c["passed"]}


# 1 — basic-but-valid is now rejected
def test_basic_but_valid_is_rejected():
    r = evaluate_landing_page_quality(BASIC_PAGE, BRIEF)
    assert r["status"] == "needs_work"
    # the premium checks are precisely what catch it (structure/truthfulness passed)
    assert {"section_variety", "visual_depth", "typographic_scale", "design_system"} & _failed(r)


# 2 — REGRESSION for the real root cause: a page whose styling is ONLY Tailwind
# utility classes depends on the Play CDN runtime and renders UNSTYLED in the
# sandboxed preview (verified in a real browser). It has "premium" class names in
# source but loses all styling at render, so it MUST be rejected — never shipped
# as premium. This test fails if the gate ever again rewards CDN-dependent styling.
def test_tailwind_cdn_only_page_is_rejected():
    r = evaluate_landing_page_quality(PREMIUM_TAILWIND, {"primary_cta": "Join now", "primary_goal": "Sign up"})
    assert r["status"] == "needs_work"
    failed = _failed(r)
    assert "self_contained_styling" in failed                       # the exact defect
    assert {"visual_depth", "design_system", "typographic_scale"} <= failed  # its "premium" was CDN-only


# 2b — a self-contained inline-CSS premium page (styling survives render) IS accepted
SELF_CONTAINED_PREMIUM = (
    '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1">'
    '<title>Aura Studio — Wellness</title><meta name="description" content="Calm, guided wellness.">'
    '<style>'
    ':root{--brand:#0e7c66;--ink:#10201b;--bg:#f7fbf9;--surface:#fff;--radius:20px}'
    "body{font-family:'Inter',system-ui,sans-serif;color:var(--ink);background:var(--bg);margin:0;line-height:1.6}"
    'h1{font-size:clamp(38px,6vw,66px);font-weight:800;letter-spacing:-0.02em}'
    'h2{font-size:clamp(24px,4vw,38px);font-weight:700}'
    '.hero{background:radial-gradient(900px 480px at 80% -10%,#0e7c6622,transparent),linear-gradient(135deg,#0e7c660d,#c58b7a08);padding:92px 24px}'
    '.btn{display:inline-flex;background:var(--brand);color:#fff;padding:14px 26px;border-radius:999px;font-weight:700;text-decoration:none;transition:transform .2s ease,box-shadow .2s ease}'
    '.card{background:var(--surface);border-radius:var(--radius);box-shadow:0 18px 40px rgba(16,32,27,.08);padding:26px;transition:transform .2s ease}'
    'section{padding:76px 24px}@media(max-width:640px){section{padding:52px 20px}}'
    '</style></head><body>'
    '<header><a class="btn" href="#book">Book a session</a></header><main>'
    '<section class="hero"><h1>Calm, guided wellness</h1><p>Personalised sessions near you.</p><a class="btn" href="#book">Book a session</a></section>'
    '<section><h2>How it works</h2><div class="card">Assess, plan, practise.</div></section>'
    '<section><h2>Why Aura</h2><div class="card">Certified guides and a calm space.</div></section>'
    '<section id="book"><h2>Ready to begin?</h2><a class="btn" href="#start">Book a session</a></section>'
    '</main><footer>Aura Studio</footer></body></html>'
)


def test_self_contained_premium_page_is_accepted():
    r = evaluate_landing_page_quality(SELF_CONTAINED_PREMIUM, {"primary_cta": "Book a session"})
    assert r["status"] == "ready_for_human_review", r["next_actions"]


# 3 — the deterministic premium floor passes the SAME gate (Policy A depends on this)
@pytest.mark.parametrize("prompt,brief", [
    ("a yoga studio", {"brand_name": "Calm"}),
    ("a family pizza restaurant", {"brand_name": "Forno", "vertical": "restaurant"}),
    ("a boutique bakery", {"brand_name": "Sweet Crumb"}),
])
def test_premium_floor_passes_the_gate(prompt, brief):
    r = evaluate_landing_page_quality(_premium_template(prompt, brief), brief)
    assert r["status"] == "ready_for_human_review", r["next_actions"]


# 4 — malformed/unsafe output still fails on the existing structural checks
def test_malformed_output_still_fails():
    r = evaluate_landing_page_quality("<html><body><h1>Untitled</h1></body></html>")
    assert r["status"] == "needs_work"
    assert {"document_shell", "mobile_viewport"} <= _failed(r)


# 5 — Policy A: verified premium floor is delivered when a draft can't reach premium
def test_verified_premium_floor_returns_when_premium():
    html, report = routes_builder._verified_premium_floor("a yoga studio", {"brand_name": "Calm"})
    assert report["status"] == "ready_for_human_review"
    assert "html" in html.lower() and "<h1" in html.lower()


# 6 — Policy A: if even the floor can't verify, never ship it — controlled failure/refund
def test_verified_floor_raises_when_floor_cannot_verify(monkeypatch):
    monkeypatch.setattr(routes_builder, "_premium_template",
                        lambda p, b=None: "<html><body><h1>flat</h1></body></html>")
    with pytest.raises(routes_builder.ProfessionalCompositionError):
        routes_builder._verified_premium_floor("anything", {})


# 7 — customer-specific content survives the fallback
def test_customer_content_preserved_in_floor():
    html = _premium_template("a bakery in Jaipur", {"brand_name": "Sweet Crumb", "audience": "families"})
    assert "Sweet Crumb" in html
    assert evaluate_landing_page_quality(html, {"brand_name": "Sweet Crumb"})["status"] == "ready_for_human_review"


# 8 — truthfulness preserved: testimonials without supplied proof stay flagged
def test_unsupported_proof_is_still_flagged():
    html = _premium_template("a spa", {"brand_name": "Aura"}) + "<section>testimonials — trusted by customers</section>"
    checks = {c["key"]: c for c in evaluate_landing_page_quality(html, {})["checks"]}
    assert checks["proof_plan"]["passed"] is False


# 9 — responsive + a11y remain required and pass on the premium floor
def test_responsive_and_accessibility_preserved_on_floor():
    checks = {c["key"]: c for c in
              evaluate_landing_page_quality(_premium_template("a cafe", {"brand_name": "Bean"}), {})["checks"]}
    assert checks["responsive_rules"]["passed"] and checks["mobile_viewport"]["passed"]
    assert checks["image_alt_text"]["passed"]


# ── business-aware composition across representative business types ───────────
import pytest as _pytest  # noqa: E402
from builder_agents import _premium_template as _pt  # noqa: E402


@_pytest.mark.parametrize("prompt,brief", [
    ("solapur fitness club", {"brand_name": "Solapur Fitness Club", "vertical": "fitness"}),
    ("luxe hair and beauty salon", {"brand_name": "Luxe Salon"}),
    ("forno family pizzeria", {"brand_name": "Forno", "vertical": "restaurant"}),
    ("sharma business consulting", {"brand_name": "Sharma Advisory", "vertical": "consultant"}),
    ("urban threads fashion store", {"brand_name": "Urban Threads", "vertical": "ecommerce"}),
    ("rapid home repair services", {"brand_name": "Rapid Repair", "vertical": "service"}),
])
def test_business_examples_are_composed_and_premium(prompt, brief):
    html = _pt(prompt, brief)
    r = evaluate_landing_page_quality(html, brief)
    low = html.lower()
    # passes the premium gate, self-contained, bounded
    assert r["status"] == "ready_for_human_review", r["next_actions"]
    assert "<style" in low and "cdn.tailwindcss.com" not in html
    assert len(html) < 40000
    # composed from a varied component vocabulary — never a single repeated grid
    assert 'class="nav"' in html and "featrow" in html
    assert 'class="steps"' in html and "<details" in low
    assert html.count("<h1") == 1
    # customer business name survives into the composition
    assert brief["brand_name"] in html
    # honest: no fabricated proof when none supplied
    assert "trusted by" not in low and "5-star" not in low


def test_different_business_types_produce_different_content():
    fit = _pt("fitness club", {"brand_name": "Brand", "vertical": "fitness"})
    rest = _pt("restaurant", {"brand_name": "Brand", "vertical": "restaurant"})
    # same brand, different business -> materially different composed content
    assert fit != rest
    assert "training" in fit.lower() and "training" not in rest.lower()
    assert "menu" in rest.lower()
