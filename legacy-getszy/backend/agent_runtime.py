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

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from agent_guard import APPROVAL_REQUIRED
from agent_tools import (
    ENGINEERING_SCHEMAS,
    MUTATING_TOOLS,
    execute_engineering_tool,
)

MAX_REPAIR_ATTEMPTS = 3


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
    result: str = "pending"
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None

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
                self.tests.append({"passed": parsed.get("passed"), "exit_code": parsed.get("exit_code")})
        self.actions.append(entry)

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

    last_error = ""
    for attempt in range(1, max_attempts + 1):
        audit.attempts = attempt
        prompt = request if attempt == 1 else (
            f"{request}\n\nThe previous attempt did not pass verification: {last_error}\n"
            "Diagnose the cause and repair it."
        )
        try:
            await _drive(prompt, system_prompt, audit, approvals, model_call, allowed_tools)
        except NoModelAvailable:
            audit.result = "no_model_available"
            audit.finished_at = time.time()
            raise
        except Exception as e:  # a tool crash is a failure, not a success
            audit.failures.append({"attempt": attempt, "error": type(e).__name__, "detail": str(e)[:400]})

        ok, why = await verify(audit)
        if ok:
            audit.result = "verified"
            audit.finished_at = time.time()
            return await _finalise(audit, operation, session_id)
        last_error = why

    audit.result = "failed_needs_human"
    audit.finished_at = time.time()
    return await _finalise(audit, operation, session_id)


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


async def _drive(prompt, system_prompt, audit, approvals, model_call, allowed_tools=None) -> None:
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
        result = await execute_engineering_tool(name, args, approvals=approvals)
        audit.record_action(name, args, result)
        return result

    schemas = ENGINEERING_SCHEMAS
    if permitted is not None:
        schemas = [s for s in ENGINEERING_SCHEMAS if s["function"]["name"] in permitted]

    await model_call(
        system=system_prompt,
        user=prompt,
        tools=schemas,
        execute=tool_executor,
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
