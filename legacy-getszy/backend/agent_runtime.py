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

    last_error = ""
    for attempt in range(1, max_attempts + 1):
        audit.attempts = attempt
        prompt = request if attempt == 1 else (
            f"{request}\n\nThe previous attempt did not pass verification: {last_error}\n"
            "Diagnose the cause and repair it."
        )
        try:
            await _drive(prompt, system_prompt, audit, approvals, model_call)
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
            return audit.to_dict()
        last_error = why

    audit.result = "failed_needs_human"
    audit.finished_at = time.time()
    return audit.to_dict()


async def _drive(prompt, system_prompt, audit, approvals, model_call) -> None:
    """One attempt: let the model call engineering tools, recording every call."""
    async def tool_executor(name: str, args: dict) -> str:
        result = await execute_engineering_tool(name, args, approvals=approvals)
        audit.record_action(name, args, result)
        return result

    await model_call(
        system=system_prompt,
        user=prompt,
        tools=ENGINEERING_SCHEMAS,
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
