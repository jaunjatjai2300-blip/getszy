"""Agent Factory — security guard.

Every tool the master agent can invoke passes through here first. This module is
deliberately separate from the tools themselves so the security decision cannot
be bypassed by adding a tool that forgets to check.

Three protections, in order of severity:

1. PATH SANDBOX — an agent may only read/write inside the repository. Absolute
   paths, symlink escapes and `..` traversal are rejected after resolution, not
   by string matching, so `a/../../etc/passwd` cannot slip through.

2. SELF-PROTECTION — the spec requires that an agent cannot silently modify its
   own security, permission, approval or factory-runtime controls. Those files
   are denied for WRITE even inside the sandbox; changing them requires a human.

3. APPROVAL GATE — destructive or outward-facing operations are refused unless
   an explicit approval token for that exact operation has been granted by a
   human. There is no "approve everything" mode.
"""
from __future__ import annotations

import os
from pathlib import Path

# Repository root the agent is allowed to operate in.
# SECURITY: this must never silently fall back to a filesystem root. An earlier
# version computed Path(__file__).resolve().parent.parent, which yields "/" when
# this module is not at <repo>/backend/agent_guard.py -- for example when the
# backend directory is bind-mounted alone into a container. The sandbox then
# contained the entire filesystem and every escape test passed trivially.
#
# The root is now DISCOVERED via a repository marker, VALIDATED, and the guard
# FAILS CLOSED when none can be established.

_MARKER = Path("backend") / "agent_guard.py"


def _is_filesystem_root(p: Path) -> bool:
    """True for a path with no parent above it ('/', 'C:\\')."""
    return p == p.parent


def _discover_repo_root():
    """Directory containing backend/agent_guard.py, or None if not found."""
    candidates = []
    override = os.environ.get("AGENT_REPO_ROOT")
    if override:
        candidates.append(Path(override))
    candidates.extend(Path(__file__).resolve().parents)
    for c in candidates:
        try:
            c = c.resolve()
        except Exception:
            continue
        if _is_filesystem_root(c):
            continue
        if (c / _MARKER).is_file():
            return c
    return None


REPO_ROOT = _discover_repo_root()
REPO_ROOT_VALID = REPO_ROOT is not None

# Files an agent may never write to. These ARE the controls; letting an agent
# edit them would let it grant itself permissions. Matched against the path
# relative to REPO_ROOT, so a rename cannot dodge the check by changing depth.
SELF_PROTECTED = {
    # The guard and the toolset: the security decision and its enforcement points.
    "backend/agent_guard.py",
    "backend/agent_tools.py",
    "backend/agent_audit.py",
    # The FACTORY RUNTIME. These decide how many repair attempts are allowed, what
    # counts as verified success, which approvals are carried, and whether a stored
    # agent config is trusted. An agent able to write these could rewrite verify()
    # to always return True, or lift its own approval gate -- the spec forbids an
    # agent silently modifying its own permission, approval or factory-runtime
    # controls, and the guard alone does not cover them.
    "backend/agent_runtime.py",
    "backend/agent_factory.py",
    "backend/agent_llm.py",
    "backend/agent_persistence.py",
    "backend/agent_delegation.py",
    "backend/agent_roles.py",
    "backend/agent_evidence.py",
    "backend/agent_knowledge.py",
    "backend/agent_memory.py",
    "backend/repo_map.py",
    "backend/agent_research.py",
    "backend/acceptance_agent_factory.py",
    "backend/acceptance_persistence.py",
    "backend/acceptance_delegation.py",
    "backend/routes_agent_factory.py",
    # Platform security and money.
    "backend/auth.py",
    "backend/credits.py",
    "backend/routes_razorpay.py",
    "backend/middleware.py",
    "backend/redis_rate_limit.py",
    "backend/metrics_protect.py",
}

# ── the two-tier contract ────────────────────────────────────────────────────
#
# TIER 1 — CAPABILITY. Which tools an agent may invoke at all. Decided by its
# validated allowed_tools and enforced at the executor. read_file, write_file,
# run_tests and the rest live here: they are ordinary engineering work.
#
# TIER 2 — AUTHORISATION. Which OPERATIONS additionally require an explicit
# human token, whatever capabilities the agent holds. These are destructive,
# outward-facing or financial.
#
# The tiers are orthogonal. Holding a capability never implies authorisation,
# and an approval never grants a capability. A few names appear in both -- a
# tool whose invocation IS the gated operation, like git_push -- and those must
# clear both tiers.
#
# A model that names a tool where an approval belongs is making a category
# error, and the fix is to correct the model's information, never to move the
# tool into tier 2. Approval-gating run_tests would put a human in front of
# verification itself, and evidence-only success depends on the agent being able
# to run the tests unaided.

