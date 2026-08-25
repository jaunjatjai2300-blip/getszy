"""Optimistic concurrency: an agent must never destroy a change it never saw.

The scenario these tests exist for is a human editing a file while the agent is
thinking. Nothing in the agent can detect that on its own — from inside the task
the write simply succeeds and the human's work is gone with no trace.

Every file here is real and inside the real sandbox; the changes are made with
ordinary filesystem writes, exactly as an editor would.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("JWT_SECRET", "test-only-agent-concurrency-secret-32!!")

import agent_runtime as rt  # noqa: E402
import agent_tools  # noqa: E402
from agent_guard import REPO_ROOT  # noqa: E402

REL = "backend/tests/_concurrency_fixture.txt"
ORIGINAL = "original content, written before the agent looked at it\n"
HUMAN_EDIT = "IMPORTANT: a human edited this while the agent was thinking\n"
AGENT_WRITE = "content the agent wanted to write\n"


@pytest.fixture
def target():
    p = REPO_ROOT / REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(ORIGINAL.encode("utf-8"))
    yield p
    if p.exists():
        p.unlink()


async def call(name, args, ledger):
    return json.loads(await agent_tools.execute_engineering_tool(name, args, ledger=ledger))


# ── the ledger records what was genuinely inspected ──────────────────────────

@pytest.mark.asyncio
async def test_a_complete_read_records_the_version(target):
    ledger = agent_tools.FileVersionLedger()
    out = await call("read_file", {"path": REL}, ledger)
    assert out["version"] == agent_tools.file_version(target)
    assert ledger.seen(REL) == out["version"]


@pytest.mark.asyncio
async def test_a_truncated_read_does_not_authorise_a_write(target):
    """Seeing part of a file is not knowing what you would be replacing."""
    ledger = agent_tools.FileVersionLedger()
    out = await call("read_file", {"path": REL, "max_bytes": 5}, ledger)
    assert out["truncated"] is True
    assert ledger.seen(REL) is None

    refused = await call("write_file", {"path": REL, "content": AGENT_WRITE}, ledger)
    assert refused["error"] == "unverified_overwrite"
    assert target.read_text(encoding="utf-8") == ORIGINAL


# ── the scenario the requirement describes ───────────────────────────────────

@pytest.mark.asyncio
async def test_write_is_refused_when_the_file_changed_after_inspection(target):
    ledger = agent_tools.FileVersionLedger()

    # 1. the agent reads the file
    seen = await call("read_file", {"path": REL}, ledger)

    # 2. a human changes it externally
    target.write_bytes(HUMAN_EDIT.encode("utf-8"))

    # 3-4. the agent attempts a write and is refused
    out = await call("write_file", {"path": REL, "content": AGENT_WRITE}, ledger)
    assert out["error"] == "concurrent_change"

    # 5. the refusal carries real evidence, not just a message
    assert out["inspected_version"] == seen["version"]
    assert out["current_version"] == agent_tools.file_version(target)
    assert out["inspected_version"] != out["current_version"]
    assert out["path"] == REL

    # 7. the human's change is intact
    assert target.read_text(encoding="utf-8") == HUMAN_EDIT


@pytest.mark.asyncio
async def test_agent_recovers_by_re_reading(target):
    """6. after the conflict the agent can re-read and proceed safely."""
    ledger = agent_tools.FileVersionLedger()
    await call("read_file", {"path": REL}, ledger)
    target.write_bytes(HUMAN_EDIT.encode("utf-8"))
    assert (await call("write_file", {"path": REL, "content": AGENT_WRITE}, ledger))["error"]

    # re-read picks up the human's version, and now the write is allowed
    reread = await call("read_file", {"path": REL}, ledger)
    assert reread["content"] == HUMAN_EDIT

    ok = await call("write_file", {"path": REL, "content": AGENT_WRITE}, ledger)
    assert "error" not in ok
    assert target.read_text(encoding="utf-8") == AGENT_WRITE


@pytest.mark.asyncio
async def test_unchanged_file_still_writes(target):
    ledger = agent_tools.FileVersionLedger()
    await call("read_file", {"path": REL}, ledger)
    out = await call("write_file", {"path": REL, "content": AGENT_WRITE}, ledger)
    assert "error" not in out and out["created"] is False
    assert target.read_text(encoding="utf-8") == AGENT_WRITE


@pytest.mark.asyncio
async def test_creating_a_new_file_needs_no_prior_read():
    """The acceptance task creates a module that does not exist; that must work."""
    ledger = agent_tools.FileVersionLedger()
    new = REPO_ROOT / "backend/tests/_concurrency_new.txt"
    try:
        out = await call("write_file", {"path": "backend/tests/_concurrency_new.txt",
                                        "content": "fresh"}, ledger)
        assert "error" not in out and out["created"] is True
        assert new.read_text(encoding="utf-8") == "fresh"
    finally:
        if new.exists():
            new.unlink()


@pytest.mark.asyncio
async def test_deletion_after_inspection_is_a_conflict(target):
    ledger = agent_tools.FileVersionLedger()
    await call("read_file", {"path": REL}, ledger)
    target.unlink()
    out = await call("write_file", {"path": REL, "content": AGENT_WRITE}, ledger)
    assert out["error"] == "concurrent_change"
    assert out["current_version"] is None
    assert not target.exists(), "a refused write must not create the file"


@pytest.mark.asyncio
async def test_a_second_write_in_the_same_task_is_allowed(target):
    """The agent knows the state it just wrote, so it may revise it."""
    ledger = agent_tools.FileVersionLedger()
    await call("read_file", {"path": REL}, ledger)
    await call("write_file", {"path": REL, "content": "first"}, ledger)
    out = await call("write_file", {"path": REL, "content": "second"}, ledger)
    assert "error" not in out
    assert target.read_text(encoding="utf-8") == "second"


@pytest.mark.asyncio
async def test_one_tasks_inspection_does_not_authorise_another(target):
    """Two agents running concurrently must not vouch for each other's reads."""
    task_a = agent_tools.FileVersionLedger()
    task_b = agent_tools.FileVersionLedger()

    await call("read_file", {"path": REL}, task_a)
    out = await call("write_file", {"path": REL, "content": AGENT_WRITE}, task_b)
    assert out["error"] == "unverified_overwrite"
    assert target.read_text(encoding="utf-8") == ORIGINAL


