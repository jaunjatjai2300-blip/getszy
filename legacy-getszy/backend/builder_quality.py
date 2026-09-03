"""Deterministic preflight checks for Talk-to-Build landing-page output.

The evaluator is deliberately conservative: it verifies observable HTML structure and
metadata, but never claims that an AI-generated page is visually perfect or guaranteed
to convert. Its report is stored with a project so customers can improve the output
before publishing it.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List


PREVIEW_QUALITY_VERSION = "1.1"

# Observable content that must never be represented as a finished customer deliverable.
_PLACEHOLDER_PATTERN = r"\[\s*(?:add|insert|your|placeholder)[^\]]*\]|lorem\s+ipsum|student\s+name|your\s+name"
_DEMO_PATTERN = r"jaks\.dev|jack-codes|templates\.jack-codes|free\s+(?:html|website)\s+template"
_FAKE_CONTACT_PATTERN = r"123\s+rhythm\s+street|\+1\s*234\s*567\s*890|info@(?:solaourdance|example)\.com"
_UNSUPPORTED_PROMISE_PATTERN = r"\b(?:free\s+trial\s+guarantee|money[-\s]?back\s+guarantee|limited\s+stock|unbeatable\s+prices|up\s+to\s+\d+%\s+off)\b"


def _has(pattern: str, html: str, flags: int = re.IGNORECASE) -> bool:
    return bool(re.search(pattern, html, flags))


def _count(pattern: str, html: str, flags: int = re.IGNORECASE) -> int:
    return len(re.findall(pattern, html, flags))


def _check(
    key: str,
    label: str,
    passed: bool,
    required: bool,
    guidance: str,
) -> Dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "passed": passed,
        "required": required,
        "guidance": guidance,
    }


def _non_empty(values: Iterable[Any]) -> List[str]:
    return [str(value).strip() for value in values if str(value or "").strip()]


def evaluate_landing_page_quality(
    html: str,
    brief: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return an explainable structural quality preflight for generated HTML.

    This is not a subjective design judge. Passing the preflight means the document has
    the expected technical and conversion-oriented foundations; it remains the
    customer's responsibility to review copy, legal claims, visual assets and fit.
    """
    html = html or ""
    brief = brief or {}
    expected_cta = str(brief.get("primary_cta") or "").strip().lower()
    expected_goal = str(brief.get("primary_goal") or "").strip()
    proof_points = _non_empty(brief.get("proof_points") or [])

    has_form = _has(r"<form\b", html)
    has_privacy = _has(r"privacy\s*(policy|notice)|privacy-policy", html)
    has_images = _has(r"<img\b", html)
    has_visual_foundation = (
        has_images
        or _has(r"background(?:-image)?\s*:\s*(?:url|linear-gradient|radial-gradient)", html)
        or _has(r"<svg\b", html)
    )
    all_images_have_alt = not _has(r"<img\b(?![^>]*\balt\s*=)[^>]*>", html)
    cta_labels = re.findall(r"<(?:a|button)\b[^>]*>(.*?)</(?:a|button)>", html, re.IGNORECASE | re.DOTALL)
    cta_text = " ".join(re.sub(r"<[^>]+>", " ", value).lower() for value in cta_labels)

    # ── premium visual-quality signals, measured from SELF-CONTAINED CSS ──
    # The signals below are read only from CSS that renders WITHOUT any external
    # runtime: the content of <style> blocks plus inline style="" attributes.
    # Utility classes (Tailwind) are deliberately NOT counted: they render only if
    # the Tailwind Play CDN loads and runs inside the sandboxed preview, and when
    # it does not (a weak model omits/malforms the <script>, or the CDN is
    # unavailable) the page ships visibly unstyled. Requiring self-contained CSS
    # is what guarantees the customer actually SEES the premium design. The
    # deterministic premium floor and curated starters are fully self-contained
    # and pass; a Tailwind-class-only page does not.
    section_count = _count(r"<section\b", html) + _count(r"<article\b", html)
    _style_css = " ".join(re.findall(r"<style\b[^>]*>(.*?)</style>", html, re.IGNORECASE | re.DOTALL))
    _inline_css = " ".join(re.findall(r"style\s*=\s*[\"']([^\"']+)[\"']", html, re.IGNORECASE))
    self_css = _style_css + " " + _inline_css
    self_css_len = len(_style_css) + len(_inline_css)
    # Depth comes in two legitimate design vocabularies and the gate must be
    # literate in both, or it rejects real craft.
    #
    # MAXIMALIST depth: shadows, gradients, rounded surfaces, motion.
    # EDITORIAL depth: deliberately flat -- a premium magazine layout builds
    # hierarchy from hairline rules, letterspacing discipline and a wide type
    # ramp, and would carry no shadow at all. Judging that page by shadows alone
    # marks genuine high-end design as "flat".
    #
    # This does NOT lower the bar: the threshold stays at >=2 signals, and the
    # editorial signals require SYSTEMATIC use (>=3 occurrences), so one stray
    # border or a single letter-spacing declaration still counts for nothing.
    _rule_system = len(re.findall(r"border-(?:top|bottom|right|left)\s*:\s*1(?:\.5)?px", self_css)) >= 3
    _tracking = len(re.findall(r"letter-spacing\s*:\s*[-.\d]+em", self_css)) >= 3
    polish_signals = sum([
        _has(r"box-shadow\s*:", self_css),
        _has(r"(?:linear|radial)-gradient\(", self_css),
        _has(r"border-radius\s*:\s*(?:1[2-9]|[2-9]\d)px|border-radius\s*:\s*9999", self_css),
        _has(r"transition\s*:|animation\s*:", self_css),
        _rule_system,
        _tracking,
    ])
    has_type_scale = (
        _has(r"clamp\(", self_css)
        or len({m for m in re.findall(r"font-size\s*:\s*(\d+)", self_css)}) >= 3
    )
    has_design_system = _has(r"--[a-z][\w-]*\s*:", self_css) or self_css_len >= 500

    checks = [
        _check(
            "document_shell",
            "Complete HTML document",
            _has(r"<!doctype\s+html", html) and _has(r"</html\s*>", html),
            True,
            "Use a complete HTML document so the downloaded project can run independently.",
        ),
        _check(
            "mobile_viewport",
            "Mobile viewport metadata",
            _has(r"<meta[^>]+name=[\"']viewport[\"']", html),
            True,
            "Include the viewport meta tag and verify the result at a 375px mobile width.",
        ),
        _check(
            "page_title",
            "Descriptive page title",
            bool(re.search(r"<title>\s*[^<]{4,}</title>", html, re.IGNORECASE)),
            True,
            "Add a concise page title that names the offer or brand.",
        ),
        _check(
            "meta_description",
            "Meta description",
            _has(r"<meta[^>]+name=[\"']description[\"']", html),
            True,
            "Add a customer-readable meta description; do not rely on placeholder copy.",
        ),
        _check(
            "single_h1",
            "One clear primary headline",
            _count(r"<h1\b", html) == 1,
            True,
            "Use one benefit-led H1 that makes the offer understandable in a few seconds.",
        ),
        _check(
            "semantic_landmarks",
            "Semantic content landmarks",
            _has(r"<main\b", html) and _has(r"<(?:header|section)\b", html) and _has(r"<footer\b", html),
            True,
            "Use header, main, section and footer landmarks for clarity and accessibility.",
        ),
        _check(
            "primary_cta",
            "Visible primary call to action",
            bool(cta_labels) and (not expected_cta or expected_cta in cta_text),
            True,
            "Use one clear, action-led CTA; repeat the same goal only where it helps the visitor act.",
        ),
        _check(
            "responsive_rules",
            "Responsive layout rules",
            _has(r"@media\s*\(|\b(?:sm|md|lg|xl):", html),
            True,
            "Include responsive CSS or utility variants and review desktop, tablet and mobile previews.",
        ),
        _check(
            "visual_foundation",
            "Intentional visual foundation",
            has_visual_foundation,
            True,
            "Use an intentional hero visual, brand-led composition or approved customer asset; a plain generic layout is not a finished landing-page deliverable.",
        ),
        _check(
            "image_alt_text",
            "Accessible image descriptions",
            (not has_images) or all_images_have_alt,
            True,
            "Every meaningful image needs useful alt text; decorative images may use an empty alt attribute.",
        ),
        _check(
            "no_placeholder_content",
            "No demo placeholders",
            not _has(_PLACEHOLDER_PATTERN, html),
            True,
            "Replace template placeholders and anonymous testimonial stubs with verified customer content or remove the section before review.",
        ),
        _check(
            "no_demo_residue",
            "No source-template residue",
            not _has(_DEMO_PATTERN, html),
            True,
            "Remove template-demo bars, source brands, free-download messaging, analytics and source metadata before customer review.",
        ),
        _check(
            "no_fake_contacts",
            "No example contact details",
            not _has(_FAKE_CONTACT_PATTERN, html),
            True,
            "Use the customer's confirmed contact details or leave contact details out of the private draft.",
        ),
        _check(
            "no_unsupported_promises",
            "No unsupported promotional promise",
            not _has(_UNSUPPORTED_PROMISE_PATTERN, html),
            True,
            "Remove unverified guarantees, urgency, discounts and promotional promises; add only customer-approved factual offers.",
        ),
        _check(
            "goal_alignment",
            "Explicit conversion goal",
            bool(expected_goal),
            False,
            "Set a primary goal such as collect leads, book a demo, sell a product or start a trial.",
        ),
        _check(
            "proof_plan",
            "Authentic proof plan",
            bool(proof_points) or not _has(r"testimonial|trusted by|customer stories", html),
            False,
            "Provide real testimonials, verified metrics or customer logos before publishing; never invent proof.",
        ),
        _check(
            "form_privacy",
            "Privacy link for lead capture",
            (not has_form) or has_privacy,
            False,
            "If the page collects personal data, add a real privacy-policy link before publishing.",
        ),
        # ── premium visual-quality baseline (the bar a basic-but-valid page fails) ──
        _check(
            "self_contained_styling",
            "Self-contained styling (renders without a CDN)",
            self_css_len >= 400,
            True,
            "Put the design system in an inline <style> block (or inline styles); do not rely on Tailwind or an external styling CDN, which may not load in the sandboxed private preview and leaves the page rendered unstyled.",
        ),
        _check(
            "section_variety",
            "Rich, varied page sections",
            section_count >= 3,
            True,
            "A premium landing page needs several distinct sections (hero, value, proof, features, CTA); one flat block reads as a basic draft.",
        ),
        _check(
            "visual_depth",
            "Premium visual depth",
            polish_signals >= 2,
            True,
            "Add real depth — shadows, gradients, rounded surfaces or smooth transitions; a flat page is not a premium deliverable.",
        ),
        _check(
            "typographic_scale",
            "Deliberate typography scale",
            has_type_scale,
            True,
            "Use a real type scale — fluid clamp() sizes or a clear large-to-small heading ramp — not a single default font size.",
        ),
        _check(
            "design_system",
            "Coherent design system",
            has_design_system,
            True,
            "Build on a coherent style system — design tokens/CSS variables or a utility framework — not a few ad-hoc inline styles.",
        ),
        _check(
            "cta_prominence",
            "Prominent styled call to action",
            _has(r"\.btn\b|class=[\"'][^\"']*\b(?:btn|button|bg-[a-z])|<(?:a|button)[^>]+style=[\"'][^\"']*background", html),
            False,
            "Give the primary CTA a prominent, styled button treatment so the next step is unmistakable.",
        ),
    ]

    # ── anti-template checks ────────────────────────────────────────────────
    # A page can satisfy every structural check above and still be a recoloured
    # template with clip-art. These checks target that failure mode directly.
    #
    # Emoji/cartoon-led art: an emoji rendered as page artwork (inside the SVG
    # artwork or at display size) is clip-art, not design. Emoji used as small
    # inline text is not the target, so the test is scoped to the artwork.
    _svg_blocks = " ".join(re.findall(r"<svg\b.*?</svg>", html, re.IGNORECASE | re.DOTALL))
    _emoji = re.compile(
        "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]")
    _emoji_art = bool(_emoji.search(_svg_blocks))
    _big_emoji_text = bool(re.search(
        r"font-size\s*[:=]\s*[\"']?\s*(?:[4-9]\d|\d{3,})", _svg_blocks)) and _emoji_art
    # Generic human/mascot illustration standing in for real imagery.
    _cartoon = bool(re.search(
        r"(?:cartoon|mascot|avatar|clipart|clip-art|undraw|storyset)", html, re.IGNORECASE))

    # Component vocabulary: distinct component types, not one grid repeated.
    _component_kinds = sum(bool(re.search(pat, html, re.IGNORECASE)) for pat in (
        r'class="[^"]*\bnav\b', r'class="[^"]*\bfeatrow\b', r'class="[^"]*\bsteps?\b',
        r'class="[^"]*\bgrid3\b', r'<details', r'class="[^"]*\bctaband\b',
        r'class="[^"]*\b(?:gstrip|lgrid|indexlist|manifesto|specs|stats)\b',
    ))

    # Direction-declared expectations, when the caller supplied one.
    _direction = (brief or {}).get("design_recipe") or (brief or {}).get("_direction_id") or ""
    _recipe = None
    if _direction:
        try:
            import design_registry as _dr
            _recipe = _dr.get_recipe(_direction)
        except Exception:
            _recipe = None
    _motion_expected = bool(_recipe and (_recipe.motion_rules or {}).get("budget") not in (None, "none"))
    _motion_present = _has(r"transition\s*:|animation\s*:|@keyframes", self_css)
    _illustration_hero_forbidden = bool(_recipe and _recipe.forbids_illustration_hero())

    checks.extend([
        _check(
            "no_placeholder_art",
            "No emoji or cartoon stand-in artwork",
            not (_emoji_art or _big_emoji_text or _cartoon),
            True,
            "Emoji, mascots and cartoon people are clip-art, not design. Use real licensed "
            "photography, or a composed abstract treatment for the art direction.",
        ),
        _check(
            "composition_richness",
            "Rich component vocabulary",
            _component_kinds >= 4,
            # Binding only when the page CLAIMS a high-end art direction. A page
            # that promises "cinematic"/"editorial" and delivers a generic 3-4
            # section template is a failed deliverable. A modest page that makes
            # no such claim is judged by the universal checks alone -- this check
            # exists to catch broken promises, not to outlaw simple pages.
            bool(_direction),
            "Compose from several distinct component types (navigation, feature rows, a "
            "process or index, an accordion, a CTA band) — a page that claims a premium art "
            "direction but is built from one repeated card grid reads as a template.",
        ),
        _check(
            "art_direction_motion",
            "Motion matches the declared art direction",
            (not _motion_expected) or _motion_present,
            False,
            "This art direction declares a motion budget, so the page should carry the "
            "corresponding transition/animation vocabulary.",
        ),
        _check(
            "art_direction_imagery",
            "Imagery matches the declared art direction",
            (not _illustration_hero_forbidden) or not (_emoji_art or _cartoon),
            False,
            "This art direction forbids illustration as the primary hero media; supply real "
            "photography or the direction's composed treatment.",
        ),
    ])

    required_checks = [check for check in checks if check["required"]]
    passed_required = sum(1 for check in required_checks if check["passed"])
    passed_optional = sum(1 for check in checks if not check["required"] and check["passed"])
    score = round(100 * (passed_required + 0.5 * passed_optional) / (len(required_checks) + 0.5 * (len(checks) - len(required_checks))))
    failed_required = [check["key"] for check in required_checks if not check["passed"]]

    # The premium baseline is passing every *required* check (truthfulness,
    # structure, CTA, proof-plan, etc.). When that is met the page is eligible
    # for human/customer review; gating on a high numeric score kept the review
    # gate effectively unreachable, so we no longer require score >= 90.
    if failed_required:
        status = "needs_work"
    else:
        status = "ready_for_human_review"

    return {
        "version": PREVIEW_QUALITY_VERSION,
        "score": score,
        "status": status,
        "required_checks_passed": passed_required,
        "required_checks_total": len(required_checks),
        "checks": checks,
        "next_actions": [check["guidance"] for check in checks if not check["passed"]][:4],
        "disclaimer": "Automated preflight checks document structure and declared brief data. It does not guarantee visual quality, legal compliance, accessibility conformance or conversion performance; review the private preview before publishing.",
    }
