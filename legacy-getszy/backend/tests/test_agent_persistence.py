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


# ── runtime wiring (added after persistence was connected to run_task) ───────

@pytest.mark.asyncio
async def test_persist_requires_user_id():
    """Durability cannot be requested without an owner to key it against."""
    import agent_runtime as rt
    async def driver(system, user, tools, execute):
        pass
    with pytest.raises(ValueError):
        await rt.run_task("x", system_prompt="s", model_call=driver, persist=True)


@pytest.mark.asyncio
async def test_memory_session_does_not_break_a_run_without_mongo():
    """session_id is accepted and degrades cleanly when the store is absent."""
    import agent_runtime as rt
    async def driver(system, user, tools, execute):
        await execute("run_tests", {"target": "backend/tests/test_agent_guard.py"})
    out = await rt.run_task(
        "verify guard", system_prompt="s", model_call=driver,
        session_id="sess-no-mongo", user_id="u1",
    )
    assert out["result"] == "verified"


def test_model_tier_maps_to_an_installed_model_only():
    """A tier must never resolve to a model that is not installed."""
    from agent_llm import model_for_tier, TIER_MODELS
    # none installed -> None, never a hallucinated model name
    assert model_for_tier("strong", installed=[]) is None
    # only the 7b present -> strong falls back to it, not to 14b
    assert model_for_tier("strong", installed=["qwen2.5-coder:7b"]) == "qwen2.5-coder:7b"
    # exact preference honoured when present
    assert model_for_tier("strong", installed=["qwen2.5-coder:14b", "qwen2.5-coder:7b"]) == "qwen2.5-coder:14b"
    assert model_for_tier("light", installed=["llama3.2:3b"]) == "llama3.2:3b"
    assert set(TIER_MODELS) == {"light", "standard", "strong"}


def test_factory_tiers_all_resolve():
    """Every tier the factory can assign must exist in the model map."""
    from agent_factory import MODEL_TIERS
    from agent_llm import TIER_MODELS
    assert set(MODEL_TIERS) <= set(TIER_MODELS)
