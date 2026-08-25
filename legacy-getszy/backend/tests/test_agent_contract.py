"""The two-tier contract, repair-loop learning, and provider-agnostic routing.

Phase 1 exists because a real model repeatedly named `run_tests` where an
approval belonged. The tempting fix -- add run_tests to APPROVAL_REQUIRED so the
request succeeds -- would put a human in front of verification itself, and
evidence-only success depends on an agent being able to run its own tests. So the
contract is enforced structurally instead.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("JWT_SECRET", "test-only-agent-contract-secret-32chars!")

import agent_guard as guard  # noqa: E402
import agent_llm  # noqa: E402
import agent_runtime as rt  # noqa: E402
import agent_tools  # noqa: E402


# ── Phase 1: tools and approvals are different things ────────────────────────

@pytest.mark.parametrize("tool", [
    "run_tests", "read_file", "list_files", "grep_repo", "write_file",
    "git_status", "git_diff", "git_log", "git_commit",
])
def test_engineering_tools_never_require_approval(tool):
    assert not guard.is_approval_gated(tool), f"{tool} must be ordinary engineering work"
    assert guard.classify(tool) == "capability"


@pytest.mark.parametrize("operation", [
    "git_push", "git_reset", "git_force_push", "deploy",
    "db_delete", "db_migrate", "secrets_write", "payment_change", "install_dependency",
])
def test_destructive_and_outward_operations_stay_gated(operation):
    assert guard.is_approval_gated(operation)
    guard.require_approval(operation, {operation})            # with a token: allowed
    with pytest.raises(guard.ApprovalRequired):
        guard.require_approval(operation, None)               # without: refused


def test_the_two_tiers_do_not_overlap():
    assert guard.NEVER_APPROVAL_GATED & guard.APPROVAL_REQUIRED == set()


def test_every_engineering_tool_is_classified():
    """A tool in neither tier would have an undefined authorisation story."""
    unclassified = [t for t in agent_tools.ENGINEERING_TOOLS
                    if guard.classify(t) == "unknown"]
    assert unclassified == [], unclassified


def test_gating_an_engineering_tool_is_rejected_at_import(monkeypatch, tmp_path):
    """The exact patch this contract forbids must not be possible silently."""
    import importlib

    src = open(guard.__file__, encoding="utf-8").read()
    broken = src.replace('    "install_dependency",\n}',
                         '    "install_dependency",\n    "run_tests",\n}', 1)
    assert broken != src, "could not construct the violating variant"

    module_path = tmp_path / "broken_guard.py"
    module_path.write_text(broken, encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    try:
        with pytest.raises(RuntimeError) as e:
            importlib.import_module("broken_guard")
        assert "two-tier contract violated" in str(e.value).lower()
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("broken_guard", None)


@pytest.mark.asyncio
async def test_run_tests_executes_with_no_approvals_granted():
    """The end-to-end proof: verification works with an empty approval set."""
    out = json.loads(await agent_tools.execute_engineering_tool(
        "run_tests", {"target": "backend/tests/test_agent_contract.py"}, approvals=None))
    assert "error" not in out
    assert "exit_code" in out


@pytest.mark.asyncio
async def test_git_push_is_still_refused_with_no_approvals():
    out = json.loads(await agent_tools.execute_engineering_tool(
        "git_push", {"remote": "origin"}, approvals=None))
    assert out["error"] == "approval_required"


# ── Phase 2: a repair attempt is told what actually happened ─────────────────

def _audit_with_failure():
    audit = rt.AuditRecord(task_id="t", request="make the tests pass")
    audit.attempts = 2
    audit.record_action("write_file", {"path": "backend/x.py", "content": "..."},
                        json.dumps({"path": "backend/x.py", "created": True}))
    audit.record_action("run_tests", {"target": "backend/tests/t.py"}, json.dumps({
        "exit_code": 1, "passed": False,
        "output": "E  assert to_snake_case('parseHTTPResponse') == 'parse_http_response'\n"
                  "E  AssertionError: 'parse_h_t_t_p_response' != 'parse_http_response'",
    }))
    return audit


def test_the_real_test_output_is_captured_for_the_next_attempt():
    audit = _audit_with_failure()
    assert audit.tests[-1]["passed"] is False
    assert "AssertionError" in audit.tests[-1]["output_tail"]


def test_the_repair_briefing_carries_the_actual_failure():
    audit = _audit_with_failure()
    briefing = rt._repair_briefing("make the tests pass", audit, "Tests failed (exit code 1).")
    assert "parse_h_t_t_p_response" in briefing, "the model must see what actually broke"
    assert "backend/x.py" in briefing, "it must know what it already changed"
    assert "attempt 2 of 3" in briefing


def test_the_briefing_is_compact_not_a_transcript():
    audit = _audit_with_failure()
    for i in range(30):
        audit.record_action("run_tests", {"target": f"t{i}.py"},
                            json.dumps({"exit_code": 1, "passed": False, "output": "x" * 2000}))
    briefing = rt._repair_briefing("t", audit, "Tests failed.")
    assert len(briefing) < 4000, f"briefing grew to {len(briefing)} chars"


def test_the_briefing_lists_each_refusal_once():
    audit = rt.AuditRecord(task_id="t", request="r")
    audit.attempts = 2
    for _ in range(5):
        audit.record_action("write_file", {"path": "backend/auth.py", "content": "x"},
                            json.dumps({"error": "guard_denied", "detail": "protected"}))
    briefing = rt._repair_briefing("r", audit, "Tests failed.")
    assert briefing.count("guard_denied") == 1, "a repeated refusal adds nothing"


def test_the_briefing_says_so_when_nothing_was_changed():
    audit = rt.AuditRecord(task_id="t", request="r")
    audit.attempts = 2
    briefing = rt._repair_briefing("r", audit, "No test run was executed.")
    assert "not changed any file" in briefing
    assert "never ran the tests" in briefing


@pytest.mark.asyncio
async def test_the_second_attempt_receives_the_briefing_not_the_bare_request():
    prompts = []

    async def driver(system, user, tools, execute):
        prompts.append(user)
        await execute("run_tests", {"target": "backend/tests/_contract_fail_test.py"})

    from agent_guard import REPO_ROOT
    probe = REPO_ROOT / "backend/tests/_contract_fail_test.py"
    probe.write_text("def test_no():\n    assert False\n", encoding="utf-8", newline="")
    try:
        audit = await rt.run_task("do the work", system_prompt="s", model_call=driver)
        assert audit["attempts"] == 3
        assert prompts[0] == "do the work"
        assert "attempt 2 of 3" in prompts[1]
        assert "exited 1" in prompts[1] or "exit code 1" in prompts[1]
    finally:
        probe.unlink(missing_ok=True)


# ── Phase 3: provider-agnostic routing, no customer coupling ─────────────────

@pytest.fixture(autouse=True)
def _clean_escalation_env(monkeypatch):
    for key in (agent_llm.ESCALATION_PROVIDER_ENV, agent_llm.ESCALATION_MODEL_ENV):
        monkeypatch.delenv(key, raising=False)


def test_no_escalation_is_configured_by_default():
    assert agent_llm.escalation_target() is None


def test_attempt_one_always_uses_the_local_model(monkeypatch):
    monkeypatch.setenv(agent_llm.ESCALATION_PROVIDER_ENV, "groq")
    monkeypatch.setenv(agent_llm.ESCALATION_MODEL_ENV, "llama-3.3-70b-versatile")
    plan = agent_llm.plan_for_attempt("standard", 1, ["qwen2.5-coder:7b"])
    assert plan["escalated"] is False
    assert plan["provider"] == "ollama" and plan["model"] == "qwen2.5-coder:7b"


def test_a_later_attempt_escalates_when_a_target_is_configured(monkeypatch):
    monkeypatch.setenv(agent_llm.ESCALATION_PROVIDER_ENV, "groq")
    monkeypatch.setenv(agent_llm.ESCALATION_MODEL_ENV, "llama-3.3-70b-versatile")
    plan = agent_llm.plan_for_attempt("standard", 2, ["qwen2.5-coder:7b"])
    assert plan["escalated"] is True
    assert plan["provider"] == "groq" and plan["model"] == "llama-3.3-70b-versatile"


def test_without_a_configured_target_there_is_no_escalation_and_it_says_so():
    plan = agent_llm.plan_for_attempt("standard", 3, ["qwen2.5-coder:7b"])
    assert plan["escalated"] is False
    assert plan["provider"] == "ollama"
    assert "no escalation configured" in plan["reason"]


def test_an_unknown_escalation_provider_is_ignored(monkeypatch):
    monkeypatch.setenv(agent_llm.ESCALATION_PROVIDER_ENV, "some-vendor")
    assert agent_llm.escalation_target() is None


def test_an_uninstalled_local_escalation_model_is_ignored(monkeypatch):
    monkeypatch.setenv(agent_llm.ESCALATION_PROVIDER_ENV, "ollama")
    monkeypatch.setenv(agent_llm.ESCALATION_MODEL_ENV, "not-a-real-model:999b")
    monkeypatch.setattr(agent_llm, "installed_models", lambda: ["qwen2.5-coder:7b"])
    assert agent_llm.escalation_target() is None


def test_escalation_never_reads_customer_provider_configuration(monkeypatch):
    """Internal work must not depend on, or consume, customer LLM config."""
    monkeypatch.setenv("GROQ_API_KEY", "customer-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "customer-key")
    monkeypatch.setenv("FREE_ONLY", "true")
    assert agent_llm.escalation_target() is None, \
        "customer keys must not silently enable internal escalation"


def test_the_router_returns_none_when_nothing_can_serve_the_attempt():
    """No model and no escalation must fail honestly, not silently degrade."""
    router = agent_llm.router_for("standard", installed=[])
    assert router(1) is None


@pytest.mark.asyncio
async def test_run_task_fails_honestly_when_the_router_has_no_model():
    router = agent_llm.router_for("standard", installed=[])
    with pytest.raises(rt.NoModelAvailable):
        await rt.run_task("do it", system_prompt="s", model_router=router)


@pytest.mark.asyncio
async def test_the_router_is_consulted_once_per_attempt():
    seen = []

    def router(attempt):
        seen.append(attempt)

        async def call(system, user, tools, execute):
            return "nothing done"
        return call

    audit = await rt.run_task("do it", system_prompt="s", model_router=router)
    assert seen == [1, 2, 3], "each attempt must get its own routing decision"
    assert audit["attempts"] == 3
