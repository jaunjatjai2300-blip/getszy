"""Persistence tests — durability and memory built on existing components.

Verifies the ADAPTATION layer: idempotency key stability, evidence shaping, and
that model reasoning never reaches the durable record. The underlying
paid_operations / session_memory modules are production code with their own
tests (test_paid_operations.py, test_operation_aware_credits.py) and are not
re-tested here.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("JWT_SECRET", "test-only-agent-persistence-secret-32ch!!")

import agent_persistence as ap  # noqa: E402


def test_idempotency_key_is_stable_for_the_same_request():
    a = ap.task_idempotency_key("fix the failing test", "master")
    b = ap.task_idempotency_key("  fix the failing test  ", "master")
    assert a == b, "whitespace must not change the key"


def test_idempotency_key_differs_per_request_and_per_agent():
    assert ap.task_idempotency_key("task one") != ap.task_idempotency_key("task two")
    assert ap.task_idempotency_key("same", "agent-a") != ap.task_idempotency_key("same", "agent-b")


def test_idempotency_key_is_bounded_for_the_operation_store():
    # paid_operations rejects keys over 200 chars.
    key = ap.task_idempotency_key("x" * 5000)
    assert len(key) <= 200


def test_evidence_carries_verification_facts():
    audit = {
        "request": "r", "attempts": 2, "result": "verified",
        "files_changed": ["backend/x.py"],
        "tests": [{"passed": True, "exit_code": 0}],
        "failures": [], "approvals_granted": ["git_push"], "approvals_denied": [],
        "actions": [{"tool": "read_file", "mutating": False},
                    {"tool": "write_file", "mutating": True}],
        "duration_sec": 1.5,
    }
    ev = ap._evidence(audit)
    assert ev["tests"] == [{"passed": True, "exit_code": 0}]
    assert ev["tools_used"] == ["read_file", "write_file"]
    assert ev["mutating_actions"] == ["write_file"]
    assert ev["files_changed"] == ["backend/x.py"]


def test_evidence_never_carries_model_reasoning():
    audit = {
        "request": "r", "result": "verified", "actions": [],
        "reasoning": "secret chain of thought",
        "plan": "internal deliberation",
    }
    ev = ap._evidence(audit)
    assert "reasoning" not in ev
    assert "secret chain of thought" not in str(ev)


def test_agent_tasks_use_a_distinct_action_type():
    # Must not collide with customer paid actions in the same collection.
    assert ap.AGENT_ACTION_TYPE == "agent_task"


@pytest.mark.asyncio
async def test_memory_failure_never_breaks_a_task():
    """Memory is an enhancement; a Mongo outage must not fail the run."""
    # No Mongo in this environment -> these must degrade, not raise.
    assert await ap.recall("no-such-session") == []
    await ap.remember("no-such-session", "user", "hello")  # must not raise
