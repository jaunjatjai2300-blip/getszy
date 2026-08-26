"""Convergence: one authoritative engineering runtime, one guarded path to the disk.

Getszy has two loops that both call themselves "agent", and they are NOT rivals:

  * agent_runtime.py    — the autonomous ENGINEERING runtime. Touches the
                          repository: files, git, pytest. Bounded repair,
                          evidence-only verification, approval gates.
  * chat_builder/agent_loop.py — a PRODUCT/CONTENT orchestration loop. Runs
                          commerce capabilities (scripts, videos, storefronts)
                          through `process_message`. It has no repository access
                          at all.

Converging them would be wrong: they solve different problems, and folding the
commerce loop into the engineering runtime would delete working functionality.
What matters instead is that the boundary between them is REAL and stays real.

These tests are structural, parsed from the actual import graph and call graph,
so they fail if someone later wires the product loop to the disk, or routes an
agent around agent_guard. A comment saying "don't do this" would not.
"""
import ast
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("JWT_SECRET", "test-only-agent-converge-secret-32chr!")

BACKEND = Path(__file__).resolve().parent.parent

# Every module an autonomous engineering agent can execute through.
AGENT_MODULES = [
    "agent_runtime.py", "agent_tools.py", "agent_guard.py", "agent_llm.py",
    "agent_factory.py", "agent_delegation.py", "agent_research.py",
    "agent_knowledge.py", "agent_evidence.py", "agent_persistence.py",
]

