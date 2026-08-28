"""Agent Factory — master runtime.

Drives the engineering tool loop (agent_llm, which reuses llm_provider's
provider transports with the ENGINEERING registry) and adds the four things the
spec requires:

  1. the engineering toolset (agent_tools) instead of the commerce toolset
  2. a bounded repair loop — max 3 autonomous attempts, then stop for a human
  3. an approval gate carried through every tool call (agent_guard)
  4. an audit trail of operational evidence

Deliberately NOT stored in the audit: model reasoning / chain-of-thought. The
record holds requests, actions, results, failures and approvals — what was done
and what happened — not what the model was thinking.

Nothing here simulates a model. If no provider is reachable the run FAILS with
`no_model_available`; it never returns a plausible-looking fabricated result.
"""
from __future__ import annotations

import inspect
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from agent_delegation import DELEGATION_TOOLS
from agent_evidence import (
    STRATEGY_INSTRUCTIONS,
    AttemptLedger,
    next_strategy,
    parse_failure,
)
from agent_guard import APPROVAL_REQUIRED
from agent_tools import (
    ENGINEERING_SCHEMAS,
    MUTATING_TOOLS,
    FileVersionLedger,
    execute_engineering_tool,
)

MAX_REPAIR_ATTEMPTS = 3

# How much of a failing test's real output is carried into the next attempt.
# Enough to name the failing assertion; small enough not to crowd the context.
TEST_OUTPUT_TAIL = 1200

# Deterministic lifecycle. A task is always in exactly one of these, and the
# terminal state is derived from evidence rather than asserted by a caller.
RECEIVED = "received"
PLANNING = "planning"
EXECUTING = "executing"
VERIFYING = "verifying"
REPAIRING = "repairing"
SUCCEEDED = "verified"                 # kept as 'verified' for compatibility
FAILED = "failed_needs_human"
HUMAN_REVIEW = "human_review"
LIFECYCLE = [RECEIVED, PLANNING, EXECUTING, VERIFYING, REPAIRING,
             SUCCEEDED, FAILED, HUMAN_REVIEW]


class NoModelAvailable(RuntimeError):
    """Raised when no LLM provider can be reached. Never swallowed."""


# ── audit ────────────────────────────────────────────────────────────────────

