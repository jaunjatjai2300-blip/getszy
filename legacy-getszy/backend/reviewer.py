"""Reviewer / Verification Agent for the Agent Factory.

Lightweight reviewer that inspects task results, diffs, tests, and
acceptance criteria. Does NOT modify production directly.

Output: PASS / FAIL / NEEDS_HUMAN

Reviewer cannot:
- bypass guard
- approve itself
- change security policy
- deploy
- push
- modify secrets
"""
from __future__ import annotations

import re
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger('getszy.reviewer')


class ReviewVerdict(Enum):
    PASS = 'PASS'
    FAIL = 'FAIL'
    NEEDS_HUMAN = 'NEEDS_HUMAN'


@dataclass
class ReviewCheck:
    name: str
    passed: bool
    severity: str = 'required'  # required | recommended
    message: str = ''

    def to_dict(self) -> dict:
        return {'name': self.name, 'passed': self.passed, 'severity': self.severity, 'message': self.message}


@dataclass
class ReviewResult:
    verdict: ReviewVerdict
    checks: list[ReviewCheck] = field(default_factory=list)
    summary: str = ''
    confidence: float = 0.0  # 0-1

    @property
    def required_passed(self) -> bool:
        return all(c.passed for c in self.checks if c.severity == 'required')

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def total_required(self) -> int:
        return sum(1 for c in self.checks if c.severity == 'required')

    def to_dict(self) -> dict:
        return {
            'verdict': self.verdict.value,
            'checks': [c.to_dict() for c in self.checks],
            'summary': self.summary,
            'confidence': round(self.confidence, 2),
            'passed_count': self.passed_count,
            'total_required': self.total_required,
        }


# ── Review checks ─────────────────────────────────────────────────────────────

def _check_html_structure(html: str) -> ReviewCheck:
    """Verify HTML is a complete document."""
    has_doctype = bool(re.search(r'<!doctype\s+html', html, re.IGNORECASE))
    has_html_end = '</html>' in html.lower()
    has_head = '<head' in html.lower()
    has_body = '<body' in html.lower()
    passed = has_doctype and has_html_end and has_head and has_body
    return ReviewCheck(
        name='html_structure',
        passed=passed,
        severity='required',
        message='Complete HTML document' if passed else 'Missing document structure (doctype/head/body/closing tag)',
    )


def _check_no_placeholders(html: str) -> ReviewCheck:
    """Verify no placeholder content remains."""
    patterns = [
        r'\[\s*(?:add|insert|your|placeholder)[^\]]*\]',
        r'lorem\s+ipsum',
        r'your\s+name\s+here',
        r'todo:',
        r'placeholder',
    ]
    found = []
    for p in patterns:
        matches = re.findall(p, html, re.IGNORECASE)
        found.extend(matches)
    passed = len(found) == 0
    return ReviewCheck(
        name='no_placeholders',
        passed=passed,
        severity='required',
        message='No placeholder content' if passed else f'Found placeholder content: {found[:3]}',
    )


def _check_no_fake_contacts(html: str) -> ReviewCheck:
    """Verify no fake contact details."""
    patterns = [
        r'123\s+rhythm\s+street',
        r'\+1\s*234\s*567\s*890',
        r'info@example\.com',
        r'your@email\.com',
    ]
    found = []
    for p in patterns:
        if re.search(p, html, re.IGNORECASE):
            found.append(p)
    passed = len(found) == 0
    return ReviewCheck(
        name='no_fake_contacts',
        passed=passed,
        severity='required',
        message='No fake contact details' if passed else f'Found fake contacts: {len(found)}',
    )


def _check_responsive(html: str) -> ReviewCheck:
    """Verify responsive CSS rules exist."""
    has_media = bool(re.search(r'@media\s*\(', html))
    has_viewport = bool(re.search(r'name=["\']viewport["\']', html))
    passed = has_media and has_viewport
    return ReviewCheck(
        name='responsive',
        passed=passed,
        severity='required',
        message='Responsive design present' if passed else 'Missing responsive rules or viewport meta',
    )


def _check_single_h1(html: str) -> ReviewCheck:
    """Verify exactly one H1 tag."""
    h1_count = len(re.findall(r'<h1\b', html, re.IGNORECASE))
    passed = h1_count == 1
    return ReviewCheck(
        name='single_h1',
        passed=passed,
        severity='required',
        message='Single H1 present' if passed else f'Found {h1_count} H1 tags (expected 1)',
    )


def _check_semantic_landmarks(html: str) -> ReviewCheck:
    """Verify semantic HTML landmarks."""
    has_main = '<main' in html.lower()
    has_header = '<header' in html.lower() or '<section' in html.lower()
    has_footer = '<footer' in html.lower()
    passed = has_main and has_header and has_footer
    return ReviewCheck(
        name='semantic_landmarks',
        passed=passed,
        severity='recommended',
        message='Semantic landmarks present' if passed else 'Missing semantic landmarks (main/header/footer)',
    )


