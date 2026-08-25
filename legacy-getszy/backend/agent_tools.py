"""Agent Factory — real engineering tools.

The existing `tools.py` registry is commerce-only (products, courses, pricing).
The master agent needs to inspect and modify a repository, so these are the
engineering tools, kept in a separate registry with its own schemas.

Everything here is REAL: real filesystem reads, real ripgrep/grep, real git via
the existing `git_ops`, real pytest execution. Nothing is mocked or simulated —
a tool that cannot do the real thing raises instead of returning a plausible
string, because a fabricated tool result is worse than a failure.

Every path-touching tool goes through `agent_guard` first.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

from agent_guard import (
    REPO_ROOT,
    ApprovalRequired,
    GuardDenied,
    assert_readable,
    assert_writable,
    rel_to_repo,
    require_approval,
)

MAX_READ_BYTES = 200_000
MAX_GREP_MATCHES = 200


# ── read-only inspection ─────────────────────────────────────────────────────

async def read_file(path: str, max_bytes: int = MAX_READ_BYTES) -> str:
    """Read a repository file. Truncates rather than blowing up the context."""
    p = assert_readable(path)
    if not p.is_file():
        return json.dumps({"error": f"Not a file: {path}"})
    data = p.read_bytes()[: int(max_bytes)]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return json.dumps({"error": f"Binary file, cannot read as text: {path}"})
    return json.dumps({
        "path": rel_to_repo(p),
        "bytes": p.stat().st_size,
        "truncated": p.stat().st_size > int(max_bytes),
        "content": text,
    })


async def list_files(path: str = ".", pattern: str = "*", limit: int = 200) -> str:
    """List files under a directory, newest first."""
    d = assert_readable(path)
    if not d.is_dir():
        return json.dumps({"error": f"Not a directory: {path}"})
    hits = []
    for f in d.rglob(pattern):
        if not f.is_file():
            continue
        if any(part in {".git", "node_modules", "__pycache__", "build", "dist"} for part in f.parts):
            continue
        hits.append(f)
        if len(hits) >= int(limit) * 3:
            break
    hits.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return json.dumps({
        "dir": rel_to_repo(d),
        "count": len(hits[: int(limit)]),
        "files": [rel_to_repo(f) for f in hits[: int(limit)]],
    })


async def grep_repo(pattern: str, path: str = ".", glob: str = "") -> str:
    """Search file contents. Uses ripgrep, then grep, then a pure-Python scan.

    A search that COULD NOT RUN must never look like a search that found nothing.
    An earlier version returned `matches: 0` when the grep binary was absent
    (exit 127), which would tell an agent "this symbol does not exist" about a
    repository it had not actually searched. Exit 1 means no matches; anything
    above that is a failure and is reported as one.
    """
    d = assert_readable(path)
    cmd = None
    if _has(["rg", "--version"]):
        cmd = ["rg", "-n", "--no-heading", "-m", str(MAX_GREP_MATCHES), pattern, str(d)]
        if glob:
            cmd[1:1] = ["--glob", glob]
    elif _has(["grep", "--version"]):
        cmd = ["grep", "-rn", "--exclude-dir=.git", "--exclude-dir=node_modules", pattern, str(d)]

    if cmd is not None:
        out = _run(cmd)
        if out["code"] > 1:
            return json.dumps({
                "error": "search_failed",
                "detail": f"exit {out['code']}: {(out['stderr'] or '').strip()[:400]}",
            })
        lines = [ln for ln in out["stdout"].splitlines() if ln][:MAX_GREP_MATCHES]
        return json.dumps({"pattern": pattern, "matches": len(lines), "lines": lines})

    return _python_grep(pattern, d, glob)


def _python_grep(pattern: str, root: Path, glob: str = "") -> str:
    """Fallback scan, so the toolset does not depend on an external binary."""
    import re

    try:
        rx = re.compile(pattern)
    except re.error as e:
        return json.dumps({"error": "bad_pattern", "detail": str(e)})

    lines: list[str] = []
    targets = root.rglob(glob or "*") if root.is_dir() else [root]
    for f in targets:
        if not f.is_file():
            continue
        if any(p in {".git", "node_modules", "__pycache__", "build", "dist"} for p in f.parts):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                lines.append(f"{f}:{n}:{line[:300]}")
                if len(lines) >= MAX_GREP_MATCHES:
                    return json.dumps({"pattern": pattern, "matches": len(lines), "lines": lines})
    return json.dumps({"pattern": pattern, "matches": len(lines), "lines": lines})


# ── write (guarded) ──────────────────────────────────────────────────────────

async def write_file(path: str, content: str) -> str:
    """Write a repository file. Refused for self-protected control files."""
    p = assert_writable(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    existed = p.exists()
    before = p.read_text(encoding="utf-8") if existed else None
    p.write_text(content, encoding="utf-8")
    return json.dumps({
        "path": rel_to_repo(p),
        "created": not existed,
        "bytes_written": len(content.encode("utf-8")),
        "previous_bytes": len(before.encode("utf-8")) if before is not None else 0,
    })


# ── git (read-only here; mutating git is approval-gated) ─────────────────────

async def git_status() -> str:
    out = _run(["git", "status", "--short", "--branch"])
    return json.dumps({"ok": out["ok"], "output": out["stdout"][:8000]})


async def git_diff(path: str = "", staged: bool = False) -> str:
    cmd = ["git", "diff"] + (["--cached"] if staged else [])
    if path:
        cmd += ["--", str(assert_readable(path))]
    out = _run(cmd)
    return json.dumps({"ok": out["ok"], "diff": out["stdout"][:20000]})


async def git_log(limit: int = 10) -> str:
    out = _run(["git", "log", "--oneline", f"-{int(limit)}"])
    return json.dumps({"ok": out["ok"], "log": out["stdout"]})


async def git_commit(message: str, paths: list[str] | None = None, approvals=None) -> str:
    """Stage specific paths and commit. Committing is allowed; PUSHING is not.

    Paths are individually guarded, so a commit cannot sweep in a self-protected
    control file that was modified by other means.
    """
    if not message or not message.strip():
        return json.dumps({"error": "A commit message is required."})
    targets = paths or []
    if not targets:
        return json.dumps({"error": "Explicit paths are required; refusing to 'git add -A'."})
    safe = [str(assert_writable(p)) for p in targets]
    add = _run(["git", "add", "--sparse", *safe])
    if not add["ok"]:
        return json.dumps({"error": "git add failed", "stderr": add["stderr"][:2000]})
    com = _run(["git", "commit", "-m", message])
    head = _run(["git", "rev-parse", "HEAD"])
    return json.dumps({
        "ok": com["ok"],
        "commit": head["stdout"].strip()[:40] if head["ok"] else None,
        "output": (com["stdout"] + com["stderr"])[:4000],
    })


async def git_push(remote: str = "origin", branch: str = "", approvals=None) -> str:
    """Pushing is outward-facing and always approval-gated."""
    require_approval("git_push", approvals)
    cmd = ["git", "push", remote] + ([branch] if branch else [])
    out = _run(cmd)
    return json.dumps({"ok": out["ok"], "output": (out["stdout"] + out["stderr"])[:4000]})


# ── verification ─────────────────────────────────────────────────────────────

async def run_tests(target: str = "", timeout: int = 300) -> str:
    """Run the real pytest suite. Returns the real exit code and output.

    Never reports success on a non-zero exit — the caller must be able to trust
    that a pass is a pass.
    """
    backend = REPO_ROOT / "backend"
    cmd = ["python", "-m", "pytest", "-q"]
    if target:
        cmd.append(str(assert_readable(target)))
    out = _run(cmd, cwd=backend, timeout=timeout)
    tail = (out["stdout"] + out["stderr"]).strip().splitlines()[-25:]
    return json.dumps({
        "exit_code": out["code"],
        "passed": out["code"] == 0,
        "output": "\n".join(tail),
    })


# ── plumbing ─────────────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 60) -> dict:
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=str(cwd or REPO_ROOT)
        )
        return {"ok": r.returncode == 0, "code": r.returncode, "stdout": r.stdout, "stderr": r.stderr}
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": 124, "stdout": "", "stderr": f"timeout after {timeout}s"}
    except FileNotFoundError as e:
        return {"ok": False, "code": 127, "stdout": "", "stderr": str(e)}


def _has(cmd: list[str]) -> bool:
    try:
        subprocess.run(cmd, capture_output=True, timeout=5)
        return True
    except Exception:
        return False


ENGINEERING_TOOLS = {
    "read_file": read_file,
    "list_files": list_files,
    "grep_repo": grep_repo,
    "write_file": write_file,
    "git_status": git_status,
    "git_diff": git_diff,
    "git_log": git_log,
    "git_commit": git_commit,
    "git_push": git_push,
    "run_tests": run_tests,
}

# Operations that mutate or reach outside the repo — surfaced so the runtime and
# the audit trail can flag them without re-deriving the list.
MUTATING_TOOLS = {"write_file", "git_commit", "git_push"}


def _schema(name: str, desc: str, props: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


ENGINEERING_SCHEMAS = [
    _schema("read_file", "Read a file from the repository.",
            {"path": {"type": "string"}, "max_bytes": {"type": "integer"}}, ["path"]),
    _schema("list_files", "List files under a repository directory.",
            {"path": {"type": "string"}, "pattern": {"type": "string"}, "limit": {"type": "integer"}}, []),
    _schema("grep_repo", "Search repository file contents for a regex pattern.",
            {"pattern": {"type": "string"}, "path": {"type": "string"}, "glob": {"type": "string"}}, ["pattern"]),
    _schema("write_file", "Write a repository file. Refused for protected control files.",
            {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    _schema("git_status", "Show git status.", {}, []),
    _schema("git_diff", "Show git diff.", {"path": {"type": "string"}, "staged": {"type": "boolean"}}, []),
    _schema("git_log", "Show recent commits.", {"limit": {"type": "integer"}}, []),
    _schema("git_commit", "Stage explicit paths and commit.",
            {"message": {"type": "string"}, "paths": {"type": "array", "items": {"type": "string"}}},
            ["message", "paths"]),
    _schema("git_push", "Push to a remote. Requires human approval.",
            {"remote": {"type": "string"}, "branch": {"type": "string"}}, []),
    _schema("run_tests", "Run the real pytest suite and return the real exit code.",
            {"target": {"type": "string"}, "timeout": {"type": "integer"}}, []),
]


async def execute_engineering_tool(name: str, arguments: dict, approvals: set[str] | None = None) -> str:
    """Dispatch one engineering tool.

    Guard failures are returned to the model as structured errors rather than
    raised, so the agent can adapt — but the operation genuinely did not happen.
    """
    fn = ENGINEERING_TOOLS.get(name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {name}"})
    args = dict(arguments or {})
    try:
        if name in {"git_commit", "git_push"}:
            args["approvals"] = approvals
        result = fn(**args)
        return await result if asyncio.iscoroutine(result) else str(result)
    except ApprovalRequired as e:
        return json.dumps({"error": "approval_required", "detail": str(e)})
    except GuardDenied as e:
        return json.dumps({"error": "guard_denied", "detail": str(e)})
    except TypeError as e:
        return json.dumps({"error": "bad_arguments", "detail": str(e)})