@dataclass
class AuditRecord:
    """Operational evidence for one task. Persisted by the caller."""
    task_id: str
    request: str
    plan: str = ""
    actions: list[dict] = field(default_factory=list)
    files_changed: set[str] = field(default_factory=set)
    tests: list[dict] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    approvals_granted: list[str] = field(default_factory=list)
    approvals_denied: list[str] = field(default_factory=list)
    attempts: int = 0
    state: str = RECEIVED
    states_seen: list[str] = field(default_factory=list)
    attempt_log: list = field(default_factory=list)
    stuck: bool = False
    result: str = "pending"
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    def enter(self, state: str) -> None:
        """Move to a lifecycle state and record the transition."""
        self.state = state
        if not self.states_seen or self.states_seen[-1] != state:
            self.states_seen.append(state)

    def record_action(self, tool: str, args: dict, result: str) -> None:
        parsed = _safe_json(result)
        entry = {
            "tool": tool,
            "arguments": _redact(args),
            "mutating": tool in MUTATING_TOOLS,
            "ok": not (isinstance(parsed, dict) and "error" in parsed),
            "at": time.time(),
        }
        if isinstance(parsed, dict):
            if "error" in parsed:
                entry["error"] = parsed["error"]
                self.failures.append({"tool": tool, "error": parsed["error"], "detail": parsed.get("detail")})
                if parsed["error"] == "approval_required":
                    self.approvals_denied.append(tool)
            if tool == "write_file" and parsed.get("path"):
                self.files_changed.add(parsed["path"])
            if tool == "git_commit" and parsed.get("commit"):
                entry["commit"] = parsed["commit"]
            if tool == "run_tests":
                self.tests.append({
                    "passed": parsed.get("passed"),
                    "exit_code": parsed.get("exit_code"),
                    # Carried through so the ledger and any ancestry briefing can
                    # name the tests that were still failing, not just say "failed".
                    "failing_tests": parsed.get("failing_tests") or [],
                    "failed_count": parsed.get("failed_count"),
                    "passed_count": parsed.get("passed_count"),
                    # A bounded tail of the REAL output. Without it a repair
                    # attempt is told only "tests failed", which is not enough
                    # information to repair anything from.
                    "output_tail": (parsed.get("output") or "")[-TEST_OUTPUT_TAIL:],
                })
            if tool in DELEGATION_TOOLS:
                self._absorb_child_evidence(tool, parsed, entry)
        self.actions.append(entry)

    def _absorb_child_evidence(self, tool: str, parsed: dict, entry: dict) -> None:
        """Take a delegate's REAL evidence into this audit.

        A child's passing test run is genuine evidence -- pytest actually ran --
        so it counts towards the parent's verification. A child's FAILURE is
        absorbed too, which is the important half: it lands in the parent's test
        record and failures, so verify() cannot be satisfied while a delegate is
        broken. The master therefore cannot turn a child failure into a success.
        """
        children = [parsed] if tool == "spawn_specialist" else (parsed.get("children") or [])
        for child in children:
            if not isinstance(child, dict):
                continue
            for test in child.get("tests") or []:
                self.tests.append(test)
            for path in child.get("files_changed") or []:
                self.files_changed.add(path)
            if child.get("commit"):
                entry["commit"] = child["commit"]
            if child.get("status") != "verified":
                entry["ok"] = False
                self.failures.append({
                    "tool": tool,
                    "error": f"child_{child.get('status')}",
                    "detail": (child.get("errors") or [None])[0],
                })

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "request": self.request,
            "plan": self.plan,
            "actions": self.actions,
            "files_changed": sorted(self.files_changed),
            "tests": self.tests,
            "failures": self.failures,
            "approvals_granted": self.approvals_granted,
            "approvals_denied": self.approvals_denied,
            "attempts": self.attempts,
            "state": self.state,
            "states_seen": self.states_seen,
            "attempt_log": self.attempt_log,
            "stuck": self.stuck,
            "result": self.result,
            "duration_sec": round((self.finished_at or time.time()) - self.started_at, 2),
        }


_SECRET_HINT = ("key", "token", "secret", "password", "authorization")


def _redact(args: dict) -> dict:
    """Never let a credential reach the audit log."""
    out = {}
    for k, v in (args or {}).items():
        if any(h in k.lower() for h in _SECRET_HINT):
            out[k] = "[redacted]"
        elif isinstance(v, str) and len(v) > 400:
            out[k] = v[:400] + f"…(+{len(v) - 400} chars)"
        else:
            out[k] = v
    return out


def _safe_json(s: str) -> Any:
    try:
        return json.loads(s)
    except Exception:
        return s


# ── verification ─────────────────────────────────────────────────────────────

async def verify(audit: AuditRecord) -> tuple[bool, str]:
    """Decide whether the task actually succeeded, from evidence only.

    A run is successful only if the test suite was actually executed and
    actually passed. 'The model said it was done' is not evidence.
    """
    if not audit.tests:
        return False, "No test run was executed — cannot verify the change."
    last = audit.tests[-1]
    if not last.get("passed"):
        return False, f"Tests failed (exit code {last.get('exit_code')})."
    return True, "Tests executed and passed."


# ── master loop ──────────────────────────────────────────────────────────────