# git_ops functions that change repository state.
GIT_OPS_MUTATIONS = {
    "git_commit", "git_push", "git_pull", "git_rollback", "git_checkout",
    "git_branch_create", "git_clone", "git_init",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    return found


def _source(name: str) -> str:
    return (BACKEND / name).read_text(encoding="utf-8")


# ── 1. no agent path reaches raw git_ops ─────────────────────────────────────

@pytest.mark.parametrize("module", AGENT_MODULES)
def test_no_agent_module_imports_git_ops(module):
    """git_ops has no sandbox, no approval gate and no audit trail.

    An agent reaching it would sidestep every control at once. The engineering
    tools shell out to git themselves, through agent_guard-checked paths.
    """
    assert "git_ops" not in _imports(BACKEND / module), (
        f"{module} imports git_ops, which bypasses agent_guard entirely"
    )


@pytest.mark.parametrize("module", AGENT_MODULES)
def test_no_agent_module_calls_a_git_ops_mutation(module):
    """Belt and braces: catch a call even if the import were disguised."""
    src = _source(module)
    for fn in GIT_OPS_MUTATIONS:
        assert f"git_ops.{fn}" not in src, f"{module} calls git_ops.{fn}"


def test_the_toolset_documents_how_it_actually_reaches_git():
    """The docstring must not claim a path the code does not take.

    agent_tools once said it used git_ops. It does not -- it runs git directly
    through guard-checked paths. A false claim here would send a future auditor
    looking at the wrong module for the security boundary.
    """
    src = _source("agent_tools.py")
    head = src[:src.index('"""', 3)]
    # Naming git_ops is fine — and useful — as long as it is to disclaim it.
    assert "real git via" not in head, "docstring still claims git runs via git_ops"
    if "git_ops" in head:
        assert "do NOT" in head or "does NOT" in head or "not use" in head, (
            "docstring mentions git_ops without making clear it is not the path taken"
        )


# ── 2. the product loop has no repository reach ──────────────────────────────

def test_the_product_loop_cannot_touch_the_repository():
    """chat_builder/agent_loop.py runs commerce capabilities, not engineering."""
    loop = BACKEND / "chat_builder" / "agent_loop.py"
    imported = _imports(loop)
    for forbidden in ("git_ops", "agent_tools", "agent_guard", "subprocess", "shutil"):
        assert forbidden not in imported, (
            f"agent_loop imports {forbidden}; the product loop must not reach the disk"
        )


def test_the_product_loop_performs_no_filesystem_writes():
    src = (BACKEND / "chat_builder" / "agent_loop.py").read_text(encoding="utf-8")
    for pattern in (".write_text(", ".write_bytes(", "os.remove(", "shutil.rmtree("):
        assert pattern not in src, f"agent_loop performs a filesystem write: {pattern}"


def test_no_commerce_capability_grants_repository_access():
    """A capability that could write the repo would be an unguarded side door."""
    from chat_builder.capabilities import CAPABILITIES

    try:
        from chat_builder.capabilities_ext import CAPABILITIES as EXT
    except Exception:
        EXT = {}

    everything = {**CAPABILITIES, **EXT}
    assert everything, "no capabilities loaded — the assertion would be vacuous"
    for name in everything:
        lowered = name.lower()
        for danger in ("git", "file_write", "write_file", "shell", "exec_", "deploy_repo"):
            assert danger not in lowered, f"capability '{name}' looks repository-facing"


def test_the_product_loop_is_not_an_engineering_runtime():
    """It must not import the engineering runtime and quietly become a second one."""
    imported = _imports(BACKEND / "chat_builder" / "agent_loop.py")
    assert "agent_runtime" not in imported
    assert "agent_delegation" not in imported


# ── 3. every repository mutation passes agent_guard ──────────────────────────

def _function_source(module_src: str, fn_name: str) -> str:
    tree = ast.parse(module_src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == fn_name:
            return ast.get_source_segment(module_src, node) or ""
    raise AssertionError(f"{fn_name} not found")


@pytest.mark.parametrize("tool,guard_call", [
    ("write_file", "assert_writable"),
    ("read_file", "assert_readable"),
    ("list_files", "assert_readable"),
    ("grep_repo", "assert_readable"),
    ("git_commit", "assert_writable"),
    ("git_push", "require_approval"),
    ("run_tests", "assert_readable"),
])
def test_each_path_touching_tool_calls_the_guard(tool, guard_call):
    src = _source("agent_tools.py")
    body = _function_source(src, tool)
    assert guard_call in body, f"{tool} does not call {guard_call}; it would bypass the sandbox"


def test_commit_refuses_to_stage_everything():
    """`git add .` would sweep in files the agent never inspected."""
    body = _function_source(_source("agent_tools.py"), "git_commit")
    assert '"git", "add", "--sparse", *safe' in body or "'git', 'add'" in body
    for sweeping in ('"add", "-A"', '"add", "."', "'add', '-A'", "'add', '.'"):
        assert sweeping not in body, f"git_commit stages everything via {sweeping}"


def test_only_the_dispatcher_executes_tools():
    """A caller reaching a tool function directly would skip approvals and the ledger."""
    src = _source("agent_runtime.py")
    assert "execute_engineering_tool" in src
    for direct in ("agent_tools.write_file(", "agent_tools.git_commit(", "agent_tools.git_push("):
        assert direct not in src, f"agent_runtime calls {direct} outside the dispatcher"


# ── 4. the authoritative runtime keeps its guarantees ────────────────────────

def test_the_repair_bound_is_three():
    import agent_runtime as rt

    assert rt.MAX_REPAIR_ATTEMPTS == 3


def test_verification_requires_real_test_evidence():
    """A model's claim must never constitute success."""
    import asyncio

    import agent_runtime as rt

    empty = rt.AuditRecord(task_id="t", request="r")
    ok, why = asyncio.run(rt.verify(empty))
    assert ok is False and "No test run" in why

    claimed = rt.AuditRecord(task_id="t", request="r")
    claimed.plan = "I have completed the task successfully and all tests pass."
    ok, _ = asyncio.run(rt.verify(claimed))
    assert ok is False, "prose in the audit must not satisfy verification"

    failed = rt.AuditRecord(task_id="t", request="r")
    failed.tests = [{"passed": False, "exit_code": 1}]
    ok, _ = asyncio.run(rt.verify(failed))
    assert ok is False


def test_the_runtime_is_the_only_module_driving_the_tool_dispatcher():
    """One authoritative loop. A second driver would be a parallel runtime."""
    drivers = []
    for path in BACKEND.glob("*.py"):
        if path.name in {"agent_tools.py"} or path.name.startswith("acceptance_"):
            continue
        src = path.read_text(encoding="utf-8", errors="ignore")
        if "execute_engineering_tool(" in src and "await execute_engineering_tool" in src:
            drivers.append(path.name)
    assert drivers == ["agent_runtime.py"], (
        f"more than one module drives the engineering dispatcher: {drivers}"
    )


def test_secret_redaction_still_applies():
    import agent_runtime as rt

    out = rt._redact({"api_key": "sk-live-123", "token": "abc", "path": "backend/x.py"})
    assert out["api_key"] == "[redacted]" and out["token"] == "[redacted]"
    assert out["path"] == "backend/x.py"


# ── 5. the unguarded admin git surface is known and contained ────────────────

def test_the_raw_git_route_is_admin_only():
    """routes_git exposes real git mutations. It is a human admin tool, not an
    agent path -- but that is only true while every route on it requires admin."""
    src = _source("routes_git.py")
    tree = ast.parse(src)
    routes = [n for n in ast.walk(tree)
              if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and n.decorator_list]
    assert routes, "no routes found — the assertion would be vacuous"
    for fn in routes:
        body = ast.get_source_segment(src, fn) or ""
        assert "get_current_admin" in body, (
            f"routes_git.{fn.name} is not admin-gated; raw git would be reachable"
        )


def test_no_agent_tool_can_issue_an_http_request():
    """The one thing that would make the admin git surface agent-reachable.

    Agents have no HTTP tool, so they cannot call /admin/git/* even with a token.
    If an HTTP or shell tool is ever added, this fails and routes_git must be
    reconsidered at the same time.
    """
    import agent_tools

    for name in agent_tools.ENGINEERING_TOOLS:
        lowered = name.lower()
        for danger in ("http", "curl", "request", "fetch", "shell", "bash", "exec"):
            assert danger not in lowered, (
                f"tool '{name}' may reach the network or a shell; re-check routes_git"
            )
