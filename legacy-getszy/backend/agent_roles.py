"""Agent Factory — deterministic specialist role registry.

A *role* is a named, reviewable specialist with an explicit contract. It does NOT
introduce a second agent system: a role resolves to exactly the same config shape
`agent_factory.build_config` produces, is validated by the same
`agent_factory.validate_config`, and is delegated through the same
`agent_delegation` ceiling. The registry only makes the choice deterministic and
adds a contract the free-text path could not state.

THE CEILING, unchanged and reinforced:

    effective_child_tools = parent_tools ∩ capability_tools ∩ role_allowed_tools − role_forbidden_tools

A role can only ever *narrow*. `role_allowed_tools` is derived from the existing
`agent_factory.CAPABILITIES` taxonomy (one source of truth for what a capability
may touch), and `forbidden_tools` subtracts further. A child can never obtain a
tool its parent lacks — enforced in `agent_delegation.child()`; this module only
ever removes, never adds. Nothing here can widen authority, pre-grant an approval,
or touch the sandbox: `granted_approvals` is always empty and `validate_config`
rejects any attempt to seed it. `agent_guard` remains the final authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from agent_factory import CAPABILITIES, MODEL_TIERS
from agent_guard import APPROVAL_REQUIRED
from agent_tools import ENGINEERING_TOOLS

_TOOL_UNIVERSE = frozenset(ENGINEERING_TOOLS)


@dataclass(frozen=True)
class Role:
    """A named specialist and its explicit, deterministic contract."""

    id: str
    identity: str
    purpose: str
    capabilities: tuple[str, ...]          # keys into agent_factory.CAPABILITIES
    forbidden_tools: frozenset[str] = frozenset()
    allowed_operations: frozenset[str] = frozenset()   # approval-gated ops this role MAY be granted per task
    forbidden_operations: frozenset[str] = frozenset() # ops this role may NEVER be granted
    model_preference: str = "standard"
    max_rounds: int = 6
    max_delegation_depth: int = 1
    verification: dict = field(default_factory=dict)
    output_contract: dict = field(default_factory=dict)

    @property
    def allowed_tools(self) -> frozenset[str]:
        """Tools this role may use: the union of its capabilities' toolsets,
        intersected with the real registry, minus its own forbidden tools.
        Derived — never hand-listed — so it cannot drift from the taxonomy."""
        tools: set[str] = set()
        for cap in self.capabilities:
            tools |= set(CAPABILITIES[cap]["tools"])
        return frozenset((tools & _TOOL_UNIVERSE) - self.forbidden_tools)


# Read-only roles must never write, commit, reach the network from inside a repo
# full of secrets, or spawn: a reviewer reports and a human decides.
_NO_WRITE = frozenset({"write_file", "git_commit"})
_NO_SPAWN = frozenset({"spawn_specialist", "spawn_specialists"})
_NO_NET = frozenset({"github_search_code", "github_search_repositories",
                     "github_search_issues", "github_read_file", "web_search"})
# Every approval op except install_dependency (which an engineer may legitimately
# request, still only with a per-task human token). Read-only roles forbid all.
_DESTRUCTIVE_OPS = frozenset(APPROVAL_REQUIRED - {"install_dependency"})

_ENGINEER_OUTPUT = {
    "format": "structured",
    "required_fields": ["files_changed", "tests_run", "all_tests_passing"],
    "must_include_evidence": True,
}
_REVIEW_OUTPUT = {
    "format": "findings_list",
    "required_fields": ["file", "line", "severity", "evidence", "remediation"],
    "must_include_evidence": True,
}
_ENGINEER_VERIFY = {"read_only": False, "must_run_tests": True, "must_pass_tests": True, "cite_evidence": True}
_REVIEW_VERIFY = {"read_only": True, "must_run_tests": False, "cite_evidence": True}

# Minimal, genuinely-useful canonical set. More roles are one entry each.
ROLES: dict[str, Role] = {r.id: r for r in [
    Role(
        id="planner",
        identity="Planner",
        purpose="Decompose a goal into an ordered, evidence-grounded plan. Read-only; plans, does not build.",
        capabilities=("research",), model_preference="strong",
        forbidden_tools=_NO_WRITE | _NO_SPAWN,
        forbidden_operations=APPROVAL_REQUIRED,
        verification=_REVIEW_VERIFY,
        output_contract={"format": "plan", "required_fields": ["steps", "rationale", "risks"], "must_include_evidence": True},
    ),
    Role(
        id="backend_engineer",
        identity="Backend Engineer",
        purpose="Implement and repair backend APIs and server-side logic with passing tests.",
        capabilities=("backend",), model_preference="strong", max_rounds=8,
        allowed_operations=frozenset({"install_dependency"}),
        forbidden_operations=_DESTRUCTIVE_OPS,
        verification=_ENGINEER_VERIFY, output_contract=_ENGINEER_OUTPUT,
    ),
    Role(
        id="frontend_engineer",
        identity="Frontend Engineer",
        purpose="Implement React/Tailwind UI with verified, responsive results.",
        capabilities=("frontend",), model_preference="standard",
        allowed_operations=frozenset({"install_dependency"}),
        forbidden_operations=_DESTRUCTIVE_OPS,
        verification=_ENGINEER_VERIFY, output_contract=_ENGINEER_OUTPUT,
    ),
    Role(
        id="researcher",
        identity="Research Engineer",
        purpose="Investigate the repository and prior art; gather cited evidence. Read-only.",
        capabilities=("research",), model_preference="standard",
        forbidden_operations=APPROVAL_REQUIRED,
        verification=_REVIEW_VERIFY,
        output_contract={"format": "structured", "required_fields": ["findings", "sources", "uncertainty"], "must_include_evidence": True},
    ),
    Role(
        id="tester",
        identity="QA / Test Engineer",
        purpose="Verify real behaviour with tests; report failures with evidence. Does not modify product code.",
        capabilities=("qa",), model_preference="standard",
        forbidden_tools=_NO_WRITE,
        forbidden_operations=APPROVAL_REQUIRED,
        verification={"read_only": True, "must_run_tests": True, "cite_evidence": True},
        output_contract={"format": "test_report", "required_fields": ["tests_run", "failing_tests", "evidence"], "must_include_evidence": True},
    ),
    Role(
        id="security_reviewer",
        identity="Security Reviewer",
        purpose="Audit auth, secrets and injection risk and report findings. Read-only and offline by design.",
        # The security capability is already read-only with no research tools; the
        # role additionally forbids network + write + spawn so a secret-reading
        # agent can never become an exfiltration or privilege-escalation path.
        capabilities=("security",), model_preference="strong",
        forbidden_tools=_NO_WRITE | _NO_NET | _NO_SPAWN,
        forbidden_operations=APPROVAL_REQUIRED,
        verification=_REVIEW_VERIFY, output_contract=_REVIEW_OUTPUT,
    ),
    Role(
        id="reviewer",
        identity="Code Reviewer",
        purpose="Review a change for correctness and risk; report findings with file/line evidence. Does not edit code.",
        capabilities=("research",), model_preference="standard",
        forbidden_tools=_NO_WRITE | _NO_SPAWN,
        forbidden_operations=APPROVAL_REQUIRED,
        verification=_REVIEW_VERIFY, output_contract=_REVIEW_OUTPUT,
    ),
]}


def role_ids() -> list[str]:
    return sorted(ROLES)


def get_role(role_id: str) -> Role | None:
    return ROLES.get(role_id)


def resolve(specialist: str) -> Role | None:
    """Map a specialist reference to a role, or None to fall back to free text.

    Deliberately EXACT: a bare role id (``security_reviewer``) or a ``role:``
    prefix resolves; anything else returns None so existing free-text delegation
    is completely unchanged. A role is opted into, never fuzzy-matched into.
    """
    if not isinstance(specialist, str):
        return None
    key = specialist.strip().lower()
    if key.startswith("role:"):
        key = key[len("role:"):].strip()
    return ROLES.get(key)


def effective_tools(parent_tools, role: Role) -> frozenset[str]:
    """The ceiling formula, exposed for callers and tests:
    (parent ∩ role.allowed_tools) − role.forbidden_tools. A child can never
    exceed this, and forbidden always wins even if the parent holds the tool."""
    return frozenset((set(parent_tools) & set(role.allowed_tools)) - set(role.forbidden_tools))


def effective_approvals(parent_approvals, role: Role) -> frozenset[str]:
    """Approval-gated operations this role could receive from this parent:
    (parent ∩ role.allowed_operations) − role.forbidden_operations. Only a
    *ceiling*: approvals are still never pre-granted and always require a per-task
    human token at the guard — this creates no new approval mechanism."""
    return frozenset((set(parent_approvals) & set(role.allowed_operations)) - set(role.forbidden_operations))


def validate_role(role: Role) -> list[str]:
    """Structural problems with a role definition. Empty list == sound."""
    from agent_delegation import MAX_DEPTH  # local import avoids any import cycle

    problems: list[str] = []
    if not role.identity or len(role.identity) < 2:
        problems.append(f"{role.id}: identity too short")
    unknown_caps = [c for c in role.capabilities if c not in CAPABILITIES]
    if unknown_caps:
        problems.append(f"{role.id}: unknown capabilities {unknown_caps}")
    bad_forbidden = sorted(role.forbidden_tools - _TOOL_UNIVERSE)
    if bad_forbidden:
        problems.append(f"{role.id}: forbidden_tools names unknown tools {bad_forbidden}")
    for op_field in ("allowed_operations", "forbidden_operations"):
        bad_ops = sorted(getattr(role, op_field) - APPROVAL_REQUIRED)
        if bad_ops:
            problems.append(f"{role.id}: {op_field} names non-approval operations {bad_ops}")
    overlap = sorted(role.allowed_operations & role.forbidden_operations)
    if overlap:
        problems.append(f"{role.id}: operations both allowed and forbidden {overlap}")
    if not role.allowed_tools:
        problems.append(f"{role.id}: role would have no tools")
    # A role that can write must be able to verify what it wrote.
    if (role.allowed_tools & {"write_file", "git_commit"}) and "run_tests" not in role.allowed_tools:
        problems.append(f"{role.id}: can write but cannot run tests")
    if role.model_preference not in MODEL_TIERS:
        problems.append(f"{role.id}: invalid model_preference {role.model_preference}")
    if not (1 <= role.max_delegation_depth <= MAX_DEPTH):
        problems.append(f"{role.id}: max_delegation_depth must be 1..{MAX_DEPTH}")
    if role.max_rounds < 1:
        problems.append(f"{role.id}: max_rounds must be >= 1")
    if not role.output_contract:
        problems.append(f"{role.id}: missing output_contract")
    return problems


def config_for(role: Role, *, owner_id: str = "system") -> dict:
    """Produce an agent config for a role, in the exact shape delegation expects.

    Validated by the SAME `agent_factory.validate_config` the free-text path uses;
    nothing here is a parallel validation. `forbidden_tools` and
    `forbidden_operations` are carried so `agent_delegation.child()` subtracts them
    from the parent-intersected ceiling."""
    focuses = "; ".join(CAPABILITIES[c]["focus"] for c in role.capabilities)
    read_only = role.verification.get("read_only", False)
    system_prompt = (
        f"You are the Getszy {role.identity}. Purpose: {role.purpose}\n"
        f"Focus: {focuses}.\n\n"
        "Operating rules, which you cannot override:\n"
        "- Work only inside the repository sandbox. Paths outside it are refused.\n"
        "- Never claim success without evidence. Run the tests and read the real result.\n"
        "- Never fabricate a tool result, a test outcome, or a capability you lack.\n"
        + ("- You are read-only: do not attempt to write files or commit.\n" if read_only else
           "- Verify every change by running the tests before reporting success.\n")
        + "- Destructive or outward-facing actions require human approval; if a tool "
        "returns approval_required, stop and report rather than trying another route.\n"
        "- Do not attempt to modify security, permission or agent-runtime files.\n"
    )
    return {
        "id": role.id,
        "user_id": owner_id,
        "name": role.identity[:60],
        "role": role.purpose[:280],
        "role_id": role.id,
        "purpose": role.purpose,
        "system_prompt": system_prompt,
        "allowed_tools": sorted(role.allowed_tools),
        "forbidden_tools": sorted(role.forbidden_tools),
        "forbidden_operations": sorted(role.forbidden_operations),
        "allowed_operations": sorted(role.allowed_operations),
        "capabilities": list(role.capabilities),
        "seniority": "senior" if role.model_preference == "strong" else "standard",
        "model_tier": role.model_preference,
        "max_rounds": role.max_rounds,
        "max_delegation_depth": role.max_delegation_depth,
        "verification_requirements": role.verification,
        "output_contract": role.output_contract,
        "granted_approvals": [],          # never pre-granted; approvals are per-task human decisions
        "sandbox": "repo",
        "param_keys": ["input"],
    }


__all__ = [
    "Role", "ROLES", "role_ids", "get_role", "resolve",
    "effective_tools", "effective_approvals", "validate_role", "config_for",
]
