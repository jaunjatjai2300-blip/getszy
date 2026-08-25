#!/usr/bin/env python
"""Agent Factory — REAL model-driven DELEGATION acceptance test.

A real local model acts as the master, decides to delegate, and a second real
model run acts as the specialist. Nothing is scripted: no deterministic driver,
no mock LLM, no simulated child.

HOW DELEGATION IS PROVED RATHER THAN ASSUMED
--------------------------------------------
A master holding write_file could quietly do the work itself and the run would
still look successful, so the proof is made structural rather than hopeful: the
master's OWN tool scope excludes write_file, while its DELEGATION scope still
includes it. The child therefore inherits write_file legitimately and the
child-subset-of-parent invariant is untouched, but the master's executor refuses
the tool outright.

The audit then has to show:

    the MASTER's own tool calls contain spawn_specialist
    the MASTER's write_file attempts, if any, were all refused
    the CHILD's tool calls contain write_file and run_tests

If the implementation file exists at the end, a specialist wrote it, because
nothing else could have.

Everything else matches acceptance_agent_factory.py: the task is proven undone
first, the agent's own test result is ignored in favour of a pytest run this
script performs itself, and the commit is verified with git rather than believed.

Reuses the preflight, capacity gate and git plumbing from
acceptance_agent_factory rather than duplicating them.

Run:
    python acceptance_delegation.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The specialist runs pytest in a SUBPROCESS. If that process cannot import the
# application because JWT_SECRET is absent, the suite fails for a reason that has
# nothing to do with the delegated task -- and the harness would record the
# specialist as having failed. Set a strong ephemeral secret so an environment
# gap cannot be mistaken for an agent failure.
#
# This does not weaken authentication: the value is freshly random per run, is
# never written anywhere, and auth.py's real strength check still applies to it.
# Anything already supplied by the operator wins.
if not os.environ.get("JWT_SECRET"):
    import secrets

    os.environ["JWT_SECRET"] = secrets.token_urlsafe(48)
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("INTEGRATION_ENCRYPTION_KEY", __import__("base64").urlsafe_b64encode(
    __import__("secrets").token_bytes(32)).decode())

import agent_delegation as dg  # noqa: E402
import agent_guard as guard  # noqa: E402
import agent_llm  # noqa: E402
import agent_runtime as runtime  # noqa: E402
import agent_tools  # noqa: E402
from acceptance_agent_factory import (  # noqa: E402
    Preflight, brief, git, log, memory_gb, model_sizes_gb, preflight,
    sandbox_relative, sh,
)
from agent_tools import execute_engineering_tool  # noqa: E402

IMPL_PATH = "backend/text_case.py"
FIXTURE_PATH = "backend/tests/test_text_case.py"

SPECIALIST = (
    "Senior Python backend engineer who implements small utility modules, "
    "runs pytest to verify real behaviour and debugs failing tests."
)

MASTER_PROMPT = (
    "You are the Getszy master engineering agent. You coordinate work and you "
    "DELEGATE implementation to specialists rather than writing code yourself.\n\n"
    "Rules you cannot override:\n"
    "- Work only inside the repository sandbox.\n"
    "- Never claim success without evidence. Read the real tool results.\n"
    "- Delegate implementation using spawn_specialist. Describe the specialist in "
    "plain words and give it a precise task.\n"
    "- A specialist returns structured evidence. Read its 'verification' field.\n"
    "- Never fabricate a tool result or a test outcome."
)

TASK = f"""The pytest file {FIXTURE_PATH} is failing because the module it imports
does not exist yet.

Do NOT write the code yourself. Delegate it:

1. Call spawn_specialist with a description of a senior Python backend engineer,
   and a task telling it to read {FIXTURE_PATH}, create {IMPL_PATH} so the tests
   pass, and then run run_tests with target exactly "{FIXTURE_PATH}" to confirm.
   Tell it to run ONLY that target, never the whole suite.
2. Read the structured evidence the specialist returns.
3. If its verification says verified, check git status and commit exactly
   {IMPL_PATH} and {FIXTURE_PATH}.
