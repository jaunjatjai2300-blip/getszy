"""Deterministic control-centre helpers for professional builder projects.

These helpers intentionally never label a project production-ready. They only describe
observable state from the stored brief, evidence choices, quality report and versions.
"""

from __future__ import annotations

from typing import Any

BRIEF_FIELDS = ("audience", "primary_goal", "primary_cta", "offer")


def _present(value: Any) -> bool:
    return bool(str(value or "").strip())


def brief_progress(brief: dict | None) -> dict[str, Any]:
    brief = brief or {}
    completed = [field for field in BRIEF_FIELDS if _present(brief.get(field))]
    missing = [field for field in BRIEF_FIELDS if field not in completed]
    return {
        "completed": len(completed),
        "required": len(BRIEF_FIELDS),
        "is_complete": len(missing) == 0,
        "missing": missing,
    }


def evidence_summary(evidence_items: list[dict] | None) -> dict[str, Any]:
    items = evidence_items or []
    statuses = {"approved": 0, "needs_confirmation": 0, "blocked": 0, "expired": 0}
    for item in items:
        status = str((item or {}).get("status") or "needs_confirmation")
        if status in statuses:
            statuses[status] += 1
    return {
        "total": len(items),
        **statuses,
        "has_blockers": statuses["blocked"] > 0 or statuses["expired"] > 0,
        "has_pending": statuses["needs_confirmation"] > 0,
    }


def quality_summary(report: dict | None) -> dict[str, Any]:
    report = report or {}
    status = str(report.get("status") or "not_run")
    required_passed = report.get("required_checks_passed")
    required_total = report.get("required_checks_total")
    check_complete = isinstance(required_passed, int) and isinstance(required_total, int) and required_total > 0 and required_passed == required_total
    return {
        "status": status,
        "score": report.get("score"),
        "required_checks_passed": required_passed,
        "required_checks_total": required_total,
        "is_ready_for_human_review": status == "ready_for_human_review" and check_complete,
    }


def mission_control_state(project: dict) -> dict[str, Any]:
    """Return a transparent mission map without claiming unavailable checks ran."""
    brief = brief_progress(project.get("brief") or {})
    evidence = evidence_summary(project.get("evidence_items") or [])
    quality = quality_summary(project.get("quality_report") or {})
    versions = int(project.get("version_count") or 0)

    steps = [
        {"key": "founder_brief", "label": "Founder brief", "status": "done" if brief["is_complete"] else "current", "detail": "Complete" if brief["is_complete"] else f"Missing: {', '.join(brief['missing'])}"},
        {"key": "evidence", "label": "Evidence review", "status": "blocked" if evidence["has_blockers"] else ("done" if evidence["total"] and not evidence["has_pending"] else "not_started"), "detail": "Blocked or expired evidence needs attention" if evidence["has_blockers"] else ("Approved evidence is ready" if evidence["total"] and not evidence["has_pending"] else "No completed evidence review yet")},
        {"key": "build", "label": "Build", "status": "done" if bool(project.get("html_content")) else "not_started", "detail": "Private output exists" if project.get("html_content") else "No private output yet"},
        {"key": "quality", "label": "Quality gate", "status": "done" if quality["is_ready_for_human_review"] else ("blocked" if quality["status"] == "needs_work" else "not_started"), "detail": "Ready for human review" if quality["is_ready_for_human_review"] else ("Quality work remains" if quality["status"] == "needs_work" else "Required checks have not run")},
        {"key": "versions", "label": "Versions", "status": "done" if versions > 0 else "not_started", "detail": f"{versions} saved version(s)" if versions else "No named restore point yet"},
        {"key": "release", "label": "Customer approval", "status": "not_started", "detail": "Explicit approval is required; this is never automatic"},
    ]

    current = next((step["key"] for step in steps if step["status"] == "current"), None)
    if not current:
        current = next((step["key"] for step in steps if step["status"] in {"blocked", "not_started"}), "release")
    return {
        "brief": brief,
        "evidence": evidence,
        "quality": quality,
        "steps": steps,
        "current_step": current,
        "eligible_for_customer_review": brief["is_complete"] and not evidence["has_blockers"] and quality["is_ready_for_human_review"],
        "production_ready": False,
        "production_ready_note": "Getszy never infers production readiness from this control centre. Separate release checks and explicit customer approval are required.",
    }
