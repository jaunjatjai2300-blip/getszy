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
