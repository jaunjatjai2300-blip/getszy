"""Unified Memory Interface: one facade, and 'unavailable' is never 'empty'.

The facade unifies the memory the Factory already has (session, attempt ledger,
codebase, project) behind one contract. These tests prove the contract holds
without a live Mongo: a reachable-but-empty store reports EMPTY, an unreachable
one reports UNAVAILABLE, every item carries provenance, and project memory is
isolated per namespace.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("JWT_SECRET", "test-only-agent-memory-secret-32chars!")

import agent_memory as mem  # noqa: E402
import agent_evidence  # noqa: E402
import agent_knowledge  # noqa: E402
import session_memory  # noqa: E402
import agent_guard  # noqa: E402


# ── an in-memory Mongo double, so project memory is testable offline ─────────

class _Res:
    def __init__(self, modified_count=0):
        self.modified_count = modified_count
        self.upserted_id = None


class _Cursor:
    def __init__(self, docs):
        self._docs = docs
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i >= len(self._docs):
            raise StopAsyncIteration
        d = self._docs[self._i]
        self._i += 1
        return d


class FakeProjects:
    def __init__(self):
        self.docs = []

    @staticmethod
    def _match(d, q):
        return all(d.get(k) == v for k, v in q.items())

    async def update_one(self, flt, update, upsert=False):
        for d in self.docs:
            if self._match(d, flt):
                d.update(update.get("$set", {}))
                return _Res(1)
        if upsert:
            nd = {}
            nd.update(update.get("$setOnInsert", {}))
            nd.update(update.get("$set", {}))
            self.docs.append(nd)
        return _Res(0)

    def find(self, q, projection=None):
        return _Cursor([dict(d) for d in self.docs if self._match(d, q)])

    async def update_many(self, q, update):
        n = 0
        for d in self.docs:
            if self._match(d, q):
                d.update(update.get("$set", {}))
                n += 1
        return _Res(n)


class RaisingProjects:
    def _boom(self, *a, **k):
        raise RuntimeError("mongo down")
    update_one = find = update_many = _boom


@pytest.fixture
def fake_projects(monkeypatch):
    fp = FakeProjects()
    monkeypatch.setattr(mem, "_projects", lambda: fp)
    return fp


# ── the core invariant: unavailable is a distinct state from empty ───────────

def test_available_property_distinguishes_the_three_states():
    assert mem.MemoryResult("x", mem.OK, items=[object()]).available is True
    assert mem.MemoryResult("x", mem.EMPTY).available is True     # empty is still available
    assert mem.MemoryResult("x", mem.UNAVAILABLE).available is False


# ── session memory ───────────────────────────────────────────────────────────

async def test_session_returns_items_with_provenance(monkeypatch):
    async def fake(session_id, **kw):
        return [{"role": "user", "content": "make a reel", "timestamp": "t1"}]
    monkeypatch.setattr(session_memory, "get_context_messages", fake)
    r = await mem.recall_session("sess-1")
    assert r.status == mem.OK and len(r.items) == 1
    assert r.items[0].source == "session:sess-1" and r.items[0].kind == "session"
    assert r.items[0].meta["role"] == "user"


async def test_session_reachable_but_empty_is_EMPTY(monkeypatch):
    async def fake(session_id, **kw):
        return []
    monkeypatch.setattr(session_memory, "get_context_messages", fake)
    r = await mem.recall_session("sess-1")
    assert r.status == mem.EMPTY and r.available is True


async def test_session_unreachable_is_UNAVAILABLE_not_empty(monkeypatch):
    async def boom(session_id, **kw):
        raise RuntimeError("mongo down")
    monkeypatch.setattr(session_memory, "get_context_messages", boom)
    r = await mem.recall_session("sess-1")
    assert r.status == mem.UNAVAILABLE and r.available is False and r.items == []


# ── attempt history (real runtime ledger) ────────────────────────────────────

def test_attempts_from_a_real_ledger_carry_confidence_and_provenance():
    ledger = agent_evidence.AttemptLedger()
    ledger.open(1); ledger.close(passed=False, failure={"test": "t", "error_type": "AssertionError"})
    ledger.open(2); ledger.close(passed=True, failure=None)
    r = mem.recall_attempts(ledger)
    assert r.status == mem.OK and len(r.items) == 2
    assert r.items[0].source == "attempt:1" and r.items[0].confidence == 0.0
    assert r.items[1].confidence == 1.0


def test_unused_ledger_is_EMPTY_but_missing_ledger_is_UNAVAILABLE():
    assert mem.recall_attempts(agent_evidence.AttemptLedger()).status == mem.EMPTY
    assert mem.recall_attempts(None).status == mem.UNAVAILABLE


# ── codebase memory: fail-closed carried through from agent_knowledge ────────

async def test_codebase_unavailable_is_UNAVAILABLE_not_empty(monkeypatch):
    async def fake(query, limit=6):
        return '{"error": "retrieval_unavailable", "detail": "ChromaDB is not installed"}'
    monkeypatch.setattr(agent_knowledge, "search_codebase", fake)
    r = await mem.recall_codebase("MissionWorkspace")
    assert r.status == mem.UNAVAILABLE and r.available is False
    assert "ChromaDB" in r.reason


async def test_codebase_results_are_marked_untrusted(monkeypatch):
    async def fake(query, limit=6):
        return '{"provider":"codebase_rag","count":1,"notice":"n","results":[{"file":"x.py","content":"code","score":0.9}]}'
    monkeypatch.setattr(agent_knowledge, "search_codebase", fake)
    r = await mem.recall_codebase("x")
    assert r.status == mem.OK and r.items[0].untrusted is True
    assert r.items[0].source == "codebase:x.py"


# ── project memory: storage, provenance, isolation, invalidation ─────────────

async def test_project_remember_then_recall_with_provenance(fake_projects):
    w = await mem.remember_project("projA", "stack", "React + FastAPI", confidence=0.8)
    assert w.status == mem.OK
    r = await mem.recall_project("projA")
    assert r.status == mem.OK and len(r.items) == 1
    it = r.items[0]
    assert it.content == "React + FastAPI" and it.confidence == 0.8
    assert it.namespace == "projA" and it.source == "project:projA/stack" and it.timestamp


async def test_project_memory_is_isolated_per_namespace(fake_projects):
    await mem.remember_project("projA", "k", "A-secret")
    await mem.remember_project("projB", "k", "B-secret")
    ra = await mem.recall_project("projA")
    assert [i.content for i in ra.items] == ["A-secret"]        # never sees projB
    rb = await mem.recall_project("projB")
    assert [i.content for i in rb.items] == ["B-secret"]


async def test_invalidated_memory_is_no_longer_recalled(fake_projects):
    await mem.remember_project("projA", "old", "stale")
    await mem.invalidate_project("projA", key="old")
    r = await mem.recall_project("projA")
    assert r.status == mem.EMPTY and r.items == []


async def test_empty_namespace_is_refused_not_matched_broadly(fake_projects):
    with pytest.raises(ValueError):
        await mem.recall_project("")
    with pytest.raises(ValueError):
        await mem.remember_project("", "k", "v")


async def test_project_store_unreachable_is_UNAVAILABLE(monkeypatch):
    monkeypatch.setattr(mem, "_projects", lambda: RaisingProjects())
    assert (await mem.recall_project("projA")).status == mem.UNAVAILABLE
    assert (await mem.remember_project("projA", "k", "v")).status == mem.UNAVAILABLE


# ── the facade itself is a protected control file ────────────────────────────

def test_memory_facade_is_self_protected():
    assert "backend/agent_memory.py" in agent_guard.SELF_PROTECTED


def test_status_reports_each_backing_store_without_a_query():
    s = mem.status()
    assert set(s) == {"session", "attempt", "codebase", "project"}
    assert "retrieval_available" in s["codebase"]
