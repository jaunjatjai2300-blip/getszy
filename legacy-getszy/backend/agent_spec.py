"""Agent Factory — structured task specification, decomposition & convergence.

The pattern adopted from GitHub Spec Kit (specify → plan → tasks → converge),
reimplemented NATIVELY on the existing Factory contracts. It adds the one layer
the Factory lacked: a request was handed to delegation as free text, with no
explicit objective / acceptance criteria / dependency order / convergence check.

What this is NOT:
  * not a second task engine — a spec RESOLVES to the existing agent_delegation
    call; execution, ceilings and the guard are unchanged.
  * not a permission mechanism — a spec grants NOTHING. `allowed_tools` on a spec
    is only a *request*, intersected down by the delegation ceiling; a spec can
    never widen authority. Specs are data, never grants.
  * not a replacement for verification — convergence complements test-driven
    repair; it never treats "done" as success. A criterion is met only from
    real evidence (tests actually passed, files actually changed, verified flag),
    and unverifiable criteria are surfaced for a human, never auto-passed.

Reuses: agent_roles (assignment + tools + contract), agent_evidence (failure
signatures + next-strategy for non-progress detection). agent_guard remains the
final authority.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

import agent_roles

# Machine-checkable acceptance-criterion kinds. Anything else is "manual" and is
# never auto-passed — it is surfaced for a human, so "done" is never trusted.
CHECK_TESTS_PASS = "tests_pass"
CHECK_VERIFIED = "verified"
CHECK_FILES_CHANGED = "files_changed"
CHECK_NO_ERRORS = "no_tool_errors"
CHECK_MANUAL = "manual"
_MACHINE_CHECKS = {CHECK_TESTS_PASS, CHECK_VERIFIED, CHECK_FILES_CHANGED, CHECK_NO_ERRORS}


@dataclass
class TaskSpec:
    """One unit of work with an explicit, reviewable contract."""
    id: str
    objective: str
    requirements: list = field(default_factory=list)
    acceptance_criteria: list = field(default_factory=list)  # list of {check, desc}
    dependencies: list = field(default_factory=list)         # ids of prerequisite specs
    constraints: list = field(default_factory=list)
    assigned_role: str | None = None
    allowed_tools: frozenset = frozenset()                   # a REQUEST, ceiled by delegation
    verification: dict = field(default_factory=dict)
    output_contract: dict = field(default_factory=dict)
    resource_limits: dict = field(default_factory=dict)

    def briefing(self) -> str:
        """A compact task briefing for the specialist — objective + what 'done'
        actually means. Carries no capability, only intent (the guard/ceiling
        still decide what the specialist may do)."""
        lines = [self.objective]
        if self.requirements:
            lines += ["", "Requirements:"] + [f"- {r}" for r in self.requirements]
        if self.constraints:
            lines += ["", "Constraints:"] + [f"- {c}" for c in self.constraints]
        crit = [c.get("desc", c.get("check")) for c in self.acceptance_criteria]
        if crit:
            lines += ["", "Acceptance criteria (all must be met with real evidence):"] + [f"- {c}" for c in crit]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "objective": self.objective, "requirements": self.requirements,
            "acceptance_criteria": self.acceptance_criteria, "dependencies": self.dependencies,
            "constraints": self.constraints, "assigned_role": self.assigned_role,
            "allowed_tools": sorted(self.allowed_tools), "verification": self.verification,
            "output_contract": self.output_contract, "resource_limits": self.resource_limits,
        }


def _spec_id(text: str, n: int = 0) -> str:
    digest = hashlib.sha256(f"{n}:{text.strip().lower()}".encode("utf-8")).hexdigest()
    return f"task-{digest[:12]}"


def _pick_role(objective: str) -> str:
    """Deterministically assign a specialist role from the objective. Falls back
    to a safe read-only researcher when the intent is unclear (never a
    write-capable role by default).

    AUTHORING PRECEDENCE (wiring correctness): creating or implementing a source
    artifact REQUIRES write_file, and only the engineer roles hold it. Such a task
    must never be routed to a verify-only role — the tester role has run_tests but
    NO write_file — merely because the objective also names a test file for
    verification. That mis-assignment hands the specialist a toolset that cannot
    produce the deliverable, so it loops reading the same files until it runs out
    of rounds (observed on a real 14B model in the spec E2E). So an
    author-of-implementation objective is matched to an engineer BEFORE the generic
    keyword signals. A task whose deliverable is the TESTS themselves ("write tests
    and verify coverage") names no non-test code artifact here and still resolves
    to tester in the signal table below — the precedence is deliberately narrow."""
    exact = agent_roles.resolve(objective)
    if exact is not None:
        return exact.id
    text = objective.lower()

    _AUTHOR_VERB = ("create", "implement", "build ", "make ", "generate", "refactor", "add ")
    _CODE_ARTIFACT = (".py", ".ts", ".tsx", ".js", "function", "module", "class ",
                      "endpoint", "route", "api ", "backend", "frontend",
                      "server", "database")
    _UI = ("frontend", "react", "css", " ui", "component", "tailwind", ".tsx", ".jsx")
    if any(v in text for v in _AUTHOR_VERB) and any(a in text for a in _CODE_ARTIFACT):
        return "frontend_engineer" if any(u in text for u in _UI) else "backend_engineer"

    signals = [
        ("security_reviewer", ("security", "vulnerab", "auth", "secret", "injection", "xss")),
        ("tester", ("test", "qa", "regression", "verify behaviour", "coverage")),
        ("reviewer", ("review", "audit the", "assess", "inspect the change")),
        ("frontend_engineer", ("frontend", "react", "css", "ui", "component", "tailwind", "page")),
        ("backend_engineer", ("backend", "api", "endpoint", "route", "server", "database", "python", "implement", "fix", "build")),
        ("researcher", ("research", "investigate", "find out", "explore", "compare")),
        ("planner", ("plan", "decompose", "design the approach", "outline")),
    ]
    for role_id, kws in signals:
        if any(k in text for k in kws):
            return role_id
    return "researcher"


def _criteria_for_role(role) -> list:
    """Default, honest acceptance criteria derived from the role's verification
    contract. Write roles must produce passing tests; read-only roles produce a
    report that a human confirms — never auto-passed."""
    v = role.verification if role else {}
    if v.get("must_run_tests") and not v.get("read_only", False) is True and v.get("must_pass_tests"):
        return [
            {"check": CHECK_TESTS_PASS, "desc": "The test suite runs and passes."},
            {"check": CHECK_VERIFIED, "desc": "The change is verified by real test evidence."},
            {"check": CHECK_FILES_CHANGED, "desc": "The intended files were actually changed."},
        ]
    if v.get("must_run_tests"):
        return [
            {"check": CHECK_TESTS_PASS, "desc": "The tests were run and the result reported."},
            {"check": CHECK_NO_ERRORS, "desc": "No tool call failed unrecovered."},
        ]
    # read-only / review / research roles: output is a report, human-confirmed
    return [
        {"check": CHECK_NO_ERRORS, "desc": "The investigation ran without tool failures."},
        {"check": CHECK_MANUAL, "desc": "A human confirms the report meets the objective."},
    ]


def build_spec(request: str, *, index: int = 0, dependencies: list | None = None,
               role_id: str | None = None, prior_step: str | None = None) -> TaskSpec:
    """Turn one request into a structured, reviewable TaskSpec. Deterministic.

    `prior_step` carries the PRECEDING step's objective in a decomposed plan so a
    follow-on step ("run that test target to confirm", "review the change") is
    self-contained. Each delegation is a fresh specialist with no memory of the
    sibling steps, so a dangling reference ("it"/"that") would otherwise leave the
    specialist guessing and looping — the same class of failure as an unusable
    toolset, just at the task-context layer."""
    objective = (request or "").strip()
    rid = role_id or _pick_role(objective)
    role = agent_roles.get_role(rid)
    constraints = []
    if prior_step and prior_step.strip():
        constraints.append(
            f'This step follows an earlier step in the same plan: "{prior_step.strip()}". '
            'Resolve any reference like "it", "that", or "the change" to that step.'
        )
    return TaskSpec(
        id=_spec_id(objective, index),
        objective=objective,
        acceptance_criteria=_criteria_for_role(role),
        dependencies=list(dependencies or []),
        constraints=constraints,
        assigned_role=rid,
        allowed_tools=(role.allowed_tools if role else frozenset()),
        verification=(role.verification if role else {}),
        output_contract=(role.output_contract if role else {}),
    )


# ── decomposition (dependency-ordered) ───────────────────────────────────────

_SPLIT = re.compile(r"""\s*(?:\bthen\b|;|(?<!\d)\.\s+(?=[A-Z])|\n\s*\d+[.)]\s*|\n\s*[-*]\s*)\s*""",
                    re.IGNORECASE)


def decompose(request: str) -> list[TaskSpec]:
    """Split a compound request into ordered TaskSpecs with linear dependencies.

    Deterministic and conservative: it only splits on explicit sequence markers
    ('then', ';', numbered/bulleted steps, sentence boundaries). A simple request
    stays a single spec — it never invents work the user did not ask for. Each
    step depends on the previous one, so `topological_order` runs them in order."""
    request = (request or "").strip()
    parts = [p.strip() for p in _SPLIT.split(request) if p and p.strip()]
    if len(parts) <= 1:
        return [build_spec(request)]
    specs: list[TaskSpec] = []
    prev_id: str | None = None
    prev_part: str | None = None
    for i, part in enumerate(parts):
        deps = [prev_id] if prev_id else []
        spec = build_spec(part, index=i, dependencies=deps, prior_step=prev_part)
        specs.append(spec)
        prev_id = spec.id
        prev_part = part
    return specs


def topological_order(specs: list[TaskSpec]) -> list[TaskSpec]:
    """Order specs so every dependency comes first. Raises on a dependency cycle
    (an unschedulable plan is a real error, not a silent partial run)."""
    by_id = {s.id: s for s in specs}
    ordered: list[TaskSpec] = []
    state: dict[str, int] = {}  # 0=visiting, 1=done

    def visit(sid: str, stack: tuple):
        if state.get(sid) == 1:
            return
        if state.get(sid) == 0:
            raise ValueError(f"Dependency cycle detected at {sid}: {' -> '.join(stack + (sid,))}")
        if sid not in by_id:
            return  # external/unknown dependency is ignored, not fatal
        state[sid] = 0
        for dep in by_id[sid].dependencies:
            visit(dep, stack + (sid,))
        state[sid] = 1
        ordered.append(by_id[sid])

    for s in specs:
        visit(s.id, ())
    return ordered


# ── delegation handoff (reuses agent_delegation; adds no execution path) ──────

def to_delegation_request(spec: TaskSpec) -> dict:
    """Args for `agent_delegation.delegate` — the spec's assigned role and its
    briefing. `tools` is the spec's requested set, which delegation intersects
    with the parent ceiling; the spec cannot widen authority."""
    return {
        "specialist": spec.assigned_role or spec.objective,
        "task": spec.briefing(),
        "tools": sorted(spec.allowed_tools) or None,
    }


# ── convergence (complements test-driven repair; never trusts 'done') ────────

@dataclass
class ConvergenceReport:
    converged: bool
    progressed: bool
    met: list = field(default_factory=list)
    unmet: list = field(default_factory=list)
    needs_human: list = field(default_factory=list)
    remaining_work: list = field(default_factory=list)
    recommended_strategy: str | None = None
    signature: str = ""

    def to_dict(self) -> dict:
        return {
            "converged": self.converged, "progressed": self.progressed,
            "met": self.met, "unmet": self.unmet, "needs_human": self.needs_human,
            "remaining_work": self.remaining_work,
            "recommended_strategy": self.recommended_strategy, "signature": self.signature,
        }


def _last_test_passed(evidence: dict) -> bool | None:
    tests = evidence.get("tests") or []
    if not tests:
        return None
    return bool(tests[-1].get("passed"))


def _evidence_signature(evidence: dict) -> str:
    """A stable identity for the current failure, reusing agent_evidence so
    convergence and the repair loop agree on what 'the same failure' means."""
    from agent_evidence import failure_signature, parse_failure
    tests = evidence.get("tests") or []
    if tests and not tests[-1].get("passed"):
        last = tests[-1]
        failure = parse_failure(last.get("output_tail") or last.get("output") or "",
                                last.get("exit_code") or 1)
        return failure_signature(failure)
    failures = evidence.get("failures") or []
    if failures:
        return hashlib.sha256(str(failures[-1]).encode("utf-8")).hexdigest()[:16]
    return ""


def converge(spec: TaskSpec, evidence: dict, *, prior_signatures: list | None = None) -> ConvergenceReport:
    """Check evidence against the spec's acceptance criteria.

    Machine-checkable criteria are decided ONLY from real evidence; unverifiable
    ('manual') criteria are surfaced for a human and never auto-passed. Repeating
    the same failure signature is flagged as non-progress and a different strategy
    is recommended, so retries cannot burn out repeating one dead end."""
    from agent_evidence import next_strategy

    evidence = evidence or {}
    verified = bool(evidence.get("verification", {}).get("verified")) or evidence.get("status") == "verified" or evidence.get("result") == "verified"
    tests_passed = _last_test_passed(evidence)
    files_changed = bool(evidence.get("files_changed"))
    tool_errors = bool(evidence.get("failures"))

    met, unmet, needs_human, remaining = [], [], [], []
    for crit in spec.acceptance_criteria:
        kind = crit.get("check")
        desc = crit.get("desc", kind)
        if kind == CHECK_TESTS_PASS:
            (met if tests_passed else unmet).append(desc)
            if not tests_passed:
                remaining.append("Make the tests actually run and pass.")
        elif kind == CHECK_VERIFIED:
            (met if verified else unmet).append(desc)
            if not verified:
                remaining.append("Produce real passing-test evidence for the change.")
        elif kind == CHECK_FILES_CHANGED:
            (met if files_changed else unmet).append(desc)
            if not files_changed:
                remaining.append("No file was changed yet — implement, then verify.")
        elif kind == CHECK_NO_ERRORS:
            (met if not tool_errors else unmet).append(desc)
        else:  # manual / unknown — never auto-pass
            needs_human.append(desc)

    signature = _evidence_signature(evidence)
    prior = list(prior_signatures or [])
    progressed = not (signature and signature in prior)
    converged = (not unmet) and all(c.get("check") in _MACHINE_CHECKS for c in spec.acceptance_criteria)

    recommended = None
    if not converged and not progressed:
        recommended = next_strategy("default")  # same failure again -> change approach

    return ConvergenceReport(
        converged=converged, progressed=progressed, met=met, unmet=unmet,
        needs_human=needs_human, remaining_work=remaining,
        recommended_strategy=recommended, signature=signature,
    )


__all__ = [
    "TaskSpec", "ConvergenceReport", "build_spec", "decompose", "topological_order",
    "to_delegation_request", "converge",
    "CHECK_TESTS_PASS", "CHECK_VERIFIED", "CHECK_FILES_CHANGED", "CHECK_NO_ERRORS", "CHECK_MANUAL",
]
