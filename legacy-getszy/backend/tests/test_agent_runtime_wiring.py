"""P1.1 runtime wiring: roles and repo intelligence actually reach execution.

Everything here runs the REAL machinery — the real tool executor, the real
run_task loop, the real delegation ceiling — with only the model scripted, so a
green here means the capability is genuinely wired, not merely importable.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("JWT_SECRET", "test-only-runtime-wiring-secret-32ch!!")

import agent_tools  # noqa: E402
import agent_runtime as rt  # noqa: E402
import agent_delegation as dg  # noqa: E402
import agent_guard  # noqa: E402
import agent_roles as roles  # noqa: E402

FULL = frozenset(agent_tools.ENGINEERING_TOOLS)


# ── repo-map is a registered, read-only capability ───────────────────────────

def test_repo_map_query_is_registered_as_a_readonly_capability():
    assert "repo_map_query" in agent_tools.ENGINEERING_TOOLS
    assert any(s["function"]["name"] == "repo_map_query" for s in agent_tools.ENGINEERING_SCHEMAS)
    assert agent_guard.classify("repo_map_query") == "capability"
    assert not agent_guard.is_approval_gated("repo_map_query")
    # available to roles (unioned in via READ_ONLY_TOOLS)
    assert "repo_map_query" in roles.get_role("backend_engineer").allowed_tools
    assert "repo_map_query" in roles.get_role("researcher").allowed_tools


# ── the tool runs through the REAL executor and answers about the real repo ──

async def test_repo_map_tool_answers_through_the_real_executor():
    raw = await agent_tools.execute_engineering_tool(
        "repo_map_query", {"query_type": "where_is", "symbol": "build_config"})
    data = json.loads(raw)
    assert data["count"] >= 1
    assert any(r["file"].endswith("agent_factory.py") for r in data["results"])


async def test_repo_map_tool_validates_arguments():
    r = json.loads(await agent_tools.execute_engineering_tool(
        "repo_map_query", {"query_type": "not_a_query", "symbol": "x"}))
    assert r["error"] == "bad_arguments"


# ── allowed_tools still gates the new tool at the executor in run_task ────────

async def test_run_task_gates_repo_map_by_allowed_tools():
    captured = {}

    def make_model():
        async def model_call(system, user, tools, execute):
            captured["out"] = await execute(
                "repo_map_query", {"query_type": "where_is", "symbol": "build_config"})
        return model_call

    # permitted → real structural answer
    await rt.run_task("task", system_prompt="s", model_call=make_model(),
                      allowed_tools=["repo_map_query", "run_tests"], max_attempts=1)
    assert "agent_factory.py" in captured["out"]

    # not permitted → refused at the executor, even though the tool exists
    await rt.run_task("task", system_prompt="s", model_call=make_model(),
                      allowed_tools=["read_file"], max_attempts=1)
    assert "tool_not_permitted" in captured["out"]


# ── max_rounds threads to a model call that accepts it, safely otherwise ─────

async def test_max_rounds_reaches_a_model_call_that_accepts_it():
    seen = {}

    async def model_call(system, user, tools, execute, max_rounds=None):
        seen["mr"] = max_rounds

    await rt.run_task("task", system_prompt="s", model_call=model_call,
                      max_attempts=1, max_rounds=9)
    assert seen["mr"] == 9


async def test_max_rounds_does_not_break_a_plain_model_call():
    seen = {}

    async def model_call(system, user, tools, execute):   # no max_rounds param
        seen["ok"] = True

    # Passing max_rounds must NOT crash a call whose signature omits it.
    await rt.run_task("task", system_prompt="s", model_call=model_call,
                      max_attempts=1, max_rounds=9)
    assert seen["ok"] is True


# ── a delegated role carries its contract and its loop budget ────────────────

async def test_delegate_role_threads_contract_and_max_rounds():
    seen = {}

    def factory(tier):
        async def call(system, user, tools, execute, max_rounds=None):
            seen["mr"] = max_rounds
        return call

    ctx = dg.master_context(task_id="t", tools=FULL, model_factory=factory)
    out = await dg.delegate(specialist="security_reviewer", task="audit auth", context=ctx)
    spec = out["specialist"]
    assert spec["role_id"] == "security_reviewer"
    assert spec["output_contract"] and spec["verification_requirements"]
    # the role's declared max_rounds actually reached the child's model call
    assert seen["mr"] == roles.get_role("security_reviewer").max_rounds


async def test_free_text_specialist_has_no_role_contract_and_default_rounds():
    seen = {}

    def factory(tier):
        async def call(system, user, tools, execute, max_rounds=None):
            seen["mr"] = max_rounds
        return call

    ctx = dg.master_context(task_id="t", tools=FULL, model_factory=factory)
    out = await dg.delegate(specialist="Senior Python backend engineer who runs pytest.",
                            task="do work", context=ctx)
    assert out["specialist"]["role_id"] is None       # free text stays free text
    assert seen["mr"] is None                          # runtime default, not a role budget
