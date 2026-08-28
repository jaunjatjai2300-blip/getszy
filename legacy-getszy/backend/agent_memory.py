"""Agent Factory — unified memory interface (facade).

ONE facade over the memory the Factory ALREADY has. It creates no new store and
no second engine:

  * session memory   -> session_memory (Mongo `chat_sessions`)
  * attempt history  -> agent_evidence.AttemptLedger (runtime-owned)
  * codebase memory  -> agent_knowledge (codebase_rag + ChromaDB, fail-closed)
  * project memory   -> a thin `agent_memory` collection in the SAME Mongo

Two invariants it exists to guarantee, uniformly across every backing store:

1. UNAVAILABLE IS NOT EMPTY. A backend that cannot be reached returns
   status="unavailable" with a reason — never an empty result that an agent would
   read as "there is no such knowledge". `agent_knowledge` already draws this line
   for the codebase; the facade draws it for every store.

2. NOTHING IS FABRICATED. Every item carries provenance (which store, which id),
   a timestamp and, where meaningful, a confidence. Retrieved repository content
   keeps its untrusted marker. The facade never invents a memory.

Namespaces isolate project memory: a recall is scoped to exactly one namespace,
and an empty namespace is a programming error (it would match everything), so it
raises rather than silently crossing the boundary.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import agent_knowledge
import session_memory
from db import db

logger = logging.getLogger("getszy.agent.memory")

# Retrieval status — the three are distinct on purpose.
OK = "ok"
EMPTY = "empty"
UNAVAILABLE = "unavailable"

PROJECT_COLLECTION = "agent_memory"
DEFAULT_LIMIT = 20


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class MemoryItem:
    """One remembered thing, always with provenance."""
    content: str
    source: str                 # provenance, e.g. "session:abc", "attempt:2", "codebase", "project:ns/key"
    kind: str                   # session | attempt | codebase | project
    timestamp: str | None = None
    confidence: float | None = None
    namespace: str | None = None
    untrusted: bool = False
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "content": self.content, "source": self.source, "kind": self.kind,
            "timestamp": self.timestamp, "confidence": self.confidence,
            "namespace": self.namespace, "untrusted": self.untrusted, "meta": self.meta,
        }


@dataclass
class MemoryResult:
    """The outcome of a recall. `status` separates unavailable from empty."""
    kind: str
    status: str                 # OK | EMPTY | UNAVAILABLE
    items: list = field(default_factory=list)
    reason: str = ""
    retrieved_at: str = field(default_factory=_now)

    @property
    def available(self) -> bool:
        """False only when the backend could not be reached — never merely empty."""
        return self.status != UNAVAILABLE

    def to_dict(self) -> dict:
        return {
            "kind": self.kind, "status": self.status, "available": self.available,
            "reason": self.reason, "retrieved_at": self.retrieved_at,
            "count": len(self.items), "items": [i.to_dict() for i in self.items],
        }


def _ok(kind: str, items: list) -> MemoryResult:
    return MemoryResult(kind=kind, status=OK if items else EMPTY, items=items)


def _empty(kind: str, reason: str = "") -> MemoryResult:
    return MemoryResult(kind=kind, status=EMPTY, items=[], reason=reason)


def _unavailable(kind: str, reason: str) -> MemoryResult:
    return MemoryResult(kind=kind, status=UNAVAILABLE, items=[], reason=reason)


# ── session memory ───────────────────────────────────────────────────────────

async def recall_session(session_id: str, *, max_messages: int | None = None,
                         max_tokens: int | None = None) -> MemoryResult:
    """Recent conversation for a session. Reachable-but-empty is EMPTY; an
    unreachable store is UNAVAILABLE — the two are never conflated."""
    if not session_id:
        return _unavailable("session", "A session_id is required.")
    try:
        messages = await session_memory.get_context_messages(
            session_id, max_messages=max_messages, max_tokens=max_tokens)
    except Exception as e:                                    # store unreachable
        logger.warning("session recall failed: %s", e)
        return _unavailable("session", f"Session store unavailable: {type(e).__name__}.")
    items = [
        MemoryItem(
            content=str(m.get("content", "")),
            source=f"session:{session_id}", kind="session",
            timestamp=m.get("timestamp"), meta={"role": m.get("role", "user")},
        ) for m in (messages or [])
    ]
    return _ok("session", items)


# ── attempt history (runtime-owned ledger; never model-writable) ─────────────

def recall_attempts(ledger) -> MemoryResult:
    """Read-only view of what a task has already tried. Takes the runtime's
    AttemptLedger; a missing ledger is UNAVAILABLE, an unused one is EMPTY."""
    if ledger is None:
        return _unavailable("attempt", "No attempt ledger for this task.")
    try:
        evidence = ledger.to_evidence()
    except Exception as e:
        return _unavailable("attempt", f"Attempt ledger unreadable: {type(e).__name__}.")
    items = [
        MemoryItem(
            content=(f"attempt {a.get('attempt')}: "
                     f"{'passed' if a.get('passed') else 'failed'}"
                     + (f" — changed {', '.join(a.get('files_changed') or [])}" if a.get("files_changed") else "")),
            source=f"attempt:{a.get('attempt')}", kind="attempt",
            confidence=(1.0 if a.get("passed") else 0.0 if a.get("passed") is not None else None),
            meta={k: v for k, v in a.items() if k != "raw"},
        ) for a in evidence
    ]
    return _ok("attempt", items)


# ── codebase memory (delegates fail-closed behaviour to agent_knowledge) ─────

async def recall_codebase(query: str, *, limit: int | None = None) -> MemoryResult:
    """Semantic codebase retrieval. `agent_knowledge` already fails closed; the
    facade surfaces its `retrieval_unavailable` as UNAVAILABLE, and a real empty
    result as EMPTY, so an agent never mistakes a missing index for missing code."""
    try:
        raw = await agent_knowledge.search_codebase(query, limit or agent_knowledge.MAX_RESULTS)
        data = json.loads(raw)
    except Exception as e:
        return _unavailable("codebase", f"Codebase retrieval error: {type(e).__name__}.")
    if data.get("error"):
        return _unavailable("codebase", str(data.get("detail") or data.get("error")))
    items = [
        MemoryItem(
            content=str(r.get("content", "")),
            source=f"codebase:{r.get('file') or '?'}", kind="codebase",
            confidence=r.get("score"), untrusted=True,
            meta={"file": r.get("file"), "notice": data.get("notice")},
        ) for r in (data.get("results") or [])
    ]
    return _ok("codebase", items)


# ── project memory (long-term, in the SAME Mongo; namespace-isolated) ────────

def _projects():
    """The project-memory collection — a collection in the existing Mongo, not a
    new database. Indirected so tests can substitute an in-memory double."""
    return db[PROJECT_COLLECTION]


def _require_namespace(namespace: str) -> None:
    if not namespace or not str(namespace).strip():
        # An empty namespace would match every namespace at once. Isolation is a
        # boundary, not a default — crossing it is a bug, so refuse loudly.
        raise ValueError("A non-empty namespace is required; memory is isolated per namespace.")


async def remember_project(namespace: str, key: str, content: str, *,
                           confidence: float | None = None, source: str = "agent",
                           meta: dict | None = None) -> MemoryResult:
    """Store or update one long-term project memory. Idempotent on (namespace, key)."""
    _require_namespace(namespace)
    if not key:
        return _unavailable("project", "A key is required.")
    now = _now()
    doc = {
        "namespace": namespace, "key": key, "content": content,
        "confidence": confidence, "source": source, "meta": meta or {},
        "valid": True, "updated_at": now,
    }
    try:
        await _projects().update_one(
            {"namespace": namespace, "key": key},
            {"$set": doc, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
    except Exception as e:
        logger.warning("project remember failed: %s", e)
        return _unavailable("project", f"Project memory store unavailable: {type(e).__name__}.")
    return _ok("project", [MemoryItem(
        content=content, source=f"project:{namespace}/{key}", kind="project",
        timestamp=now, confidence=confidence, namespace=namespace, meta=meta or {})])


async def recall_project(namespace: str, *, key: str | None = None,
                         limit: int = DEFAULT_LIMIT) -> MemoryResult:
    """Recall long-term memories for exactly one namespace. Never crosses it."""
    _require_namespace(namespace)
    query = {"namespace": namespace, "valid": True}
    if key:
        query["key"] = key
    try:
        cursor = _projects().find(query, {"_id": 0})
        docs = [d async for d in cursor]
    except Exception as e:
        logger.warning("project recall failed: %s", e)
        return _unavailable("project", f"Project memory store unavailable: {type(e).__name__}.")
    docs.sort(key=lambda d: d.get("updated_at") or "", reverse=True)
    items = [
        MemoryItem(
            content=str(d.get("content", "")),
            source=f"project:{namespace}/{d.get('key')}", kind="project",
            timestamp=d.get("updated_at"), confidence=d.get("confidence"),
            namespace=namespace, meta=d.get("meta") or {},
        ) for d in docs[:max(1, int(limit))]
    ]
    return _ok("project", items)


async def invalidate_project(namespace: str, *, key: str | None = None) -> MemoryResult:
    """Retire memories (retention-preserving: marked invalid, not deleted) so they
    stop being recalled. Scoped to one namespace; a key narrows to one memory."""
    _require_namespace(namespace)
    query = {"namespace": namespace, "valid": True}
    if key:
        query["key"] = key
    try:
        result = await _projects().update_many(
            query, {"$set": {"valid": False, "invalidated_at": _now()}})
        count = getattr(result, "modified_count", 0)
    except Exception as e:
        logger.warning("project invalidate failed: %s", e)
        return _unavailable("project", f"Project memory store unavailable: {type(e).__name__}.")
    return MemoryResult(kind="project", status=OK, items=[], reason=f"invalidated {count}")


# ── status ───────────────────────────────────────────────────────────────────

def status() -> dict:
    """What memory this deployment can actually serve. Honest about the codebase
    backend (checkable without a query); Mongo-backed stores are reported by
    intent and confirmed only when actually queried (fail-closed at call time)."""
    return {
        "session": {"backend": "mongo:chat_sessions"},
        "attempt": {"backend": "runtime:AttemptLedger"},
        "codebase": agent_knowledge.status(),
        "project": {"backend": f"mongo:{PROJECT_COLLECTION}"},
    }


__all__ = [
    "MemoryItem", "MemoryResult", "OK", "EMPTY", "UNAVAILABLE",
    "recall_session", "recall_attempts", "recall_codebase",
    "remember_project", "recall_project", "invalidate_project", "status",
]
