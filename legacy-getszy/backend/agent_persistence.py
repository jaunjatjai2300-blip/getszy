"""Agent Factory — durable persistence, built on existing production components.

Two gaps in the runtime, both already solved elsewhere in Getszy. This module
integrates those solutions rather than reimplementing them:

  1. DURABILITY. AuditRecord lives in memory and dies with the process, so a
     restart mid-task loses the evidence and a retried request re-runs the work.
     `paid_operations` already provides durable records with idempotency keys and
     lease-controlled execution — production-proven for paid customer actions.
     Agent tasks reuse it under action_type 'agent_task'.

  2. MEMORY. run_task is stateless, so a follow-up instruction cannot refer to
     the previous turn. `session_memory` already provides multi-turn context with
     token-window trimming. Agent tasks reuse it.

Nothing here duplicates those modules; it adapts the agent's shapes onto them.

NOTE ON CREDITS: paid_operations deliberately does not debit credits, and this
module does not either. Internal engineering tasks are not customer purchases.
The operation record is used for durability and idempotency only.
"""
from __future__ import annotations

import hashlib
from typing import Any

from paid_operations import (
    RUNNING,
    SUCCEEDED,
    FAILED_REFUNDED,
    claim_execution,
    create_or_reuse_operation,
    get_operation_for_user,
    update_operation,
)

AGENT_ACTION_TYPE = "agent_task"


def task_idempotency_key(request: str, agent_id: str = "master") -> str:
    """Stable key for a (agent, request) pair.

    Deterministic so an identical instruction submitted twice reuses the first
    operation instead of doing the work again.
    """
    digest = hashlib.sha256(f"{agent_id}::{request.strip()}".encode("utf-8")).hexdigest()
    return f"agent:{agent_id}:{digest[:40]}"


async def begin_task(
    *, user_id: str, request: str, agent_id: str = "master", worker_id: str,
    idempotency_key: str | None = None,
) -> tuple[dict, bool]:
    """Create or reuse a durable record, then take the execution lease.

    Returns (operation, should_execute). `should_execute` is False when another
    worker holds the lease or the operation already reached a terminal state —
    the caller must NOT run the task in that case.
    """
    key = idempotency_key or task_idempotency_key(request, agent_id)
    operation, created = await create_or_reuse_operation(
        user_id=user_id,
        action_type=AGENT_ACTION_TYPE,
        idempotency_key=key,
        payload={"request": request[:2000], "agent_id": agent_id},
    )

    claimed = await claim_execution(operation["operation_id"], worker_id)
    if not claimed:
        # Either terminal already, or another worker is executing it.
        return operation, False
    return claimed, True


async def finish_task(*, operation_id: str, audit: dict) -> None:
    """Persist the run's evidence and final state.

    Status is derived from the audit's own verification result, not from a
    caller's assertion — the same evidence-only rule the runtime uses.
    """
    verified = audit.get("result") == "verified"
    await update_operation(operation_id, {
        "status": SUCCEEDED if verified else FAILED_REFUNDED,
        "result_ref": audit.get("task_id"),
        "failure_code": None if verified else audit.get("result"),
        "evidence": _evidence(audit),
        "completed_at": _now(),
    })


async def mark_running(operation_id: str) -> None:
    await update_operation(operation_id, {"status": RUNNING})


def _evidence(audit: dict) -> dict:
    """The durable slice of the audit. Deliberately excludes model reasoning."""
    return {
        "request": audit.get("request"),
        "attempts": audit.get("attempts"),
        "result": audit.get("result"),
        "files_changed": audit.get("files_changed", []),
        "tests": audit.get("tests", []),
        "failures": audit.get("failures", []),
        "approvals_granted": audit.get("approvals_granted", []),
        "approvals_denied": audit.get("approvals_denied", []),
        "tools_used": [a.get("tool") for a in audit.get("actions", [])],
        "mutating_actions": [a.get("tool") for a in audit.get("actions", []) if a.get("mutating")],
        "duration_sec": audit.get("duration_sec"),
    }


def _now() -> str:
    from paid_operations import now
    return now()


# ── memory ───────────────────────────────────────────────────────────────────

async def recall(session_id: str, max_messages: int = 10) -> list[dict]:
    """Prior turns for this agent session, trimmed to the context window."""
    from session_memory import get_context_messages
    try:
        return await get_context_messages(session_id, max_messages=max_messages)
    except Exception:
        # Memory is an enhancement; losing it must not fail the task.
        return []


async def remember(session_id: str, role: str, content: str) -> None:
    from session_memory import add_message
    try:
        await add_message(session_id, role, content[:4000])
    except Exception:
        pass


async def ensure_session(session_id: str, user_id: str, metadata: dict | None = None) -> Any:
    from session_memory import create_session, get_session
    try:
        existing = await get_session(session_id)
        if existing:
            return existing
        return await create_session(session_id, user_id, metadata or {})
    except Exception:
        return None


async def task_status(operation_id: str, user_id: str) -> dict | None:
    """Read a durable agent task record back."""
    return await get_operation_for_user(operation_id, user_id)


__all__ = [
    "AGENT_ACTION_TYPE", "task_idempotency_key", "begin_task", "finish_task",
    "mark_running", "recall", "remember", "ensure_session", "task_status",
]
