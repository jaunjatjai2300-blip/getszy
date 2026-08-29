"""Structured spec / decomposition / convergence — the Spec Kit pattern, native.

Proves the spec layer adds an explicit objective/acceptance-criteria/dependency
contract WITHOUT granting authority and WITHOUT trusting 'done': convergence is
decided only from real evidence, unverifiable criteria go to a human, and a
repeated failure signature is flagged as non-progress with a strategy change.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("JWT_SECRET", "test-only-agent-spec-secret-32chars!!!")

import agent_spec as sp  # noqa: E402
import agent_roles as roles  # noqa: E402
import agent_guard  # noqa: E402

FAIL_EV = {"tests": [{"passed": False, "output_tail": "E assert parse_h_t_t_p != parse_http", "exit_code": 1}],
           "files_changed": [], "verification": {"verified": False}, "status": "failed"}
PASS_EV = {"tests": [{"passed": True}], "files_changed": ["auth.py"],
           "verification": {"verified": True}, "status": "verified", "result": "verified"}


# ── build_spec: an explicit contract, role-assigned ──────────────────────────

def test_build_spec_has_a_full_contract():
    spec = sp.build_spec("implement the login API and fix the token bug")
    assert spec.objective and spec.id.startswith("task-")
    assert spec.assigned_role == "backend_engineer"
    assert spec.acceptance_criteria and spec.allowed_tools
    # tools come from the role and are a subset of the role's tools (a request only)
    assert spec.allowed_tools == roles.get_role("backend_engineer").allowed_tools


def test_role_assignment_is_deterministic_and_sane():
    assert sp.build_spec("audit auth for injection and secrets").assigned_role == "security_reviewer"
    assert sp.build_spec("write tests and verify regression coverage").assigned_role == "tester"
    assert sp.build_spec("build a responsive react landing page").assigned_role == "frontend_engineer"
    assert sp.build_spec("investigate how the cache works").assigned_role == "researcher"
    # unclear intent falls back to a READ-ONLY role, never a write-capable one
    assert sp.build_spec("do the needful").assigned_role == "researcher"


def test_author_task_mentioning_tests_gets_a_write_capable_role():
    """Regression: a task to CREATE/IMPLEMENT a source file that also names a test
    file for verification must be assigned an engineer WITH write_file — never the
    verify-only tester role. The tester has run_tests but no write_file, so it
    could not author the deliverable and looped on reads until it ran out of rounds
    (observed on a real 14B model in the spec E2E). The precedence is narrow: a
    task whose deliverable is the tests themselves stays with tester."""
    for req in (
        "Create backend/spec_demo.py with a function to_snake_case so backend/tests/test_spec_demo.py passes",
        "implement backend/util.py so that tests/test_util.py passes",
        "add a to_snake_case function in backend/text.py and make its unit tests pass",
    ):
        spec = sp.build_spec(req)
        assert spec.assigned_role == "backend_engineer", req
        assert "write_file" in spec.allowed_tools, req      # can actually produce the file
    # deliverable-is-the-tests still routes to the verify-only tester (unchanged)
    assert sp.build_spec("write tests and verify regression coverage").assigned_role == "tester"


def test_decomposed_followon_step_is_self_contained():
    """Regression: a decomposed follow-on step is a FRESH delegation with no memory
    of the prior step, so 'run that test target to confirm' must carry the prior
    step's objective (its referent) into the briefing — otherwise the specialist
    cannot know what 'that' is and loops."""
    specs = sp.decompose(
        "Create backend/spec_demo.py so backend/tests/test_spec_demo.py passes; "
        "run ONLY that test target to confirm")
    assert len(specs) == 2
    follow = specs[1].briefing()
    assert "test_spec_demo.py" in follow                     # the referent is now present
    assert "earlier step" in follow                          # explicitly framed as a continuation
    # the first (authoring) step is a writer; the confirm step needs no write
    assert "write_file" in specs[0].allowed_tools
    assert "write_file" not in specs[1].allowed_tools


# ── decomposition + dependency ordering ──────────────────────────────────────

def test_simple_request_stays_one_spec():
    specs = sp.decompose("fix the failing login test")
    assert len(specs) == 1 and not specs[0].dependencies


def test_compound_request_decomposes_in_order():
    specs = sp.decompose("implement the /orders endpoint; then write tests for it; then review the diff")
    assert len(specs) == 3
    # linear dependency chain
    assert specs[1].dependencies == [specs[0].id]
    assert specs[2].dependencies == [specs[1].id]
    ordered = sp.topological_order(specs)
    assert [s.id for s in ordered] == [s.id for s in specs]


def test_topological_order_detects_cycles():
    a = sp.build_spec("a", index=0)
    b = sp.build_spec("b", index=1, dependencies=[a.id])
    a.dependencies = [b.id]  # cycle
    with pytest.raises(ValueError):
        sp.topological_order([a, b])


# ── convergence: only real evidence, never 'done' ────────────────────────────

def test_converge_true_only_with_real_passing_evidence():
    spec = sp.build_spec("implement the login API")   # backend -> tests_pass/verified/files_changed
    rep = sp.converge(spec, PASS_EV)
    assert rep.converged is True and not rep.unmet


def test_converge_false_on_failure_with_remaining_work():
    spec = sp.build_spec("implement the login API")
    rep = sp.converge(spec, FAIL_EV)
    assert rep.converged is False
    assert rep.unmet and rep.remaining_work
    assert rep.signature   # a stable failure identity was captured


def test_empty_evidence_never_converges():
    spec = sp.build_spec("implement the login API")
    assert sp.converge(spec, {}).converged is False       # no evidence == not done


def test_manual_criteria_never_auto_pass():
    # a research spec carries a 'manual' criterion -> needs a human, never converged
    spec = sp.build_spec("investigate the delegation flow")
    rep = sp.converge(spec, {"failures": []})
    assert rep.converged is False and rep.needs_human


def test_repeated_failure_is_non_progress_and_changes_strategy():
    spec = sp.build_spec("fix the parser")
    first = sp.converge(spec, FAIL_EV)
    again = sp.converge(spec, FAIL_EV, prior_signatures=[first.signature])
    assert again.progressed is False
    assert again.recommended_strategy and again.recommended_strategy != "default"


# ── security: a spec grants NOTHING ──────────────────────────────────────────

def test_spec_carries_no_write_or_network_for_a_readonly_role():
    spec = sp.build_spec("audit auth for secrets")   # -> security_reviewer (read-only, offline)
    assert not (spec.allowed_tools & {"write_file", "git_commit"})
    assert not (spec.allowed_tools & {"web_search", "github_read_file"})


def test_to_delegation_request_only_requests_never_grants():
    spec = sp.build_spec("investigate the cache")
    req = sp.to_delegation_request(spec)
    # it names the role and passes the spec's tools as a REQUEST that delegation
    # will intersect with the parent ceiling — it cannot widen authority.
    assert req["specialist"] == spec.assigned_role
    assert set(req["tools"] or []) <= set(spec.allowed_tools)
    assert "task" in req and spec.objective in req["task"]


def test_spec_registry_is_self_protected():
    assert "backend/agent_spec.py" in agent_guard.SELF_PROTECTED