async def run_task(
    request: str,
    *,
    system_prompt: str,
    approvals: set[str] | None = None,
    model_call: Callable[..., Awaitable[Any]] | None = None,
    max_attempts: int = MAX_REPAIR_ATTEMPTS,
    user_id: str | None = None,
    session_id: str | None = None,
    agent_id: str = "master",
    worker_id: str | None = None,
    persist: bool = False,
    allowed_tools: list[str] | set[str] | None = None,
    delegation=None,
    model_router=None,
    max_rounds: int | None = None,
) -> dict:
    """Execute one engineering task with bounded autonomous repair.

    `model_call` is injected so the runtime is not welded to one provider. In
    production it is the engineering tool loop from agent_llm. It is NEVER
    defaulted to a stub — if nothing is supplied and no provider is importable,
    the run fails loudly.
    """
    audit = AuditRecord(task_id=uuid.uuid4().hex[:12], request=request)
    audit.approvals_granted = sorted(approvals or set())

    if model_call is None:
        model_call = _production_model_call()

    # ── durability (opt-in) ──────────────────────────────────────────────────
    # When persist=True the task gets a durable record with an idempotency key
    # and an execution lease, reusing paid_operations. If that cannot be
    # established we RAISE rather than run: the caller asked for
    # exactly-once semantics, and silently running without them could duplicate
    # real work (writes, commits) on a retry.
    operation = None
    if persist:
        if not user_id:
            raise ValueError("persist=True requires user_id")
        from agent_persistence import begin_task, finish_task, mark_running

        operation, should_execute = await begin_task(
            user_id=user_id, request=request, agent_id=agent_id,
            worker_id=worker_id or f"runtime-{audit.task_id}",
        )
        if not should_execute:
            # Another worker holds the lease, or it already reached a terminal
            # state. Returning the existing record is correct; re-running is not.
            audit.result = "already_running_or_complete"
            audit.finished_at = time.time()
            out = audit.to_dict()
            out["operation_id"] = operation.get("operation_id")
            out["operation_status"] = operation.get("status")
            return out
        await mark_running(operation["operation_id"])

    # ── memory (best-effort) ─────────────────────────────────────────────────
    # Prior turns give a follow-up instruction context. Memory is an
    # enhancement: losing it degrades the task, it must never fail it.
    if session_id:
        from agent_persistence import ensure_session, recall, remember

        await ensure_session(session_id, user_id or "system", {"agent_id": agent_id})
        prior = await recall(session_id)
        if prior:
            audit.plan = f"(continuing session with {len(prior)} prior message(s))"
        await remember(session_id, "user", request)

    # One ledger for the whole task, deliberately spanning repair attempts: a file
    # read in attempt 1 and written in attempt 2 is still checked, and a change
    # made by a human between those attempts is still caught.
    ledger = FileVersionLedger()

    # A delegation context identifies this task as a node in the tree, so an
    # ancestry record points at a real execution rather than a placeholder.
    if delegation is not None and not getattr(delegation, "task_id", ""):
        delegation.task_id = audit.task_id

    # Runtime-owned record of what has already been tried and how it failed. The
    # model never sees it directly and cannot edit it -- an agent able to rewrite
    # its own history of dead ends could quietly forget it is going in circles.
    attempts_ledger = AttemptLedger()
    strategy = "default"
    last_error = ""

    audit.enter(PLANNING)
    for attempt in range(1, max_attempts + 1):
        audit.attempts = attempt
        record = attempts_ledger.open(attempt)
        record.strategy = strategy

        prompt = request if attempt == 1 else _repair_prompt(
            request, audit, attempts_ledger, last_error, strategy)

        # A router picks the provider/model per attempt, so a task can escalate
        # after the cheap local model has actually failed. Without one the
        # single injected model_call is used for every attempt, as before.
        attempt_call = model_router(attempt) if model_router else model_call
        if attempt_call is None:
            audit.result = "no_model_available"
            audit.enter(HUMAN_REVIEW)
            audit.finished_at = time.time()
            raise NoModelAvailable(
                "No usable model for this attempt and no escalation target configured.")

        audit.enter(EXECUTING if attempt == 1 else REPAIRING)
        before_files = set(audit.files_changed)
        try:
            await _drive(prompt, system_prompt, audit, approvals, attempt_call, allowed_tools,
                         ledger, delegation, max_rounds)
        except NoModelAvailable:
            audit.result = "no_model_available"
            audit.enter(HUMAN_REVIEW)
            audit.finished_at = time.time()
            raise
        except Exception as e:  # a tool crash is a failure, not a success
            audit.failures.append({"attempt": attempt, "error": type(e).__name__, "detail": str(e)[:400]})

        # ── close out the attempt with real evidence ────────────────────────
        record.files_changed = sorted(set(audit.files_changed) - before_files)
        last_test = audit.tests[-1] if audit.tests else None
        record.test_target = _last_test_target(audit)
        if last_test is None:
            attempts_ledger.close(passed=None, failure={})
        else:
            attempts_ledger.close(
                passed=bool(last_test.get("passed")),
                failure=parse_failure(last_test.get("output_tail") or "",
                                      last_test.get("exit_code") or 1),
            )
        audit.attempt_log = attempts_ledger.to_evidence()
        audit.stuck = attempts_ledger.is_stuck()

        audit.enter(VERIFYING)
        ok, why = await verify(audit)
        if ok:
            audit.result = SUCCEEDED
            audit.enter(SUCCEEDED)
            audit.finished_at = time.time()
            return await _finalise(audit, operation, session_id)
        last_error = why

        # The same conceptual failure twice means the current approach is spent.
        # Change strategy rather than spending the next attempt the same way.
        if audit.stuck:
            strategy = next_strategy(strategy)

    audit.result = FAILED
    audit.enter(HUMAN_REVIEW if audit.stuck else FAILED)
    audit.finished_at = time.time()
    return await _finalise(audit, operation, session_id)


