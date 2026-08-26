"""Repair learning: structured failure, semantic stuck detection, the ledger.

The behaviour these exist for was observed against the real model: it received a
correct assertion diff and still re-proposed the same conceptual fix in different
code, three times. A syntactic repeat guard cannot see that — the tool calls
differ. A semantic one can.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("JWT_SECRET", "test-only-agent-evidence-secret-32chr!")

import agent_evidence as ev  # noqa: E402
import agent_knowledge as kn  # noqa: E402
import agent_runtime as rt  # noqa: E402
import agent_tools  # noqa: E402
from agent_guard import REPO_ROOT  # noqa: E402

PYTEST_FAIL = """============================= test session starts ==============================
collected 5 items

backend/tests/test_text_case.py .F...                                    [100%]

=================================== FAILURES ===================================
____________________ test_handles_consecutive_capitals _________________________

    def test_handles_consecutive_capitals():
>       assert to_snake_case("parseHTTPResponse") == "parse_http_response"
E       AssertionError: assert 'parse_h_t_t_p_response' == 'parse_http_response'

backend/tests/test_text_case.py:23: AssertionError
=========================== short test summary info ============================
FAILED backend/tests/test_text_case.py::test_handles_consecutive_capitals
========================= 1 failed, 4 passed in 0.31s ==========================
"""


# ── parsing real pytest output ───────────────────────────────────────────────

def test_a_real_assertion_is_parsed_into_fields():
    f = ev.parse_failure(PYTEST_FAIL, 1)
    assert f["test"] == "test_handles_consecutive_capitals"
    assert f["file"] == "backend/tests/test_text_case.py"
    assert f["error_type"] == "AssertionError"
    assert f["actual"] == "'parse_h_t_t_p_response'"
    assert f["expected"] == "'parse_http_response'"


def test_a_pass_parses_to_nothing():
    assert ev.parse_failure("5 passed in 0.2s", 0) == {}


def test_parsing_never_claims_a_pass():
    """A parser bug must not be able to turn a failure into a success."""
    f = ev.parse_failure("total gibberish with no recognisable structure", 1)
    assert f["exit_code"] == 1
    assert "passed" not in f


def test_raw_evidence_is_bounded():
    f = ev.parse_failure("x" * 50_000, 1)
    assert len(f["raw"]) <= ev.MAX_RAW_EVIDENCE


# ── semantic signatures ──────────────────────────────────────────────────────

def test_the_same_conceptual_failure_shares_a_signature():
    """Different code, same wrong idea — this is the case the repeat guard missed."""
    a = ev.parse_failure(PYTEST_FAIL, 1)
    b = ev.parse_failure(PYTEST_FAIL.replace("test_text_case.py:23", "test_text_case.py:41"), 1)
    assert ev.failure_signature(a) == ev.failure_signature(b)


def test_quoting_and_spacing_do_not_fork_a_signature():
    a = {"test": "t", "error_type": "AssertionError", "expected": "'a_b'", "actual": "'a  b'"}
    b = {"test": "t", "error_type": "AssertionError", "expected": "a_b", "actual": "'a b'"}
    assert ev.failure_signature(a) == ev.failure_signature(b)


def test_a_different_failure_gets_a_different_signature():
    a = ev.parse_failure(PYTEST_FAIL, 1)
    b = ev.parse_failure(PYTEST_FAIL.replace("parse_h_t_t_p_response", "PARSEHTTPRESPONSE"), 1)
    assert ev.failure_signature(a) != ev.failure_signature(b)


def test_unparseable_failures_are_distinguished_by_their_raw_text():
    a = ev.failure_signature(ev.parse_failure("segfault alpha", 2))
    b = ev.failure_signature(ev.parse_failure("segfault beta", 2))
    assert a and b and a != b, "two different errors must not collapse into one"


# ── the ledger ───────────────────────────────────────────────────────────────

def _ledger_with(n, output=PYTEST_FAIL):
    led = ev.AttemptLedger()
    for i in range(1, n + 1):
        a = led.open(i)
        a.approach = f"approach {i}"
        a.files_changed = ["backend/text_case.py"]
        led.close(passed=False, failure=ev.parse_failure(output, 1))
    return led


def test_two_identical_failures_are_stuck():
    assert _ledger_with(1).is_stuck() is False
    assert _ledger_with(2).is_stuck() is True


def test_differing_failures_are_not_stuck():
    led = ev.AttemptLedger()
    led.open(1); led.close(passed=False, failure=ev.parse_failure(PYTEST_FAIL, 1))
    led.open(2); led.close(passed=False, failure=ev.parse_failure(
        PYTEST_FAIL.replace("parse_h_t_t_p_response", "parsehttpresponse"), 1))
    assert led.is_stuck() is False


def test_the_briefing_names_the_failure_and_the_change():
    b = _ledger_with(2).briefing()
    assert "ATTEMPT 1" in b and "ATTEMPT 2" in b
    assert "parse_http_response" in b
    assert "backend/text_case.py" in b
    assert "STUCK" in b


def test_the_briefing_is_bounded():
    led = _ledger_with(3, output=PYTEST_FAIL + "x" * 40_000)
    assert len(led.briefing()) <= ev.MAX_BRIEFING_CHARS


def test_the_briefing_carries_no_model_reasoning():
    b = _ledger_with(2).briefing()
    for leaked in ("thinking", "chain of thought", "reasoning:"):
        assert leaked not in b.lower()


def test_evidence_export_drops_raw_but_keeps_the_signature():
    out = _ledger_with(2).to_evidence()
    assert len(out) == 2
    assert out[0]["signature"] and "raw" not in out[0]["failure"]


def test_strategy_advances_and_then_holds():
    assert ev.next_strategy("default") == "reconsider_approach"
    assert ev.next_strategy("reconsider_approach") == "decompose"
    assert ev.next_strategy("decompose") == "decompose"


# ── the runtime uses it ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_the_runtime_records_attempts_and_detects_stuck():
    probe = REPO_ROOT / "backend/tests/_evidence_fail_test.py"
    probe.write_text(
        'def test_consecutive():\n    assert "parse_h_t_t_p_response" == "parse_http_response"\n',
        encoding="utf-8", newline="")
    prompts = []

    async def driver(system, user, tools, execute):
        prompts.append(user)
        await execute("run_tests", {"target": "backend/tests/_evidence_fail_test.py"})

    try:
        audit = await rt.run_task("fix it", system_prompt="s", model_call=driver)
        assert audit["attempts"] == 3, "the 3-attempt bound is unchanged"
        assert audit["result"] == "failed_needs_human"
        assert audit["stuck"] is True, "identical failures must register as stuck"
        assert len(audit["attempt_log"]) == 3
        sigs = {a["signature"] for a in audit["attempt_log"]}
        assert len(sigs) == 1, "the same failure must share one signature"
        # the second attempt was told what the first did
        assert "ATTEMPT 1" in prompts[1]
        assert "parse_http_response" in prompts[1]
        # and by the third the strategy had changed
        assert audit["attempt_log"][2]["strategy"] != "default"
    finally:
        probe.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_lifecycle_states_are_recorded_in_order():
    async def driver(system, user, tools, execute):
        await execute("read_file", {"path": "backend/agent_guard.py"})

    audit = await rt.run_task("look", system_prompt="s", model_call=driver, max_attempts=1)
    seen = audit["states_seen"]
    assert seen[0] == rt.PLANNING
    assert rt.EXECUTING in seen and rt.VERIFYING in seen
    assert audit["state"] in (rt.FAILED, rt.HUMAN_REVIEW)
    assert all(s in rt.LIFECYCLE for s in seen)


@pytest.mark.asyncio
async def test_a_passing_task_ends_in_the_succeeded_state():
    probe = REPO_ROOT / "backend/tests/_evidence_pass_test.py"
    probe.write_text("def test_ok():\n    assert True\n", encoding="utf-8", newline="")

    async def driver(system, user, tools, execute):
        await execute("run_tests", {"target": "backend/tests/_evidence_pass_test.py"})

    try:
        audit = await rt.run_task("verify", system_prompt="s", model_call=driver)
        assert audit["result"] == rt.SUCCEEDED
        assert audit["state"] == rt.SUCCEEDED
        assert audit["stuck"] is False
        assert audit["attempts"] == 1
    finally:
        probe.unlink(missing_ok=True)


# ── codebase retrieval: unavailable is never empty ───────────────────────────

@pytest.mark.asyncio
async def test_retrieval_reports_unavailable_rather_than_no_results():
    out = json.loads(await agent_tools.execute_engineering_tool(
        "search_codebase", {"query": "how does the approval gate work"}))
    if out.get("error"):
        assert out["error"] in {"retrieval_unavailable", "provider_error"}
        assert "results" not in out and "count" not in out
        if out["error"] == "retrieval_unavailable":
            assert "chromadb" in out["detail"].lower()
    else:
        assert out["untrusted"] is True and "count" in out


@pytest.mark.asyncio
async def test_an_empty_retrieval_query_is_rejected():
    out = json.loads(await agent_tools.execute_engineering_tool(
        "search_codebase", {"query": "   "}))
    assert out["error"] == "bad_arguments"


def test_retrieval_status_is_honest_about_the_backend():
    st = kn.status()
    assert isinstance(st["retrieval_available"], bool)
    if not st["retrieval_available"]:
        assert st["detail"], "an unavailable backend must say why"


def test_retrieval_is_a_capability_not_an_approval():
    from agent_guard import classify, is_approval_gated

    assert classify("search_codebase") == "capability"
    assert not is_approval_gated("search_codebase")


def test_retrieval_is_registered_and_schema_matches():
    assert "search_codebase" in agent_tools.ENGINEERING_TOOLS
    named = {s["function"]["name"] for s in agent_tools.ENGINEERING_SCHEMAS}
    assert named == set(agent_tools.ENGINEERING_TOOLS)
