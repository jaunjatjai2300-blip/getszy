"""Deterministic preflight checks for Talk-to-Build landing-page output.

The evaluator is deliberately conservative: it verifies observable HTML structure and
metadata, but never claims that an AI-generated page is visually perfect or guaranteed
to convert. Its report is stored with a project so customers can improve the output
before publishing it.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List


PREVIEW_QUALITY_VERSION = "1.0"


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
    all_images_have_alt = not _has(r"<img\b(?![^>]*\balt\s*=)[^>]*>", html)
    cta_labels = re.findall(r"<(?:a|button)\b[^>]*>(.*?)</(?:a|button)>", html, re.IGNORECASE | re.DOTALL)
    cta_text = " ".join(re.sub(r"<[^>]+>", " ", value).lower() for value in cta_labels)

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
            "image_alt_text",
            "Accessible image descriptions",
            (not has_images) or all_images_have_alt,
            True,
            "Every meaningful image needs useful alt text; decorative images may use an empty alt attribute.",
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
    ]

    required_checks = [check for check in checks if check["required"]]
    passed_required = sum(1 for check in required_checks if check["passed"])
    passed_optional = sum(1 for check in checks if not check["required"] and check["passed"])
    score = round(100 * (passed_required + 0.5 * passed_optional) / (len(required_checks) + 0.5 * (len(checks) - len(required_checks))))
    failed_required = [check["key"] for check in required_checks if not check["passed"]]

    if failed_required:
        status = "needs_work"
    elif score >= 90:
        status = "ready_for_human_review"
    else:
        status = "review_recommended"

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