def _last_test_target(audit: AuditRecord) -> str:
    for action in reversed(audit.actions):
        if action.get("tool") == "run_tests":
            return str((action.get("arguments") or {}).get("target") or "")
    return ""


def _repair_prompt(request: str, audit: AuditRecord, ledger: AttemptLedger,
                   last_error: str, strategy: str) -> str:
    """The next attempt's instruction: the task, the record, and a strategy.

    Two complementary briefings, neither a transcript. `_repair_briefing` covers
    the current state -- what changed, what the test printed, which calls were
    refused. The ledger covers the ARC: which approaches have already been tried
    and what each produced, which is what stops the model proposing the same idea
    a third time in different code.

    Replaying the full history instead would refill the context with the same
    dead ends and invite the model to walk back into them, which is exactly what
    a real specialist did.
    """
    parts = [_repair_briefing(request, audit, last_error), "", ledger.briefing()]
    instruction = STRATEGY_INSTRUCTIONS.get(strategy, "")
    if instruction:
        parts += ["", instruction]
    parts += ["", "Change the code first, then run the test again. Do not repeat a "
                  "call that already failed unchanged."]
    return "\n".join(p for p in parts if p is not None)


def _repair_briefing(request: str, audit: AuditRecord, last_error: str) -> str:
    """Compact, evidence-based account of what actually happened.

    The previous prompt said only "the previous attempt did not pass
    verification", which gives a model nothing to repair from. Replaying the
    whole history instead would refill the context with the same dead ends and
    invite the model to repeat them -- which is what a real specialist did,
    running one failing command fifteen times.

    So this carries FACTS and nothing else: what was changed, what the test
    actually printed, and which tool calls were refused. No reasoning, no
    speculation about the cause.
    """
    lines = [
        request, "",
        f"--- attempt {audit.attempts} of {MAX_REPAIR_ATTEMPTS}: the previous attempt did not pass ---",
        f"Verification result: {last_error}",
    ]

    if audit.files_changed:
        lines.append(f"Files you have already changed: {sorted(audit.files_changed)}")
    else:
        lines.append("You have not changed any file yet. Inspect, then write the change.")

    failing = [t for t in audit.tests if not t.get("passed")]
    if failing:
        last = failing[-1]
        lines.append(f"The test run exited {last.get('exit_code')} and printed:")
        lines.append((last.get("output_tail") or "(no output captured)").strip())
    elif audit.tests:
        lines.append("The last test run passed but verification still failed; re-read the result.")
    else:
        lines.append("You never ran the tests. A change is not verified until they run and pass.")

    # Distinct refusals only: repeating the same one adds nothing.
    refusals, seen = [], set()
    for f in audit.failures:
        key = (f.get("tool"), f.get("error"))
        if not f.get("error") or key in seen:
            continue
        seen.add(key)
        refusals.append(f"  {f.get('tool')}: {f.get('error')} - {(f.get('detail') or '')[:200]}")
    if refusals:
        lines.append("Tool calls that were refused (do not simply retry these):")
        lines.extend(refusals[:5])

    lines.append("")
    lines.append("Fix the cause shown above. Do not repeat a call that already failed "
                 "unchanged; change the code first, then run the test again.")
    return "\n".join(lines)