def _check_brief_alignment(html: str, brief: dict) -> ReviewCheck:
    """Verify the HTML aligns with the customer brief."""
    if not brief:
        return ReviewCheck(name='brief_alignment', passed=True, severity='recommended', message='No brief to check against')

    html_lower = html.lower()
    issues = []

    # Check brand name appears in HTML
    brand = brief.get('brand_name') or brief.get('business_name')
    if brand and str(brand).lower() not in html_lower:
        issues.append(f'Brand name "{brand}" not found in output')

    # Check CTA appears
    cta = brief.get('primary_cta')
    if cta and str(cta).lower() not in html_lower:
        issues.append(f'CTA "{cta}" not found in output')

    passed = len(issues) == 0
    return ReviewCheck(
        name='brief_alignment',
        passed=passed,
        severity='required',
        message='Brief aligned' if passed else f'Brief misalignment: {"; ".join(issues[:3])}',
    )


def _check_no_external_calls(html: str) -> ReviewCheck:
    """Verify no unauthorized external fetch calls."""
    has_fetch = bool(re.search(r'fetch\s*\(\s*["\']https?://', html, re.IGNORECASE))
    has_iframe = bool(re.search(r'<iframe\b[^>]*src\s*=\s*["\']https?://', html, re.IGNORECASE))
    passed = not has_fetch and not has_iframe
    return ReviewCheck(
        name='no_external_calls',
        passed=passed,
        severity='required',
        message='No unauthorized external calls' if passed else 'Found unauthorized external network calls',
    )


# ── Main review function ─────────────────────────────────────────────────────

def review_task_result(
    result: str,
    task_type: str = 'builder',
    brief: dict | None = None,
    acceptance_criteria: list[str] | None = None,
    diff: str | None = None,
    tests_passed: bool | None = None,
    tests_output: str | None = None,
) -> ReviewResult:
    """Review a task result and return a verdict.

    Checks are task-type dependent. Always runs structural checks.
    """
    checks = []

    if task_type == 'builder':
        # HTML-specific checks
        if result and len(result) > 100:
            checks.append(_check_html_structure(result))
            checks.append(_check_no_placeholders(result))
            checks.append(_check_no_fake_contacts(result))
            checks.append(_check_responsive(result))
            checks.append(_check_single_h1(result))
            checks.append(_check_semantic_landmarks(result))
            checks.append(_check_brief_alignment(result, brief or {}))
            checks.append(_check_no_external_calls(result))

    # Generic checks
    if not result or len(result.strip()) < 50:
        checks.append(ReviewCheck(
            name='has_content',
            passed=False,
            severity='required',
            message='Result is empty or too short',
        ))
    else:
        checks.append(ReviewCheck(
            name='has_content',
            passed=True,
            severity='required',
            message=f'Result has {len(result)} chars',
        ))

    # Test results
    if tests_passed is not None:
        checks.append(ReviewCheck(
            name='tests_passed',
            passed=tests_passed,
            severity='required',
            message='Tests passed' if tests_passed else f'Tests failed: {(tests_output or "")[:200]}',
        ))

    # Acceptance criteria
    if acceptance_criteria:
        for i, criterion in enumerate(acceptance_criteria):
            # Basic heuristic: check if the criterion's keywords appear in the result
            keywords = [w.lower() for w in criterion.split() if len(w) > 3]
            found = sum(1 for kw in keywords if kw in result.lower())
            ratio = found / len(keywords) if keywords else 0
            checks.append(ReviewCheck(
                name=f'acceptance_{i}',
                passed=ratio >= 0.3,
                severity='recommended',
                message=f'Criterion "{criterion[:60]}" — keyword match {ratio:.0%}',
            ))

    # Determine verdict
    required_checks = [c for c in checks if c.severity == 'required']
    all_required_passed = all(c.passed for c in required_checks)

    if all_required_passed:
        verdict = ReviewVerdict.PASS
        confidence = sum(1 for c in checks if c.passed) / len(checks) if checks else 0
    elif any(c.severity == 'required' and not c.passed for c in checks):
        verdict = ReviewVerdict.FAIL
        confidence = sum(1 for c in checks if c.passed) / len(checks) if checks else 0
    else:
        verdict = ReviewVerdict.PASS
        confidence = sum(1 for c in checks if c.passed) / len(checks) if checks else 0

    failed_required = [c for c in checks if c.severity == 'required' and not c.passed]
    summary = f'Review {verdict.value}: {sum(1 for c in checks if c.passed)}/{len(checks)} checks passed'
    if failed_required:
        summary += f'. Failed required: {", ".join(c.name for c in failed_required)}'

    logger.info('Review: %s (confidence=%.2f)', verdict.value, confidence)

    return ReviewResult(
        verdict=verdict,
        checks=checks,
        summary=summary,
        confidence=confidence,
    )


async def async_review(
    result: str,
    task_type: str = 'builder',
    brief: dict | None = None,
    acceptance_criteria: list[str] | None = None,
    use_llm: bool = False,
    session_id: str = '',
) -> ReviewResult:
    """Async review — optionally uses LLM for deeper analysis.

    For now, LLM review is a future extension. The deterministic checks
    above are sufficient for V1.
    """
    return review_task_result(
        result=result,
        task_type=task_type,
        brief=brief,
        acceptance_criteria=acceptance_criteria,
    )
