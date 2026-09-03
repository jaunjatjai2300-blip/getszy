"""OFF-LINE render gate for design recipes. Never imported by the runtime.

WHY THIS LIVES OUTSIDE PRODUCTION
    Verifying a design honestly means rendering it in a real browser and reading
    COMPUTED style -- not grepping the HTML. But Chromium in the production
    backend image would add hundreds of megabytes and real CPU/RAM cost per
    build on a box already running Ollama, Mongo and Redis. So render
    verification is an out-of-band gate: a recipe is rendered and inspected
    here, and only then promoted in the registry. Production keeps the fast,
    dependency-free static gate (builder_quality).

USAGE
    python tools/design_render_check.py              # emit pages + static report
    python tools/design_render_check.py --render     # also drive Playwright
    python tools/design_render_check.py --out DIR

Exit code is non-zero when any recipe fails its gate, so CI can block promotion.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017/render_check")
os.environ.setdefault("JWT_SECRET", "render-check-secret-32-characters-min!!")

import design_registry as dr           # noqa: E402
from builder_agents import _premium_template  # noqa: E402
from builder_quality import evaluate_landing_page_quality  # noqa: E402

# One business rendered in every direction: differences are then attributable to
# the art direction alone, which is the property being verified.
FIXTURE_PROMPT = "premium modern fitness club website for Solapur Fitness Club"
FIXTURE_BRIEF = {"brand_name": "Solapur Fitness Club", "vertical": "fitness",
                 "primary_cta": "Start training"}


def build_pages(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    pages = {}
    for recipe in dr.RECIPES:
        brief = dict(FIXTURE_BRIEF, design_recipe=recipe.id)
        html = _premium_template(FIXTURE_PROMPT, brief)
        path = out_dir / f"{recipe.id}.html"
        path.write_text(html, encoding="utf-8")
        pages[recipe.id] = {"path": str(path), "html": html}
    return pages


def static_gate(recipe, html: str) -> list:
    """Checks that do not need a browser. Failures here block promotion."""
    failures = []
    report = evaluate_landing_page_quality(html, dict(FIXTURE_BRIEF, design_recipe=recipe.id))
    if report["status"] != "ready_for_human_review":
        failures.append(f"quality gate: {report['status']} "
                        f"({[c['key'] for c in report['checks'] if not c['passed'] and c['required']]})")

    # Governance metadata must be present before a recipe can ship.
    if not recipe.license:
        failures.append("no licence statement")
    if not recipe.provenance.get("origin"):
        failures.append("no provenance origin")
    if not recipe.security_review:
        failures.append("no security review note")
    # Third-party code must be declared explicitly, never implied original.
    if recipe.provenance.get("origin") == "original" and recipe.provenance.get("third_party"):
        failures.append("declared original but lists third-party sources")

    # No runtime dependency may sneak in with a recipe.
    css = dr.stylesheet(recipe)
    for bad, why in (("cdn.tailwindcss.com", "Tailwind CDN"), ("@import", "external stylesheet"),
                     ("url(http", "remote asset in CSS")):
        if bad in css:
            failures.append(f"runtime dependency: {why}")

    # Art-direction promises must be kept by the CSS that ships.
    budget = (recipe.motion_rules or {}).get("budget", "none")
    if budget != "none" and not re.search(r"transition\s*:|animation\s*:|@keyframes", css):
        failures.append(f"motion budget '{budget}' declared but no motion in CSS")
    if (recipe.surface_rules or {}).get("blur") == "required" and "backdrop-filter" not in css:
        failures.append("surface rules require blur but CSS has no backdrop-filter")

    # Emoji/cartoon artwork is never an acceptable primary visual.
    svg = " ".join(re.findall(r"<svg\b.*?</svg>", html, re.S | re.I))
    if re.search("[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", svg):
        failures.append("emoji used as artwork")
    return failures


PLAYWRIGHT_CHECKS = """
() => {
  const cs = (el, p) => el ? getComputedStyle(el)[p] : null;
  const body = document.body;
  const h1 = document.querySelector('h1');
  const btn = document.querySelector('.btn');
  const nav = document.querySelector('.nav');
  return {
    bodyBg: cs(body, 'backgroundColor'),
    bodyFont: cs(body, 'fontFamily'),
    h1Size: parseFloat(cs(h1, 'fontSize') || 0),
    h1Family: cs(h1, 'fontFamily'),
    btnBg: cs(btn, 'backgroundColor'),
    btnRadius: cs(btn, 'borderRadius'),
    btnDecoration: cs(btn, 'textDecorationLine'),
    navPosition: cs(nav, 'position'),
    navBackdrop: cs(nav, 'backdropFilter') || cs(nav, 'webkitBackdropFilter'),
    sections: document.querySelectorAll('section').length,
    docHeight: document.body.scrollHeight,
    images: document.querySelectorAll('img').length,
    svgArt: document.querySelectorAll('svg').length,
    hasTransition: [...document.querySelectorAll('*')].some(
      e => (getComputedStyle(e).transitionDuration || '0s') !== '0s'),
  };
}
"""


def render_checks(pages: dict, out_dir: Path) -> dict:
    """Drive a real browser when Playwright is installed. Returns {} otherwise."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("  playwright not installed — skipping browser pass "
              "(pip install playwright && playwright install chromium)")
        return {}

    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for rid, info in pages.items():
            page.goto(Path(info["path"]).as_uri())
            page.wait_for_timeout(350)
            metrics = page.evaluate(PLAYWRIGHT_CHECKS)
            page.screenshot(path=str(out_dir / f"{rid}.png"), full_page=False)
            failures = []
            # Rendered, not claimed: a serif default means the type system did
            # not apply; a blue underlined link means the CTA never got styled.
            if metrics["h1Size"] < 30:
                failures.append(f"h1 renders at {metrics['h1Size']}px — type scale not applied")
            if metrics["btnDecoration"] not in (None, "none"):
                failures.append("CTA renders as an underlined link, not a button")
            if metrics["sections"] < 5:
                failures.append(f"only {metrics['sections']} sections rendered")
            if metrics["docHeight"] < 2000:
                failures.append(f"page is only {metrics['docHeight']}px tall")
            results[rid] = {"metrics": metrics, "failures": failures,
                            "screenshot": str(out_dir / f"{rid}.png")}
        browser.close()
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "_render_check"))
    ap.add_argument("--render", action="store_true", help="drive a real browser via Playwright")
    args = ap.parse_args()

    out_dir = Path(args.out)
    print(f"== rendering {len(dr.RECIPES)} recipes -> {out_dir}")
    pages = build_pages(out_dir)

    report, failed = {}, False
    for recipe in dr.RECIPES:
        problems = static_gate(recipe, pages[recipe.id]["html"])
        report[recipe.id] = {"static_failures": problems}
        status = "PASS" if not problems else "FAIL"
        failed = failed or bool(problems)
        print(f"  [{status}] {recipe.id}")
        for p in problems:
            print(f"          - {p}")

    if args.render:
        print("== browser pass")
        rendered = render_checks(pages, out_dir)
        for rid, res in rendered.items():
            report[rid]["render"] = res
            status = "PASS" if not res["failures"] else "FAIL"
            failed = failed or bool(res["failures"])
            m = res["metrics"]
            print(f"  [{status}] {rid}: h1={m['h1Size']}px sections={m['sections']} "
                  f"height={m['docHeight']}px imgs={m['images']}")
            for f in res["failures"]:
                print(f"          - {f}")

    (out_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"== report: {out_dir / 'report.json'}")
    # Promotion requires a clean run; recipes stay 'pending' in the registry until
    # this gate passes with --render on the promoting machine.
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
