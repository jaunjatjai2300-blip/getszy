"""Security tests for the Agent Factory guard and engineering tools.

These assert the properties the spec calls non-negotiable: an agent cannot escape
the repository, cannot modify its own security controls, and cannot perform
approval-gated operations without an explicit token for that exact operation.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("JWT_SECRET", "test-only-agent-guard-secret-32-chars!!")

from agent_guard import (  # noqa: E402
    APPROVAL_REQUIRED,
    SELF_PROTECTED,
    ApprovalRequired,
    GuardDenied,
    assert_readable,
    assert_writable,
    require_approval,
    resolve_in_repo,
)
import agent_tools  # noqa: E402


# ── 1. path sandbox ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("escape", [
    "../../../../etc/passwd",
    "backend/../../../../etc/shadow",
    "/etc/passwd",
    "backend/../../..",
])
def test_sandbox_rejects_paths_that_escape_the_repo(escape):
    with pytest.raises(GuardDenied):
        resolve_in_repo(escape)


def test_sandbox_rejects_empty_and_null_byte_paths():
    for bad in ["", "   ", "back\x00end/auth.py"]:
        with pytest.raises(GuardDenied):
            resolve_in_repo(bad)


def test_sandbox_allows_a_real_repo_path():
    p = resolve_in_repo("backend/agent_guard.py")
    assert p.is_file()


# ── 2. self-protection ───────────────────────────────────────────────────────

@pytest.mark.parametrize("protected", sorted(SELF_PROTECTED))
def test_agent_cannot_write_its_own_security_controls(protected):
    with pytest.raises(GuardDenied):
        assert_writable(protected)


def test_self_protected_files_remain_readable():
    # An agent should be able to reason about its own constraints, just not edit them.
    assert assert_readable("backend/agent_guard.py").is_file()


def test_self_protection_survives_traversal_dodge():
    # A path that resolves to a protected file must still be refused, even when
    # written in a form that does not textually match the protected entry.
    with pytest.raises(GuardDenied):
        assert_writable("backend/../backend/auth.py")


# ── 3. approval gate ─────────────────────────────────────────────────────────

def test_gated_operation_refused_without_token():
    with pytest.raises(ApprovalRequired):
        require_approval("git_push", None)
    with pytest.raises(ApprovalRequired):
        require_approval("git_push", set())


def test_token_for_one_operation_does_not_authorise_another():
    with pytest.raises(ApprovalRequired):
        require_approval("deploy", {"git_push"})


def test_gated_operation_allowed_with_its_own_token():
    require_approval("git_push", {"git_push"})  # must not raise


def test_ungated_operation_needs_no_token():
    require_approval("read_file", None)  # must not raise


def test_destructive_operations_are_actually_gated():
    for op in ["git_push", "deploy", "db_delete", "secrets_write", "payment_change"]:
        assert op in APPROVAL_REQUIRED


# ── 4. tool-level enforcement (not just the guard in isolation) ──────────────

@pytest.mark.asyncio
async def test_write_tool_refuses_protected_file():
    out = json.loads(await agent_tools.execute_engineering_tool(
        "write_file", {"path": "backend/auth.py", "content": "compromised"}
    ))
    assert out["error"] == "guard_denied"


@pytest.mark.asyncio
async def test_write_tool_refuses_sandbox_escape():
    out = json.loads(await agent_tools.execute_engineering_tool(
        "write_file", {"path": "../../evil.txt", "content": "x"}
    ))
    assert out["error"] == "guard_denied"


@pytest.mark.asyncio
async def test_push_tool_refuses_without_approval():
    out = json.loads(await agent_tools.execute_engineering_tool(
        "git_push", {"remote": "origin"}, approvals=None
    ))
    assert out["error"] == "approval_required"


@pytest.mark.asyncio
async def test_commit_refuses_without_explicit_paths():
    out = json.loads(await agent_tools.execute_engineering_tool(
        "git_commit", {"message": "sweep everything", "paths": []}
    ))
    assert "error" in out and "paths" in out["error"].lower()


@pytest.mark.asyncio
async def test_unknown_tool_is_rejected():
    out = json.loads(await agent_tools.execute_engineering_tool("rm_rf", {}))
    assert "Unknown tool" in out["error"]


# ── 5. read-only tools really work against the real repo ────────────────────

@pytest.mark.asyncio
async def test_read_file_returns_real_content():
    out = json.loads(await agent_tools.execute_engineering_tool(
        "read_file", {"path": "backend/agent_guard.py"}
    ))
    assert "SELF_PROTECTED" in out["content"]
    assert out["bytes"] > 0


@pytest.mark.asyncio
async def test_grep_finds_a_known_symbol():
    out = json.loads(await agent_tools.execute_engineering_tool(
        "grep_repo", {"pattern": "SELF_PROTECTED", "path": "backend"}
    ))
    assert out["matches"] > 0


@pytest.mark.asyncio
async def test_schemas_cover_every_registered_tool():
    named = {s["function"]["name"] for s in agent_tools.ENGINEERING_SCHEMAS}
    assert named == set(agent_tools.ENGINEERING_TOOLS)
