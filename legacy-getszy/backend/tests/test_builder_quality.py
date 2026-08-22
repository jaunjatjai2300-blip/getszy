import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from builder_quality import evaluate_landing_page_quality


PROFESSIONAL_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Acme Analytics — Turn reports into decisions</title>
  <meta name="description" content="Analytics for modern retail teams.">
  <style>@media (max-width: 640px) { .hero { padding: 1rem; } }</style>
</head>
<body>
  <header><a href="#cta">Book a demo</a></header>
  <main>
    <section class="hero"><h1>Turn reports into confident decisions</h1><p>Retail analytics for growing teams.</p><a href="#cta">Book a demo</a></section>
    <section><h2>How it works</h2><img src="https://example.com/chart.png" alt="Analytics dashboard preview"></section>
    <section id="cta"><button>Book a demo</button></section>
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


def test_quality_preflight_requires_privacy_for_lead_capture_forms():
    html = PROFESSIONAL_PAGE.replace('<section id="cta"><button>Book a demo</button></section>', '<section id="cta"><form><input type="email"><button>Book a demo</button></form></section>').replace('<footer><a href="/privacy-policy">Privacy policy</a></footer>', '<footer>Copyright</footer>')
    report = evaluate_landing_page_quality(html, {"primary_cta": "Book a demo"})
    checks = {check["key"]: check for check in report["checks"]}

    assert not checks["form_privacy"]["passed"]
    assert not checks["form_privacy"]["required"]