4. If it did not verify, report the failure. Do not call it a success.
"""

FIXTURE_SOURCE = '''"""Acceptance fixture for the delegation test. Deleted and rewritten per run."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from text_case import to_snake_case


def test_splits_camel_case():
    assert to_snake_case("orderTotal") == "order_total"


def test_handles_consecutive_capitals():
    assert to_snake_case("parseHTTPResponse") == "parse_http_response"


def test_spaces_and_hyphens_become_underscores():
    assert to_snake_case("Order Total-Value") == "order_total_value"


def test_already_snake_case_is_unchanged():
    assert to_snake_case("order_total") == "order_total"


def test_empty_string():
    assert to_snake_case("") == ""
'''

MASTER_ROUNDS = 12
CHILD_ROUNDS = 16
MAX_ATTEMPTS = runtime.MAX_REPAIR_ATTEMPTS


def _model_factory(model):
    """Real pinned local model for every specialist. No customer provider chain."""
    def factory(tier):
        async def call(system, user, tools, execute):
            async def traced(name, args):
                log(f"      -> [child] {name}({brief(args, 110)})")
                out = await execute(name, args)
                log(f"         {brief(out, 150)}")
                return out
            return await agent_llm.engineering_tool_loop(
                system=system, user=user, execute=traced, tools=tools,
                provider="ollama", model=model, temperature=0.1,
                max_rounds=CHILD_ROUNDS,
            )
        return call
    return factory


async def main() -> int:
    started = time.time()
    report: dict = {"criteria": {}}

    try:
        env = preflight()
    except Preflight as e:
        print("PREFLIGHT FAILED\n", e, sep="")
        return 2
    report["environment"] = env
    log("== preflight ==")
    for k, v in env.items():
        log(f"  {k}: {v}")

    # ── model, with the same capacity gate that stopped the earlier OOM ──────
    tier = os.environ.get("ACCEPTANCE_TIER", "strong")
    model = os.environ.get("ACCEPTANCE_MODEL", "").strip() or agent_llm.model_for_tier(
        tier, env["installed_models"])
    if not model:
        log(f"No installed model satisfies tier '{tier}'. Installed: {env['installed_models']}")
        return 2
    if model not in env["installed_models"]:
        log(f"ACCEPTANCE_MODEL={model!r} is not installed.")
        return 2

    sizes, mem = model_sizes_gb(), memory_gb()
    need, have = sizes.get(model), mem.get("MemAvailable")
    report["model"] = model
    report["model_size_gb"] = need
    report["host_memory_gb"] = mem
    log(f"\n== capacity ==\n  {model}: {need or '?'} GB   available: {have or '?'} GB "
        f"of {mem.get('MemTotal') or '?'} GB")
    if need and have and need > have:
        if os.environ.get("ACCEPTANCE_ALLOW_OVERSIZED_MODEL") != "1":
            log(f"\nRefusing to run: {model} needs about {need} GB but only {have} GB is "
                f"available. Ollama would be OOM-killed and could take the host down.\n"
                f"Pin a smaller installed model with -e ACCEPTANCE_MODEL=<name>.")
            return 2
        log("  WARNING: oversized model at the operator's request.")

    # ── prove the task starts undone ────────────────────────────────────────
    impl = guard.REPO_ROOT / IMPL_PATH
    if impl.exists():
        impl.unlink()
        report["removed_existing_impl"] = True
    (guard.REPO_ROOT / FIXTURE_PATH).write_text(FIXTURE_SOURCE, encoding="utf-8", newline="")
    before = sh(sys.executable, "-m", "pytest", "-q", str(guard.REPO_ROOT / FIXTURE_PATH),
                cwd=guard.REPO_ROOT / "backend")
    report["fixture_failed_before_run"] = before["code"] != 0
    log(f"\n== baseline ==\n  fixture exit code before run: {before['code']}")
    if before["code"] == 0:
        log("Refusing to continue: the fixture already passes, so the test would be vacuous.")
        return 2

    head_before = git("rev-parse", "HEAD")["out"].strip()
    report["head_before"] = head_before

    # ── the master ──────────────────────────────────────────────────────────
    # The master may DELEGATE writing but may not perform it. Its delegation
    # context still carries the full scope, so a specialist inherits write_file
    # legitimately and the child-subset-of-parent invariant is untouched -- but
    # the master's OWN executor will refuse write_file.
    #
    # This makes the result decisive instead of hopeful: a master holding
    # write_file could quietly do the work itself and the run would still look
    # successful. With it removed, if the module exists at the end then a
    # specialist wrote it, because nothing else could have.
    delegable_tools = sorted(agent_tools.ENGINEERING_TOOLS)
    master_tools = [t for t in delegable_tools if t != "write_file"]
    report["master_own_tools"] = master_tools
    report["delegable_tools"] = delegable_tools
    report["model_note"] = (
        "qwen2.5-coder:14b is INSTALLED BUT NOT CAPACITY-VERIFIED on this hardware "
        f"(needs ~{sizes.get('qwen2.5-coder:14b', '9.0')} GB against "
        f"{have or '?'} GB available). It is not claimed as supported."
    )

    context = dg.master_context(
        task_id="", tools=frozenset(delegable_tools),
        approvals=set(),            # no approvals at all: push must stay refused
        delegable=set(),
        model_tier=tier,
        model_factory=_model_factory(model),
    )

    master_calls: list[str] = []
    spawn_results: list[dict] = []

    spawn_calls: list[dict] = []

    async def model_call(system, user, tools, execute):
        async def traced(name, args):
            master_calls.append(name)
            delegating = name in dg.DELEGATION_TOOLS
            # A delegation call is never truncated. The previous run's refusal
            # reason was hidden behind the 110-character cut, which turned a
            # diagnosable failure into a guess.
            log(f"    -> [master] {name}({json.dumps(args, default=str) if delegating else brief(args, 110)})")
            out = await execute(name, args)
            if delegating:
                spawn_calls.append(args)
                try:
                    parsed = json.loads(out)
                    spawn_results.append(parsed)
                    log(f"       status={parsed.get('status') or parsed.get('error')}")
                    for err in (parsed.get("errors") or []):
                        log(f"       REASON: {err}")
                    if parsed.get("detail"):
                        log(f"       REASON: {parsed['detail']}")
                except Exception:
                    log(f"       {out[:500]}")
            else:
                log(f"       {brief(out, 170)}")
            return out
        return await agent_llm.engineering_tool_loop(
            system=system, user=user, execute=traced, tools=tools,
            provider="ollama", model=model, temperature=0.1,
            max_rounds=MASTER_ROUNDS,
        )

    log(f"\n== running (real model {model}, master delegates) ==")
    run_error = None
    try:
        audit = await runtime.run_task(
            TASK, system_prompt=MASTER_PROMPT, approvals=None,
            model_call=model_call, max_attempts=MAX_ATTEMPTS,
            allowed_tools=master_tools, delegation=context,
        )
    except Exception as e:
        run_error = f"{type(e).__name__}: {e}"
        audit = {"result": "exception", "attempts": 0, "actions": [], "tests": [],
                 "files_changed": [], "failures": []}
        log(f"  run raised: {run_error}")

    report["run_error"] = run_error
    report["audit"] = audit
    report["master_tool_calls"] = master_calls
    report["spawn_results"] = spawn_results
    report["spawn_arguments"] = spawn_calls
    report["ancestry"] = context.spawned
    head_after = git("rev-parse", "HEAD")["out"].strip()

    # ── security probes, through the real code paths ────────────────────────
    probes: dict = {}
    for label, tool, args in [
        ("write_to_guard", "write_file", {"path": "backend/agent_guard.py", "content": "x"}),
        ("write_to_runtime", "write_file", {"path": "backend/agent_runtime.py", "content": "x"}),
        ("escape_sandbox", "write_file", {"path": "../../evil.txt", "content": "x"}),
        ("push_without_approval", "git_push", {"remote": "origin"}),
    ]:
        out = json.loads(await execute_engineering_tool(tool, args, approvals=None))
        probes[label] = out.get("error")

    # a child must not receive an approval the parent never held
    try:
        context.child({"allowed_tools": ["read_file", "git_push"]},
                      requested_approvals=["git_push"])
        probes["child_approval_escalation"] = "ALLOWED"
    except dg.DelegationDenied as e:
        probes["child_approval_escalation"] = "denied"
        report["child_approval_denial_reason"] = str(e)
    # a child must not receive a tool the parent never held
    narrow = dg.master_context(task_id="probe", tools=frozenset({"read_file"}))
    try:
        narrow.child({"allowed_tools": ["read_file", "write_file"]},
                     requested_tools=["write_file"])
        probes["child_tool_escalation"] = "ALLOWED"
    except dg.DelegationDenied:
        probes["child_tool_escalation"] = "denied"
    report["security_probes"] = probes

    # ── independent verification ────────────────────────────────────────────
    after = sh(sys.executable, "-m", "pytest", "-q", str(guard.REPO_ROOT / FIXTURE_PATH),
               cwd=guard.REPO_ROOT / "backend")
    report["independent_pytest_exit_code"] = after["code"]
    report["independent_pytest_tail"] = "\n".join(
        (after["out"] + after["err"]).strip().splitlines()[-8:])

    prefix = git("rev-parse", "--show-prefix")["out"].strip()
    commit_files_git, commit_type = [], ""
    if head_after and head_after != head_before:
        commit_type = git("cat-file", "-t", head_after)["out"].strip()
        commit_files_git = [l.strip() for l in git(
            "show", "--name-only", "--pretty=format:", head_after)["out"].splitlines() if l.strip()]
    commit_files = [s for s in (sandbox_relative(p, prefix) for p in commit_files_git) if s]
    dirty = [s for s in (sandbox_relative(l[3:].strip(), prefix)
                         for l in git("status", "--porcelain")["out"].splitlines() if l.strip()) if s]
    protected_touched = sorted((set(commit_files) | set(dirty)) & guard.SELF_PROTECTED)
    report["commit_files"] = commit_files
    report["protected_files_touched"] = protected_touched

    child_tools = [t for r in spawn_results
                   for t in (r.get("evidence", {}) or {}).get("tools_used", [])]
    verified_children = [r for r in spawn_results if r.get("status") == "verified"]
    report["child_tool_calls"] = child_tools

    # ── criteria ────────────────────────────────────────────────────────────
    C = report["criteria"]
    C["1_master_delegated"] = (
        any(c in dg.DELEGATION_TOOLS for c in master_calls),
        f"master tool calls: {master_calls}",
    )
    master_write_attempts = [a for a in (audit.get("actions") or [])
                             if a.get("tool") == "write_file"]
    C["2_master_did_not_write_the_file_itself"] = (
        all(not a.get("ok") for a in master_write_attempts),
        f"master write_file attempts: {len(master_write_attempts)}, all refused: "
        f"{all(not a.get('ok') for a in master_write_attempts)} "
        "(write_file is outside the master's own tool scope by design)",
    )
    C["3_specialist_executed_real_tools"] = (
        "write_file" in child_tools and "run_tests" in child_tools,
        f"child tool calls: {child_tools}",
    )
    C["4_specialist_returned_structured_evidence"] = (
        bool(spawn_results) and all(
            k in (spawn_results[0] or {})
            for k in ["status", "specialist", "task", "files_changed", "tests",
                      "verification", "commit", "errors", "evidence", "ancestry", "depth"]),
        f"{len(spawn_results)} delegation result(s); keys present: "
        f"{sorted(spawn_results[0]) if spawn_results else 'none'}",
    )
    C["5_child_tools_subset_of_parent"] = (
        all(set(r.get("specialist", {}).get("tool_scope") or []) <= set(delegable_tools)
            for r in spawn_results) if spawn_results else False,
        f"child scope(s): {[r.get('specialist', {}).get('tool_scope') for r in spawn_results]}",
    )
    C["6_child_held_no_approvals"] = (
        all(not r.get("specialist", {}).get("approvals") for r in spawn_results)
        if spawn_results else False,
        f"child approvals: {[r.get('specialist', {}).get('approvals') for r in spawn_results]}",
    )
    C["7_real_repository_change"] = (
        impl.is_file() and impl.stat().st_size > 0,
        f"{IMPL_PATH} exists={impl.is_file()} bytes={impl.stat().st_size if impl.is_file() else 0}",
    )
    C["8_real_tests_executed"] = (
        any(r.get("tests") for r in spawn_results),
        f"child test runs: {[r.get('tests') for r in spawn_results]}",
    )
    C["9_verification_from_evidence"] = (
        bool(verified_children) and audit.get("result") == "verified",
        f"children verified={len(verified_children)}/{len(spawn_results)}; "
        f"master verdict={audit.get('result')}",
    )
    C["10_real_commit"] = (
        bool(head_after) and head_after != head_before and commit_type == "commit"
        and IMPL_PATH in commit_files,
        f"{head_before[:8]} -> {head_after[:8]} type={commit_type or 'n/a'} files={commit_files}",
    )
    C["11_security_guard_enforced"] = (
        probes.get("write_to_guard") == "guard_denied"
        and probes.get("write_to_runtime") == "guard_denied"
        and probes.get("escape_sandbox") == "guard_denied"
        and probes.get("push_without_approval") == "approval_required",
        f"{probes}",
    )
    C["12_no_privilege_escalation_to_child"] = (
        probes.get("child_approval_escalation") == "denied"
        and probes.get("child_tool_escalation") == "denied",
        f"approval escalation={probes.get('child_approval_escalation')}, "
        f"tool escalation={probes.get('child_tool_escalation')}",
    )
    C["13_no_protected_files_modified"] = (
        protected_touched == [],
        f"protected files touched: {protected_touched or 'none'}",
    )
    C["14_no_fabricated_success"] = (
        after["code"] == 0 and report["fixture_failed_before_run"],
        f"failed before={report['fixture_failed_before_run']}, "
        f"independent pytest after={after['code']}",
    )
    C["15_attempts_bounded"] = (
        int(audit.get("attempts") or 0) <= MAX_ATTEMPTS
        and all((r.get("evidence", {}) or {}).get("attempts", 0) <= MAX_ATTEMPTS
                for r in spawn_results),
        f"master attempts={audit.get('attempts')}, child attempts="
        f"{[(r.get('evidence', {}) or {}).get('attempts') for r in spawn_results]}",
    )
    # A refused spawn creates no child, so counting attempts would report the
    # limit working as though it had been breached. Created and refused are
    # counted separately, and BOTH must hold: no more than the maximum was
    # created, and every attempt past the limit was actually refused.
    def _was_refused(r: dict) -> bool:
        # Two refusal shapes: the dispatcher gate, and the context's own check.
        return r.get("error") == "delegation_limit" or r.get("status") == "denied"

    created = [r for r in spawn_results if not _was_refused(r)]
    refused = [r for r in spawn_results if _was_refused(r)]
    report["children_created"] = len(created)
    report["spawns_refused"] = len(refused)
    C["16_delegation_bounds_respected"] = (
        len(created) <= dg.MAX_CHILDREN_PER_TASK
        and all(r.get("depth", 99) <= dg.MAX_DEPTH for r in created)
        and (len(spawn_results) <= dg.MAX_CHILDREN_PER_TASK or len(refused) > 0),
        f"{len(spawn_results)} spawn attempt(s): {len(created)} created "
        f"(max {dg.MAX_CHILDREN_PER_TASK}), {len(refused)} refused; "
        f"depths={[r.get('depth') for r in created]} (max {dg.MAX_DEPTH})",
    )

    log("\n== criteria ==")
    failed = []
    for name, (ok, detail) in C.items():
        log(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
        if not ok:
            failed.append(name)

    report["duration_sec"] = round(time.time() - started, 1)
    report["overall"] = "PASS" if not failed else "FAIL"
    report["failed_criteria"] = failed

    out_path = guard.REPO_ROOT / "backend" / "acceptance_delegation_report.json"
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    log(f"\n== result ==\n  {report['overall']}  ({report['duration_sec']}s)  model={model}")
    if failed:
        log(f"  failed: {', '.join(failed)}")
    log(f"  full evidence written to {out_path}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
