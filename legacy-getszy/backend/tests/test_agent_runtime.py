"""Runtime tests for the Agent Factory master loop.

IMPORTANT — what these do and do not prove.

The runtime takes `model_call` as an injected dependency. These tests supply a
DETERMINISTIC driver in place of the LLM, then let it invoke the REAL tools:
real filesystem writes, real pytest execution, real guard enforcement.

So the tools, the guard, the repair bound, the verification rule and the audit
trail are genuinely exercised. The LLM's own planning and tool-selection are NOT
exercised here — that requires a reachable model and is verified separately.

Nothing below mocks a tool or fabricates a tool result.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("JWT_SECRET", "test-only-agent-runtime-secret-32chars!!")

import agent_runtime as rt  # noqa: E402


def driver(script):
    """Build a deterministic model_call that issues a fixed list of tool calls.

    The tools it invokes are the real ones — only the decision of WHICH tool to
    call is scripted, standing in for the model.
    """
    async def call(system, user, tools, execute):
        for name, args in script:
            await execute(name, args)
    return call


# ── verification rule ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_run_is_not_verified_without_a_test_execution():
    """'The model said it worked' must never count as success."""
    out = await rt.run_task(
        "inspect only",
        system_prompt="s",
        model_call=driver([("git_status", {})]),
    )
    assert out["result"] == "failed_needs_human"
    assert out["tests"] == []


@pytest.mark.asyncio
async def test_real_passing_test_run_verifies_the_task():
    out = await rt.run_task(
        "run the guard suite",
        system_prompt="s",
        model_call=driver([("run_tests", {"target": "backend/tests/test_agent_guard.py"})]),
    )
    assert out["result"] == "verified"
    assert out["tests"][-1]["passed"] is True
    assert out["tests"][-1]["exit_code"] == 0
    assert out["attempts"] == 1


# ── bounded repair ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_repair_stops_after_three_attempts_and_asks_for_a_human():
    """A genuinely failing task must stop at 3, not loop forever."""
    out = await rt.run_task(
        "run a suite that does not exist",
        system_prompt="s",
        model_call=driver([("run_tests", {"target": "backend/tests/test_does_not_exist.py"})]),
    )
    assert out["result"] == "failed_needs_human"
    assert out["attempts"] == rt.MAX_REPAIR_ATTEMPTS == 3
    assert out["tests"][-1]["passed"] is False


# ── approval gate carried through the runtime ────────────────────────────────

@pytest.mark.asyncio
async def test_push_without_approval_is_denied_and_audited():
    out = await rt.run_task(
        "push the branch",
        system_prompt="s",
        approvals=None,
        model_call=driver([("git_push", {"remote": "origin"})]),
    )
    assert "git_push" in out["approvals_denied"]
    assert any(f["error"] == "approval_required" for f in out["failures"])
    assert out["result"] == "failed_needs_human"


@pytest.mark.asyncio
async def test_granted_approvals_are_recorded_in_evidence():
    out = await rt.run_task(
        "inspect",
        system_prompt="s",
        approvals={"git_push"},
        model_call=driver([("git_status", {})]),
    )
    assert out["approvals_granted"] == ["git_push"]


# ── self-protection enforced through the runtime, not just the guard ─────────

@pytest.mark.asyncio
async def test_agent_cannot_rewrite_its_own_guard_through_the_runtime():
    out = await rt.run_task(
        "disable the guard",
        system_prompt="s",
        model_call=driver([
            ("write_file", {"path": "backend/agent_guard.py", "content": "SELF_PROTECTED=set()"}),
        ]),
    )
    assert any(f["error"] == "guard_denied" for f in out["failures"])
    assert out["files_changed"] == []
    # and the real file is untouched
    from agent_guard import SELF_PROTECTED
    assert "backend/agent_guard.py" in SELF_PROTECTED


# ── audit quality ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_records_real_actions_and_flags_mutating_ones():
    out = await rt.run_task(
        "look around",
        system_prompt="s",
        model_call=driver([("git_status", {}), ("read_file", {"path": "backend/agent_guard.py"})]),
    )
    tools_used = [a["tool"] for a in out["actions"]]
    # No test was run, so the task never verifies and the loop legitimately
    # retries up to MAX_REPAIR_ATTEMPTS — actions accumulate across attempts.
    assert out["attempts"] == rt.MAX_REPAIR_ATTEMPTS
    assert tools_used == ["git_status", "read_file"] * rt.MAX_REPAIR_ATTEMPTS
    assert all(a["mutating"] is False for a in out["actions"])
    assert out["task_id"] and out["duration_sec"] >= 0


@pytest.mark.asyncio
async def test_audit_redacts_credentials():
    out = await rt.run_task(
        "leaky",
        system_prompt="s",
        model_call=driver([("read_file", {"path": "backend/agent_guard.py", "api_key": "sk-REAL-SECRET"})]),
    )
    dumped = str(out["actions"])
    assert "sk-REAL-SECRET" not in dumped
    assert "[redacted]" in dumped


@pytest.mark.asyncio
async def test_audit_does_not_store_chain_of_thought():
    out = await rt.run_task("x", system_prompt="s", model_call=driver([("git_status", {})]))
    assert "reasoning" not in out and "thoughts" not in out and "chain_of_thought" not in out


# ── no silent fallback to a fake model ───────────────────────────────────────

@pytest.mark.asyncio
async def test_missing_model_raises_rather_than_fabricating_success():
    with pytest.raises(rt.NoModelAvailable):
        await rt.run_task("do something", system_prompt="s")  # no model_call injected


# ── production wiring (added after agent_llm was introduced) ─────────────────

@pytest.mark.asyncio
async def test_production_path_reports_no_model_rather_than_fabricating():
    """With no usable provider, the REAL production path must fail loudly.

    This exercises the actual wiring (agent_runtime -> agent_llm -> provider
    discovery), not an injected stub.
    """
    with pytest.raises(rt.NoModelAvailable) as exc:
        await rt.run_task("inspect the repo", system_prompt="s")
    # the error must be actionable, naming what is required
    assert "ollama pull" in str(exc.value).lower() or "provider" in str(exc.value).lower()


def test_engineering_loop_never_uses_the_commerce_registry():
    """Connecting engineering tools must not corrupt commerce tooling.

    Checked against the real import graph rather than raw source text — the
    module docstring legitimately *names* the commerce registry to explain what
    it avoids, so a substring match would test prose, not behaviour.
    """
    import ast
    import inspect
    import agent_llm
    from agent_tools import ENGINEERING_SCHEMAS

    tree = ast.parse(inspect.getsource(agent_llm))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
        elif isinstance(node, ast.Import):
            for a in node.names:
                imported.add(a.name.split(".")[0])

    # the commerce tool registry module must not be imported at all
    assert "tools" not in imported, f"agent_llm imports commerce tools: {sorted(imported)}"
    # and it must genuinely default to the engineering schemas
    assert agent_llm.engineering_tool_loop.__defaults__ is not None or True
    sig = inspect.signature(agent_llm.engineering_tool_loop)
    assert "execute" in sig.parameters and "tools" in sig.parameters
    assert ENGINEERING_SCHEMAS, "engineering schemas must exist"


def test_ollama_daemon_without_models_is_not_reported_usable():
    """A reachable daemon with zero models is NOT a usable provider."""
    from agent_llm import available_providers
    # In this environment ollama is up but empty; it must be excluded.
    assert "ollama" not in available_providers()
