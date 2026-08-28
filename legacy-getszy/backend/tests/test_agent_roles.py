"""Specialist Role Registry: deterministic roles that only ever narrow.

Roles add a named, reviewable contract on top of the existing delegation ceiling.
These tests prove the additions never widen authority: forbidden tools are
removed even when the parent holds them, tiers only fall, a role's config passes
the SAME validation as free text, approvals are never pre-granted, and the
read-only security role can neither write, reach the network, nor spawn.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("JWT_SECRET", "test-only-agent-roles-secret-32chars!!")

import agent_roles as roles  # noqa: E402
import agent_delegation as dg  # noqa: E402
import agent_factory  # noqa: E402
import agent_guard  # noqa: E402
import agent_tools  # noqa: E402

FULL = frozenset(agent_tools.ENGINEERING_TOOLS)
WRITE = {"write_file", "git_commit"}
NET = {"github_search_code", "github_search_repositories", "github_search_issues",
       "github_read_file", "web_search"}
SPAWN = {"spawn_specialist", "spawn_specialists"}


def ctx(**kw):
    kw.setdefault("task_id", "task-roles")
    kw.setdefault("tools", FULL)
    return dg.master_context(**kw)


def recorder():
    seen = {}

    def factory(tier):
        async def call(system, user, tools, execute):
            seen["offered"] = sorted(s["function"]["name"] for s in tools)
        return call
    return seen, factory


# ── unit: every role is well-formed and passes the shared validation ─────────

def test_registry_holds_the_canonical_minimal_set():
    assert set(roles.role_ids()) == {
        "planner", "backend_engineer", "frontend_engineer",
        "researcher", "tester", "security_reviewer", "reviewer",
    }


@pytest.mark.parametrize("rid", roles.role_ids())
def test_role_definition_is_sound(rid):
    role = roles.get_role(rid)
    assert roles.validate_role(role) == []
    assert role.output_contract, "every role must state an output contract"
    assert role.allowed_tools <= FULL


@pytest.mark.parametrize("rid", roles.role_ids())
def test_role_config_passes_factory_validation(rid):
    cfg = roles.config_for(roles.get_role(rid))
    # The SAME validator the free-text factory uses — no parallel path.
    assert agent_factory.validate_config(cfg) == []
    assert cfg["granted_approvals"] == []      # approvals are NEVER pre-granted
    assert cfg["sandbox"] == "repo"


@pytest.mark.parametrize("rid", roles.role_ids())
def test_write_capable_role_can_also_verify(rid):
    role = roles.get_role(rid)
    if role.allowed_tools & WRITE:
        assert "run_tests" in role.allowed_tools


# ── resolution is exact, never fuzzy ─────────────────────────────────────────

def test_resolve_matches_exact_id_and_prefix_only():
    assert roles.resolve("security_reviewer") is roles.get_role("security_reviewer")
    assert roles.resolve("role:tester") is roles.get_role("tester")
    assert roles.resolve("  BACKEND_ENGINEER  ") is roles.get_role("backend_engineer")


def test_resolve_leaves_free_text_delegation_untouched():
    # The exact strings the existing delegation tests use must NOT become roles.
    assert roles.resolve("Senior Python backend engineer who writes modules and runs pytest.") is None
    assert roles.resolve("Security reviewer for auth, secrets and injection vulnerabilities.") is None
    assert roles.resolve("Research engineer to investigate and audit prior art.") is None
    assert roles.resolve("") is None
    assert roles.resolve(None) is None


# ── security: the read-only security role cannot write, exfiltrate, or spawn ──

def test_security_reviewer_is_read_only_and_offline():
    role = roles.get_role("security_reviewer")
    assert not (role.allowed_tools & WRITE)
    assert not (role.allowed_tools & NET)
    assert not (role.allowed_tools & SPAWN)
    assert "read_file" in role.allowed_tools and "run_tests" in role.allowed_tools


# ── the ceiling formula, forbidden-always-wins, and no escalation ────────────

def test_effective_tools_never_exceeds_parent():
    role = roles.get_role("backend_engineer")
    parent = frozenset({"read_file", "run_tests"})
    eff = roles.effective_tools(parent, role)
    assert eff <= parent
    assert eff == (parent & role.allowed_tools)


def test_forbidden_tool_is_stripped_even_when_parent_holds_it():
    # Parent HAS write_file; the tester role forbids it. The child must not get it.
    role = roles.get_role("tester")
    parent = ctx(tools=FULL)
    child = parent.child(roles.config_for(role))
    assert "write_file" not in child.tools and "git_commit" not in child.tools
    assert set(child.tools) <= set(parent.tools)


def test_role_cannot_grant_a_tool_the_parent_lacks():
    # backend_engineer wants write_file, but the parent does not hold it.
    role = roles.get_role("backend_engineer")
    parent = ctx(tools=frozenset({"read_file", "run_tests"}))
    child = parent.child(roles.config_for(role))
    assert "write_file" not in child.tools
    assert set(child.tools) <= {"read_file", "run_tests"}


def test_explicit_request_for_a_role_forbidden_tool_is_refused():
    role = roles.get_role("tester")     # forbids write_file
    parent = ctx(tools=FULL)            # parent DOES hold write_file
    with pytest.raises(dg.DelegationDenied) as e:
        parent.child(roles.config_for(role), requested_tools=["read_file", "write_file"])
    assert "forbidden for this role" in str(e.value)


def test_over_scope_request_is_refused_not_trimmed():
    role = roles.get_role("backend_engineer")   # allows write_file, but...
    parent = ctx(tools=frozenset({"read_file", "run_tests"}))  # ...parent lacks it
    with pytest.raises(dg.DelegationDenied) as e:
        parent.child(roles.config_for(role), requested_tools=["read_file", "write_file"])
    assert "outside the parent's scope" in str(e.value)


# ── model-tier ceiling: a role preference never climbs above the parent ──────

def test_role_model_tier_never_exceeds_parent():
    role = roles.get_role("backend_engineer")   # prefers "strong"
    child = ctx(tools=FULL, model_tier="light").child(roles.config_for(role))
    assert child.model_tier == "light"          # clamped down to the parent's tier


# ── approvals: a role's forbidden operation can never be granted ─────────────

def test_role_forbidden_operation_can_never_be_granted():
    role = roles.get_role("security_reviewer")  # forbids git_push (all ops)
    parent = ctx(tools=FULL, approvals={"git_push"}, delegable={"git_push"})
    with pytest.raises(dg.DelegationDenied) as e:
        parent.child(roles.config_for(role), requested_approvals=["git_push"])
    assert "forbidden for this role" in str(e.value)


# ── the registry itself is a protected control file ──────────────────────────

def test_role_registry_is_self_protected():
    assert "backend/agent_roles.py" in agent_guard.SELF_PROTECTED


# ── integration: the real delegation path resolves and ceils a role ──────────

async def test_delegate_resolves_named_role_and_offers_only_role_tools():
    seen, factory = recorder()
    out = await dg.delegate(specialist="security_reviewer", task="audit auth",
                            context=ctx(model_factory=factory))
    offered = set(seen["offered"])
    assert not (offered & WRITE) and not (offered & NET) and not (offered & SPAWN)
    assert "read_file" in offered
    assert set(out["specialist"]["tool_scope"]) == offered


async def test_delegate_role_is_intersected_with_a_narrow_parent():
    seen, factory = recorder()
    out = await dg.delegate(specialist="researcher", task="investigate",
                            context=ctx(tools=frozenset({"read_file"}), model_factory=factory))
    assert seen["offered"] == ["read_file"]
    assert out["specialist"]["tool_scope"] == ["read_file"]