async def _finalise(audit: AuditRecord, operation: dict | None, session_id: str | None) -> dict:
    """Persist evidence and memory, then return the audit.

    Status is derived from the audit's verification result, never asserted by a
    caller — the same evidence-only rule the loop uses.
    """
    out = audit.to_dict()
    if operation:
        from agent_persistence import finish_task

        await finish_task(operation_id=operation["operation_id"], audit=out)
        out["operation_id"] = operation["operation_id"]
    if session_id:
        from agent_persistence import remember

        await remember(session_id, "assistant", f"result={audit.result} attempts={audit.attempts}")
    return out


async def _drive(prompt, system_prompt, audit, approvals, model_call, allowed_tools=None,
                 ledger=None, delegation=None, max_rounds=None) -> None:
    """One attempt: let the model call engineering tools, recording every call.

    When the agent's configuration restricts `allowed_tools`, that restriction is
    enforced HERE as well as advertised. Filtering the schemas alone would not be
    enforcement: a model can name a tool that was never offered to it, so the
    executor refuses anything outside the set rather than trusting the prompt.
    """
    permitted = set(allowed_tools) if allowed_tools else None

    async def tool_executor(name: str, args: dict) -> str:
        if permitted is not None and name not in permitted:
            denied = json.dumps({
                "error": "tool_not_permitted",
                "detail": f"'{name}' is not in this agent's allowed tools.",
            })
            audit.record_action(name, args, denied)
            return denied
        result = await execute_engineering_tool(
            name, args, approvals=approvals, ledger=ledger, delegation=delegation)
        audit.record_action(name, args, result)
        return result

    schemas = ENGINEERING_SCHEMAS
    if permitted is not None:
        schemas = [s for s in ENGINEERING_SCHEMAS if s["function"]["name"] in permitted]

    # A role's max_rounds governs the inner tool loop, but only reaches a model
    # call that actually accepts it. Passing it blindly would break the scripted
    # calls used in tests, whose signature is (system, user, tools, execute).
    extra = {}
    if max_rounds is not None:
        try:
            if "max_rounds" in inspect.signature(model_call).parameters:
                extra["max_rounds"] = max_rounds
        except (TypeError, ValueError):
            pass

    await model_call(
        system=system_prompt,
        user=prompt,
        tools=schemas,
        execute=tool_executor,
        **extra,
    )


def _production_model_call():
    """Bind the real engineering tool loop.

    Uses agent_llm, which reuses llm_provider's provider transports with the
    ENGINEERING registry rather than the commerce one — so connecting the agent
    does not require modifying production commerce tooling.

    Raises rather than falling back to a stub: a plausible answer produced
    without the ability to inspect the repository is worse than an error.
    """
    try:
        from agent_llm import NoEngineeringProvider, engineering_tool_loop
    except Exception as e:
        raise NoModelAvailable(f"Engineering tool loop unavailable: {e}")

    async def call(system, user, tools, execute):
        try:
            return await engineering_tool_loop(
                system=system, user=user, execute=execute, tools=tools
            )
        except NoEngineeringProvider as e:
            raise NoModelAvailable(str(e)) from e

    return call


__all__ = [
    "AuditRecord", "NoModelAvailable", "MAX_REPAIR_ATTEMPTS",
    "run_task", "verify", "APPROVAL_REQUIRED",
]