# ── end to end through the runtime, across repair attempts ───────────────────

@pytest.mark.asyncio
async def test_conflict_survives_across_repair_attempts_and_is_audited(target):
    """A file read in attempt 1 and written in attempt 2 is still checked.

    Also proves the conflict does not consume the attempt budget silently: the
    existing 3-attempt bound is preserved and the refusal is real evidence in
    the audit.
    """
    state = {"attempt": 0}

    async def driver(system, user, tools, execute):
        state["attempt"] += 1
        n = state["attempt"]
        if n == 1:
            await execute("read_file", {"path": REL})
            # a human edits the file between attempts
            target.write_bytes(HUMAN_EDIT.encode("utf-8"))
        elif n == 2:
            await execute("write_file", {"path": REL, "content": AGENT_WRITE})
        else:
            await execute("read_file", {"path": REL})
            await execute("write_file", {"path": REL, "content": AGENT_WRITE})

    audit = await rt.run_task(
        "edit the fixture", system_prompt="test", model_call=driver,
    )

    assert audit["attempts"] == 3, "the 3-attempt bound must be preserved"
    conflicts = [f for f in audit["failures"] if f.get("error") == "concurrent_change"]
    assert len(conflicts) == 1, audit["failures"]
    assert REL in (conflicts[0].get("detail") or "")

    # attempt 3 re-read first, so its write was allowed
    writes = [a for a in audit["actions"] if a["tool"] == "write_file"]
    assert [a["ok"] for a in writes] == [False, True]
    assert target.read_text(encoding="utf-8") == AGENT_WRITE


@pytest.mark.asyncio
async def test_the_model_cannot_supply_its_own_ledger(target):
    """An agent must not vouch for a file it has not read."""
    ledger = agent_tools.FileVersionLedger()
    forged = agent_tools.FileVersionLedger()
    forged.record(REL, agent_tools.file_version(target))

    out = json.loads(await agent_tools.execute_engineering_tool(
        "write_file",
        {"path": REL, "content": AGENT_WRITE, "ledger": forged},
        ledger=ledger,
    ))
    assert out["error"] == "unverified_overwrite"
    assert target.read_text(encoding="utf-8") == ORIGINAL
