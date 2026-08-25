"""Agent Factory — hierarchical specialist delegation.

A master agent delegates a bounded piece of work to a specialist built by the
existing Factory, and gets structured evidence back.

THE INVARIANT, enforced in code rather than asked for in a prompt:

    child_tools     ⊆ parent_tools
    child_approvals ⊆ parent_approvals ∩ parent_delegable
    child_tier      ≤ parent_tier
    child_sandbox   = parent_sandbox   (always "repo")

A child can only ever be a narrowing of its parent. There is no path that widens
authority: the intersection is computed here, the resulting tool list is passed
to run_task which filters the schemas AND refuses anything outside the set at the
executor, and every file operation still goes through agent_guard. Delegation adds
no privilege of its own.

Two failure styles, deliberately different:

  * a config that simply DECLARES more than the parent has (a generic factory
    template) is INTERSECTED down -- that is not an attack, it is a template
    meeting a narrower context.
  * an explicit REQUEST for something outside the parent's scope is REFUSED, not
    quietly trimmed. Silently granting less than was asked for hides the attempt,
    and the attempt is the interesting part.

Bounded on three axes so a delegation tree cannot run away: depth, children per
task, and total descendants across the whole tree (a shared budget, so breadth
cannot be used to dodge the depth limit).

Nothing here relaxes Getszy's security model. agent_guard remains the authority.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field

from agent_guard import APPROVAL_REQUIRED

logger = logging.getLogger("getszy.agent.delegation")

# Bounds. Depth 2 means master -> specialist -> sub-specialist and no further.
MAX_DEPTH = 2
MAX_CHILDREN_PER_TASK = 4
MAX_TOTAL_DESCENDANTS = 8
CHILD_MAX_ATTEMPTS = 3          # the same bounded repair policy as the master

# Ordered weakest to strongest; a child may match or drop, never climb.
TIER_RANK = {"light": 0, "standard": 1, "strong": 2}

DELEGATION_TOOLS = {"spawn_specialist", "spawn_specialists"}


class DelegationDenied(PermissionError):
    """A delegation was refused. Never downgraded to a warning."""


def specialist_key(description: str) -> str:
    """Stable id for a specialist derived from its description.

    build_config mints a fresh uuid per call, which would make every delegation a
    new identity and defeat the durable idempotency key. Deriving the id from the
    description means the same specialist doing the same task reuses its record
    instead of executing twice.
    """
    digest = hashlib.sha256(description.strip().lower().encode("utf-8")).hexdigest()
    return f"spec-{digest[:16]}"


def check_spawn_allowed(context, count: int = 1) -> tuple[bool, str]:
    """Whether `count` more children may be spawned right now.

    Single source of truth for the three bounds, so the dispatcher gate and the
    context's own check can never disagree. Asking for N at once is checked as N,
    not as one — a parallel spawn of 4 when 2 remain must be refused whole rather
    than half-granted.
    """
    if context is None:
        return False, "No delegation context is present, so nothing may be spawned."
    if context.depth + 1 > MAX_DEPTH:
        return False, (
            f"Delegation depth limit reached (max {MAX_DEPTH}); this agent is at "
            f"depth {context.depth} and cannot spawn further."
        )
    if context.children_spawned + count > MAX_CHILDREN_PER_TASK:
        return False, (
            f"This task has already spawned {context.children_spawned} specialists "
            f"(max {MAX_CHILDREN_PER_TASK}); refusing {count} more."
        )
    if context.budget["descendants"] + count > MAX_TOTAL_DESCENDANTS:
        return False, (
            f"The delegation tree already contains {context.budget['descendants']} "
            f"agents (max {MAX_TOTAL_DESCENDANTS}); refusing {count} more."
        )
    return True, ""


@dataclass
class DelegationContext:
    """One node in the delegation tree: who we are and what we may hand down."""

    task_id: str
    agent_id: str
    tools: frozenset[str]
    approvals: frozenset[str] = frozenset()
    # Approvals the parent is willing to pass down at all. Possessing an approval
    # is not the same as being allowed to delegate it.
    delegable: frozenset[str] = frozenset()
    model_tier: str = "standard"
    ancestry: tuple[str, ...] = ()
    depth: int = 0
    user_id: str | None = None
    session_id: str | None = None
    # Shared across the whole tree by reference, so breadth cannot be used to
    # escape the depth limit.
    budget: dict = field(default_factory=lambda: {"descendants": 0})
    model_factory: object = None
    children_spawned: int = 0
    spawned: list = field(default_factory=list)

    def _check_budget(self, count: int = 1) -> None:
        allowed, reason = check_spawn_allowed(self, count)
        if not allowed:
            raise DelegationDenied(reason)

    def child(self, cfg: dict, *, requested_tools=None, requested_approvals=None) -> "DelegationContext":
        """Derive a child context that can only be narrower than this one."""
        self._check_budget()

        config_tools = set(cfg.get("allowed_tools") or [])
        # A generic template declaring more than we hold is intersected, not refused.
        allowed = frozenset(config_tools & set(self.tools))

        if requested_tools is not None:
            requested = set(requested_tools)
            outside = sorted(requested - allowed)
            if outside:
                # An explicit request for something out of scope is an attempt, and
                # is reported as one rather than quietly trimmed.
                raise DelegationDenied(
                    f"Requested tools outside the parent's scope: {outside}. "
                    f"A child can never exceed its parent."
                )
            allowed = frozenset(requested)

        if not allowed:
            raise DelegationDenied(
                "The specialist would have no tools within the parent's scope; "
                "refusing to spawn a powerless agent."
            )

        approvals = frozenset()
        if requested_approvals:
            asked = set(requested_approvals)
            unknown = sorted(asked - APPROVAL_REQUIRED)
            if unknown:
                raise DelegationDenied(f"Unknown approvals requested: {unknown}")
            ungranted = sorted(asked - set(self.approvals))
            if ungranted:
                raise DelegationDenied(
                    f"Parent does not hold {ungranted}, so it cannot delegate them."
                )
            undelegable = sorted(asked - set(self.delegable))
            if undelegable:
                raise DelegationDenied(
                    f"{undelegable} were not marked delegable by the parent. "
                    "Holding an approval does not imply the right to hand it down."
                )
            approvals = frozenset(asked)

        # Never upward. A template asking for a stronger tier gets the parent's.
        child_tier = cfg.get("model_tier") or "standard"
        if TIER_RANK.get(child_tier, 1) > TIER_RANK.get(self.model_tier, 1):
            child_tier = self.model_tier

        child_id = cfg.get("id") or "specialist"
        self.children_spawned += 1
        self.budget["descendants"] += 1

        return DelegationContext(
            task_id="",                       # assigned by the run
            agent_id=child_id,
            tools=allowed,
            approvals=approvals,
            delegable=approvals,              # a child may pass on only what it holds
            model_tier=child_tier,
            ancestry=self.ancestry + (self.agent_id,),
            depth=self.depth + 1,
            user_id=self.user_id,
            session_id=self.session_id,
            budget=self.budget,               # shared by reference
            model_factory=self.model_factory,
        )


def master_context(*, task_id: str, tools, approvals=None, delegable=None,
                   model_tier: str = "standard", user_id=None, session_id=None,
                   model_factory=None) -> DelegationContext:
    """Root of a delegation tree.

    `delegable` defaults to EMPTY, not to `approvals`: a master holding an
    approval must state separately that it may be handed down. Approval stays
    operation-specific at every hop.
    """
    return DelegationContext(
        task_id=task_id,
        agent_id="master",
        tools=frozenset(tools),
        approvals=frozenset(approvals or ()),
        delegable=frozenset(delegable or ()),
        model_tier=model_tier,
        ancestry=(),
        depth=0,
        user_id=user_id,
        session_id=session_id,
        model_factory=model_factory,
    )


# ── running a specialist ─────────────────────────────────────────────────────

async def delegate(*, specialist: str, task: str, context: DelegationContext,
                   requested_tools=None, requested_approvals=None,
                   persist: bool | None = None) -> dict:
    """Build, validate and run one specialist. Always returns structured evidence."""
    # Lazy: agent_factory imports agent_tools, which imports this module for the
    # spawn tools. Importing at call time keeps that cycle from forming at import.
    import agent_factory

    try:
        cfg = agent_factory.build_config(specialist, owner_id=context.user_id or "system")
        cfg["id"] = specialist_key(specialist)
        problems = agent_factory.validate_config(cfg)
        if problems:
            raise DelegationDenied(f"Specialist configuration invalid: {'; '.join(problems)}")
        child = context.child(cfg, requested_tools=requested_tools,
                              requested_approvals=requested_approvals)
    except (DelegationDenied, agent_factory.FactoryRejected) as e:
        return _denied(specialist, task, context, str(e))

    import agent_runtime

    model_call = None
    if context.model_factory is not None:
        model_call = context.model_factory(child.model_tier)

    should_persist = persist if persist is not None else bool(context.user_id)

    try:
        audit = await agent_runtime.run_task(
            task,
            system_prompt=cfg["system_prompt"],
            approvals=set(child.approvals) or None,
            model_call=model_call,
            max_attempts=CHILD_MAX_ATTEMPTS,
            user_id=context.user_id,
            session_id=None,          # a child does not write to the parent's memory
            agent_id=child.agent_id,
            allowed_tools=sorted(child.tools),
            persist=should_persist,
            delegation=child,
        )
    except Exception as e:
        logger.exception("specialist %s failed", child.agent_id)
        return _failure(specialist, task, child, cfg, f"{type(e).__name__}: {e}")

    result = _result(specialist, task, child, cfg, audit)
    context.spawned.append(_ancestry_record(child, cfg, task, result["status"]))

    if should_persist and audit.get("operation_id"):
        await _persist_ancestry(audit["operation_id"], child, cfg, task, context)
    return result


async def delegate_parallel(*, requests: list[dict], context: DelegationContext) -> dict:
    """Run independent specialists concurrently, aggregating fail-safe.

    Concurrency safety is NOT special-cased here. Each child gets its own file
    version ledger inside run_task, so if two specialists touch the same file the
    second is refused by the existing concurrency check rather than overwriting
    the first. That is the same mechanism a human editing the file would trigger.
    """
    if not requests:
        return {"status": "denied", "error": "No delegation requests supplied.", "children": []}

    async def one(spec: dict) -> dict:
        return await delegate(
            specialist=spec.get("specialist", ""),
            task=spec.get("task", ""),
            context=context,
            requested_tools=spec.get("tools"),
            requested_approvals=spec.get("approvals"),
        )

    settled = await asyncio.gather(*(one(s) for s in requests), return_exceptions=True)

    children = []
    for spec, outcome in zip(requests, settled):
        if isinstance(outcome, BaseException):
            # A crash must never vanish into a gathered result.
            children.append({
                "status": "error",
                "specialist": spec.get("specialist"),
                "task": spec.get("task"),
                "errors": [f"{type(outcome).__name__}: {outcome}"],
                "verification": {"verified": False, "reason": "The specialist raised."},
            })
        else:
            children.append(outcome)

    verified = [c for c in children if c["status"] == "verified"]
    return {
        "status": "verified" if len(verified) == len(children) else "partial",
        "requested": len(requests),
        "verified": len(verified),
        "failed": len(children) - len(verified),
        "children": children,
    }


# ── structured results ───────────────────────────────────────────────────────

def _result(specialist, task, child, cfg, audit) -> dict:
    commit = next((a.get("commit") for a in reversed(audit.get("actions") or [])
                   if a.get("commit")), None)
    verified = audit.get("result") == "verified"
    return {
        "status": audit.get("result"),
        "specialist": {
            "description": specialist[:300],
            "agent_id": child.agent_id,
            "capabilities": cfg.get("capabilities"),
            "model_tier": child.model_tier,
            "tool_scope": sorted(child.tools),
            "approvals": sorted(child.approvals),
            "sandbox": cfg.get("sandbox"),
        },
        "task": task[:500],
        "files_changed": audit.get("files_changed", []),
        "tests": audit.get("tests", []),
        "verification": {
            "verified": verified,
            "reason": ("Tests executed and passed." if verified
                       else "No passing test evidence; the specialist did not verify its work."),
        },
        "commit": commit,
        "errors": [f.get("error") or f.get("detail") for f in (audit.get("failures") or [])][:10],
        "evidence": {
            "task_id": audit.get("task_id"),
            "attempts": audit.get("attempts"),
            "max_attempts": CHILD_MAX_ATTEMPTS,
            "operation_id": audit.get("operation_id"),
            "tools_used": [a.get("tool") for a in (audit.get("actions") or [])],
            "duration_sec": audit.get("duration_sec"),
        },
        "ancestry": list(child.ancestry),
        "depth": child.depth,
    }


def _denied(specialist, task, context, reason) -> dict:
    return {
        "status": "denied",
        "specialist": {"description": specialist[:300], "agent_id": None},
        "task": task[:500],
        "files_changed": [], "tests": [], "commit": None,
        "errors": [reason],
        "verification": {"verified": False, "reason": reason},
        "evidence": {"attempts": 0, "max_attempts": CHILD_MAX_ATTEMPTS},
        "ancestry": list(context.ancestry) + [context.agent_id],
        "depth": context.depth + 1,
    }


def _failure(specialist, task, child, cfg, reason) -> dict:
    out = _result(specialist, task, child, cfg, {"result": "error", "actions": [], "attempts": 0})
    out["errors"] = [reason]
    out["verification"] = {"verified": False, "reason": reason}
    return out


def _ancestry_record(child, cfg, task, status) -> dict:
    return {
        "child_agent_id": child.agent_id,
        "specialist_type": ",".join(cfg.get("capabilities") or []),
        "requested_task": task[:300],
        "tool_scope": sorted(child.tools),
        "approvals": sorted(child.approvals),
        "model_tier": child.model_tier,
        "ancestry": list(child.ancestry),
        "depth": child.depth,
        "status": status,
    }


async def _persist_ancestry(operation_id, child, cfg, task, parent) -> None:
    """Record the parent/child relationship on the durable operation.

    Operational facts only — no prompts and no model reasoning.
    """
    try:
        from paid_operations import update_operation

        await update_operation(operation_id, {"delegation": {
            "parent_task_id": parent.task_id,
            "parent_agent_id": parent.agent_id,
            **_ancestry_record(child, cfg, task, "recorded"),
        }})
    except Exception:
        logger.warning("could not persist delegation ancestry for %s", operation_id)


# ── tools the master can call ────────────────────────────────────────────────

async def spawn_specialist(specialist: str, task: str, tools=None, approvals=None,
                           delegation: DelegationContext | None = None) -> str:
    if delegation is None:
        return json.dumps({
            "error": "delegation_unavailable",
            "detail": "This agent has no delegation context, so it cannot spawn specialists.",
        })
    if not specialist or not task:
        return json.dumps({"error": "bad_arguments",
                           "detail": "Both 'specialist' and 'task' are required."})
    result = await delegate(specialist=specialist, task=task, context=delegation,
                            requested_tools=tools, requested_approvals=approvals)
    return json.dumps(result, default=str)


async def spawn_specialists(requests=None, delegation: DelegationContext | None = None) -> str:
    if delegation is None:
        return json.dumps({
            "error": "delegation_unavailable",
            "detail": "This agent has no delegation context, so it cannot spawn specialists.",
        })
    if not isinstance(requests, list) or not requests:
        return json.dumps({"error": "bad_arguments",
                           "detail": "'requests' must be a non-empty list."})
    result = await delegate_parallel(requests=requests[:MAX_CHILDREN_PER_TASK],
                                     context=delegation)
    return json.dumps(result, default=str)


__all__ = [
    "DelegationContext", "DelegationDenied", "DELEGATION_TOOLS",
    "MAX_DEPTH", "MAX_CHILDREN_PER_TASK", "MAX_TOTAL_DESCENDANTS", "CHILD_MAX_ATTEMPTS",
    "master_context", "delegate", "delegate_parallel",
    "spawn_specialist", "spawn_specialists", "specialist_key",
]
