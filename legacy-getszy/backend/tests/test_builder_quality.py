import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from builder_quality import evaluate_landing_page_quality
from template_catalog import render_customer_template


# A genuinely premium professional page: design tokens, fluid type scale, gradient
# hero, elevated cards and smooth transitions — the visual baseline the gate now
# requires. (Previously this fixture was structurally valid but visually flat, i.e.
# exactly the "basic-but-valid" output the premium gate is designed to reject.)
PROFESSIONAL_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Acme Analytics — Turn reports into decisions</title>
  <meta name="description" content="Analytics for modern retail teams.">
  <style>
    :root{--brand:#3b5bdb;--ink:#0b1020;--bg:#fbfcff;--surface:#ffffff;--radius:20px}
    body{font-family:'Inter',system-ui,sans-serif;color:var(--ink);background:var(--bg);line-height:1.6;margin:0}
    h1{font-size:clamp(36px,6vw,64px);font-weight:800;letter-spacing:-0.02em;line-height:1.05}
    h2{font-size:clamp(26px,4vw,40px);font-weight:700;letter-spacing:-0.01em}
    .hero{background:radial-gradient(1000px 500px at 80% -10%, #3b5bdb22, transparent), linear-gradient(135deg,#3b5bdb0d,#7048e805);padding:96px 24px}
    .btn{display:inline-flex;gap:8px;background:var(--brand);color:#fff;padding:14px 26px;border-radius:999px;font-weight:700;text-decoration:none;transition:transform .2s ease, box-shadow .2s ease}
    .btn:hover{transform:translateY(-2px);box-shadow:0 14px 32px #3b5bdb33}
    .card{background:var(--surface);border-radius:var(--radius);box-shadow:0 18px 40px rgba(11,16,32,.08);padding:28px;transition:transform .2s ease}
    section{padding:80px 24px}
    @media (max-width: 640px){ .hero{padding:56px 20px} section{padding:56px 20px} }
    a:focus-visible,button:focus-visible{outline:3px solid var(--brand);outline-offset:3px}
  </style>
</head>
<body>
  <header><a class="btn" href="#cta">Book a demo</a></header>
  <main>
    <section class="hero"><h1>Turn reports into confident decisions</h1><p>Retail analytics for growing teams.</p><a class="btn" href="#cta">Book a demo</a></section>
    <section><h2>How it works</h2><div class="card"><img src="https://example.com/chart.png" alt="Analytics dashboard preview"></div></section>
    <section><h2>Built for retail teams</h2><div class="card"><p>Connect your data and see the metrics that matter, without a data team.</p></div></section>
    <section id="cta"><h2>Ready to decide with confidence?</h2><a class="btn" href="#book">Book a demo</a></section>
  </main>
  <footer><a href="/privacy-policy">Privacy policy</a></footer>
</body>
</html>"""


def test_quality_preflight_accepts_observable_professional_foundations():
    report = evaluate_landing_page_quality(
        PROFESSIONAL_PAGE,
        {
            "audience": "Indian D2C founders",
            "primary_goal": "Book a demo",
            "primary_cta": "Book a demo",
            "proof_points": ["Customer case study supplied by founder"],
        },
    )

    assert report["status"] == "ready_for_human_review"
    assert report["score"] >= 90
    assert report["required_checks_passed"] == report["required_checks_total"]
    assert not report["next_actions"]


def test_quality_preflight_identifies_missing_mobile_and_conversion_foundations():
    report = evaluate_landing_page_quality("<html><body><h1>Untitled</h1></body></html>")
    failed = {check["key"] for check in report["checks"] if not check["passed"]}

    assert report["status"] == "needs_work"
    assert {"document_shell", "mobile_viewport", "page_title", "primary_cta", "responsive_rules"} <= failed
    assert report["next_actions"]


def test_curated_dance_starter_meets_customer_quality_foundations():
    html = render_customer_template(
        "dance-academy",
        project_name="Solaour Dance Academy",
        prompt="Build a premium dance academy landing page",
        brief={"primary_goal": "Collect qualified leads", "primary_cta": "Plan a visit", "offer": "Kathak and contemporary classes in Jaipur"},
    )
    report = evaluate_landing_page_quality(html, {"primary_goal": "Collect qualified leads", "primary_cta": "Plan a visit"})

    assert report["status"] == "ready_for_human_review"
    assert report["required_checks_passed"] == report["required_checks_total"]


def test_quality_preflight_blocks_generic_placeholder_claims_and_fake_contacts():
    generic = PROFESSIONAL_PAGE.replace(
        '<section id="cta"><h2>Ready to decide with confidence?</h2><a class="btn" href="#book">Book a demo</a></section>',
        "<section>What Our Students Say<br>Student Name<br>“[Add authentic testimonial here.]”</section><section id=\"cta\"><button>Book a demo</button></section>"
    ).replace("Privacy policy", "Free Trial Guarantee · 123 Rhythm Street · +1 234 567 890 · info@example.com")
    report = evaluate_landing_page_quality(generic, {"primary_cta": "Book a demo"})
    checks = {check["key"]: check for check in report["checks"]}

    assert report["status"] == "needs_work"
    assert not checks["no_placeholder_content"]["passed"]
    assert not checks["no_fake_contacts"]["passed"]
    assert not checks["no_unsupported_promises"]["passed"]


def test_quality_preflight_requires_privacy_for_lead_capture_forms():
    html = PROFESSIONAL_PAGE.replace('<section id="cta"><h2>Ready to decide with confidence?</h2><a class="btn" href="#book">Book a demo</a></section>', '<section id="cta"><form><input type="email"><button>Book a demo</button></form></section>').replace('<footer><a href="/privacy-policy">Privacy policy</a></footer>', '<footer>Copyright</footer>')
    report = evaluate_landing_page_quality(html, {"primary_cta": "Book a demo"})
    checks = {check["key"]: check for check in report["checks"]}

    assert not checks["form_privacy"]["passed"]
    assert not checks["form_privacy"]["required"]