# Operations that always require a human approval token, never auto-granted.
APPROVAL_REQUIRED = {
    "git_push",
    "git_reset",
    "git_force_push",
    "deploy",
    "db_delete",
    "db_migrate",
    "secrets_write",
    "payment_change",
    "install_dependency",
}

# Ordinary engineering capabilities. These must NEVER require approval.
NEVER_APPROVAL_GATED = {
    # inspection
    "read_file", "list_files", "grep_repo", "git_status", "git_diff", "git_log",
    # change and verification
    "write_file", "git_commit", "run_tests",
    # read-only research
    "github_search_code", "github_search_repositories", "github_search_issues",
    "github_read_file", "web_search",
    # codebase retrieval + structural map (read-only, in-repo)
    "search_codebase",
    "repo_map_query",
    # delegation
    "spawn_specialist", "spawn_specialists",
}

_TIER_OVERLAP = NEVER_APPROVAL_GATED & APPROVAL_REQUIRED
if _TIER_OVERLAP:
    # Fail at import, not at runtime. This is the exact mistake the contract
    # exists to prevent: quietly gating an engineering tool to satisfy a model
    # that mislabelled it, and thereby requiring a human to run the tests.
    raise RuntimeError(
        f"Agent two-tier contract violated: {sorted(_TIER_OVERLAP)} are engineering "
        "capabilities and must never be approval-gated operations. Correct the "
        "caller instead of moving a tool into APPROVAL_REQUIRED."
    )


def is_approval_gated(operation: str) -> bool:
    """Whether this operation needs an explicit human token."""
    return operation in APPROVAL_REQUIRED


def classify(name: str) -> str:
    """Which tier a name belongs to: 'capability', 'gated', or 'unknown'.

    'gated' covers a tool whose invocation is itself the controlled operation.
    """
    if name in NEVER_APPROVAL_GATED:
        return "capability"
    if name in APPROVAL_REQUIRED:
        return "gated"
    return "unknown"


class GuardDenied(PermissionError):
    """Raised when the guard refuses an operation. Never caught internally."""


class ApprovalRequired(PermissionError):
    """Raised when an operation needs a human approval token it does not have."""


def resolve_in_repo(relative_path: str) -> Path:
    """Resolve a path and prove it stays inside the repository.

    Resolution happens BEFORE the containment check so symlinks and `..` are
    already collapsed — string-prefix checks alone are not sufficient.
    """
    if not REPO_ROOT_VALID:
        # Fail closed: without a validated root there is no sandbox to enforce,
        # so no path operation may proceed.
        raise GuardDenied(
            "Agent sandbox is not configured: no repository root containing "
            "backend/agent_guard.py was found. Set AGENT_REPO_ROOT. "
            "Refusing all path operations."
        )
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise GuardDenied("A path is required.")
    if "\x00" in relative_path:
        raise GuardDenied("Null byte in path.")

    candidate = (REPO_ROOT / relative_path).resolve()
    try:
        candidate.relative_to(REPO_ROOT)
    except ValueError:
        raise GuardDenied(
            f"Path escapes the repository sandbox: {relative_path!r} -> {candidate}"
        )
    return candidate


def rel_to_repo(path: Path) -> str:
    """Repo-relative POSIX path, for comparison against SELF_PROTECTED."""
    return path.relative_to(REPO_ROOT).as_posix()


def assert_writable(relative_path: str) -> Path:
    """Resolve a path for WRITING, refusing self-protected control files."""
    resolved = resolve_in_repo(relative_path)
    rel = rel_to_repo(resolved)
    if rel in SELF_PROTECTED:
        raise GuardDenied(
            f"'{rel}' governs agent security/permissions and cannot be modified "
            "by an agent. This change requires a human."
        )
    return resolved


def assert_readable(relative_path: str) -> Path:
    """Resolve a path for READING. Self-protected files may be read, not written —
    an agent should be able to reason about its own constraints."""
    return resolve_in_repo(relative_path)


def require_approval(operation: str, approvals: set[str] | None) -> None:
    """Refuse an approval-gated operation unless a token for THIS operation exists.

    `approvals` is the set of operations a human explicitly approved for this
    task. A token for one operation never authorises another.
    """
    if operation not in APPROVAL_REQUIRED:
        return
    granted = approvals or set()
    if operation not in granted:
        raise ApprovalRequired(
            f"'{operation}' requires explicit human approval and none was granted "
            f"for this task. Granted: {sorted(granted) or 'none'}"
        )
