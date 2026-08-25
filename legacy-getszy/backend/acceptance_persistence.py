#!/usr/bin/env python
"""Agent Factory — REAL Mongo persistence verification.

Runs against a real MongoDB server, in an ISOLATED database. Production
collections are never written to: the script refuses to start if DB_NAME is the
production default, and it drops its own database when it finishes.

What this proves, with a real database rather than a stand-in:

  * a durable operation record is created for an agent task
  * the idempotency key makes an identical request reuse that record instead of
    doing the work twice
  * the execution lease stops a second worker running the same task
  * session memory survives and is recalled on a later turn
  * the record is readable back after the Mongo client is closed and rebuilt,
    which is what a process or container restart looks like from the data's side

What this does NOT test is the model loop; that was proven separately by
acceptance_agent_factory.py. The tool calls made here are nonetheless REAL --
real reads and a real pytest execution -- so nothing about the work is simulated.
The only thing standing in for the model is the choice of which tools to call.

Run:
    DB_NAME=getszy_agent_acceptance python acceptance_persistence.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PRODUCTION_DB = "getszy_db"

# Checked BEFORE importing anything that opens a connection, so a misconfigured
# run cannot touch production data even briefly.
_db_name = os.environ.get("DB_NAME", PRODUCTION_DB)
if _db_name == PRODUCTION_DB and os.environ.get("ALLOW_PRODUCTION_DB") != "1":
    print(
        f"Refusing to run against the production database ({PRODUCTION_DB!r}).\n"
        "This test creates and deletes records. Use an isolated database:\n"
        "  -e DB_NAME=getszy_agent_acceptance"
    )
    raise SystemExit(2)

import agent_guard as guard  # noqa: E402
import agent_persistence as persistence  # noqa: E402
import agent_runtime as runtime  # noqa: E402
from db import client as mongo_manager, db  # noqa: E402

PROBE_REL = "backend/tests/_persistence_probe_test.py"
PROBE_SOURCE = '''"""Throwaway probe used by acceptance_persistence.py. Deleted after the run."""


def test_probe_runs_for_real():
    assert 2 + 2 == 4
'''


def log(msg: str = "") -> None:
    print(msg, flush=True)


def brief(value, limit: int = 160) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= limit else text[:limit] + f"…(+{len(text) - limit})"


async def ensure_unique_index() -> None:
    """Create the same unique index the application creates at startup.

    Idempotency in paid_operations depends entirely on a DuplicateKeyError. Without
    this index insert_one simply succeeds twice and the idempotency guarantee is
    silently absent -- the failure mode looks like everything working.
    """
    await db.paid_operations.create_index(
        [("user_id", 1), ("action_type", 1), ("idempotency_key", 1)],
        unique=True,
        name="uniq_customer_paid_operation_intention",
    )


async def production_index_present() -> bool | None:
    """Read-only check that PRODUCTION also has the index. Never writes."""
    try:
        prod = mongo_manager._active_client()[PRODUCTION_DB]
        names = await prod.paid_operations.index_information()
        return any(
            info.get("unique")
            and [k for k, _ in info.get("key", [])] == ["user_id", "action_type", "idempotency_key"]
            for info in names.values()
        )
    except Exception:
        return None


async def main() -> int:
    started = time.time()
    report: dict = {"criteria": {}}
    results: dict = {}

    log("== preflight ==")
    log(f"  database: {_db_name} (production is {PRODUCTION_DB!r}, untouched)")
    try:
        info = await mongo_manager._active_client().server_info()
        log(f"  mongo: {info.get('version')}")
        report["mongo_version"] = info.get("version")
    except Exception as e:
        log(f"  cannot reach Mongo: {e}")
        return 2

    if not guard.REPO_ROOT_VALID:
        log("  agent sandbox has no valid repository root; set AGENT_REPO_ROOT")
        return 2
    log(f"  repo_root: {guard.REPO_ROOT}")

    await ensure_unique_index()
    prod_index = await production_index_present()
    report["production_unique_index_present"] = prod_index
    log(f"  production idempotency index present: {prod_index}")

    probe = guard.REPO_ROOT / PROBE_REL
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text(PROBE_SOURCE, encoding="utf-8", newline="")

    user_id = f"acceptance-user-{uuid.uuid4().hex[:8]}"
    request = f"verify persistence probe {uuid.uuid4().hex[:8]}"
    session_id = f"acceptance-session-{uuid.uuid4().hex[:8]}"
    executions = {"count": 0}

    async def driver(system, user, tools, execute):
        """Real tool calls. Only the tool CHOICE stands in for the model."""
        executions["count"] += 1
        await execute("read_file", {"path": PROBE_REL})
        await execute("run_tests", {"target": PROBE_REL})

    try:
        # ── 1. durable execution ────────────────────────────────────────────
        log("\n== run 1: durable execution ==")
        first = await runtime.run_task(
            request, system_prompt="persistence probe", model_call=driver,
            user_id=user_id, session_id=session_id, persist=True,
            worker_id="worker-A",
        )
        log(f"  result={first['result']} attempts={first['attempts']} "
            f"operation_id={first.get('operation_id')}")
        results["first"] = first

        op_id = first.get("operation_id")
        stored = await persistence.task_status(op_id, user_id) if op_id else None
        results["stored"] = stored
        log(f"  stored status={stored and stored.get('status')} "
            f"evidence={brief((stored or {}).get('evidence'))}")

        # ── 2. idempotency: same request again ──────────────────────────────
        log("\n== run 2: identical request (idempotency + lease) ==")
        second = await runtime.run_task(
            request, system_prompt="persistence probe", model_call=driver,
            user_id=user_id, session_id=session_id, persist=True,
            worker_id="worker-B",
        )
        log(f"  result={second['result']} operation_id={second.get('operation_id')}")
        results["second"] = second

        docs = await db.paid_operations.find(
            {"user_id": user_id, "action_type": persistence.AGENT_ACTION_TYPE},
            {"_id": 0, "operation_id": 1, "status": 1, "idempotency_key": 1},
        ).to_list(length=10)
        results["operation_documents"] = docs
        log(f"  operation documents for this user: {len(docs)}")

        # ── 3. lease held by another worker ─────────────────────────────────
        log("\n== run 3: lease held elsewhere ==")
        third_request = f"leased task {uuid.uuid4().hex[:8]}"
        key = persistence.task_idempotency_key(third_request, "master")
        op, _created = await persistence.create_or_reuse_operation(
            user_id=user_id, action_type=persistence.AGENT_ACTION_TYPE,
            idempotency_key=key, payload={"request": third_request},
        )
        claimed = await persistence.claim_execution(op["operation_id"], "worker-OTHER")
        log(f"  lease taken by worker-OTHER: {bool(claimed)}")
        before_leased = executions["count"]
        leased = await runtime.run_task(
            third_request, system_prompt="persistence probe", model_call=driver,
            user_id=user_id, persist=True, worker_id="worker-C",
        )
        log(f"  result={leased['result']} (executions before={before_leased}, "
            f"after={executions['count']})")
        results["leased"] = leased
        results["executions_during_leased_run"] = executions["count"] - before_leased

        # ── 4. session memory ───────────────────────────────────────────────
        recalled = await persistence.recall(session_id)
        results["recalled_messages"] = recalled
        log(f"\n== session memory ==\n  recalled {len(recalled)} message(s)")

        # ── 5. survives a client restart ────────────────────────────────────
        log("\n== restart durability ==")
        mongo_manager.close()          # drop the connection entirely
        reread = await persistence.task_status(op_id, user_id) if op_id else None
        results["reread_after_restart"] = reread
        log(f"  record re-read on a fresh connection: {bool(reread)} "
            f"status={reread and reread.get('status')}")

        # ── criteria ────────────────────────────────────────────────────────
        C = report["criteria"]
        C["1_durable_record_created"] = (
            bool(op_id) and stored is not None
            and stored.get("action_type") == persistence.AGENT_ACTION_TYPE,
            f"operation_id={op_id} action_type={(stored or {}).get('action_type')}",
        )
        C["2_status_reflects_verified_result"] = (
            first["result"] == "verified" and (stored or {}).get("status") == "SUCCEEDED",
            f"audit result={first['result']} stored status={(stored or {}).get('status')}",
        )
        C["3_evidence_persisted"] = (
            bool((stored or {}).get("evidence", {}).get("tools_used")),
            f"tools_used={brief((stored or {}).get('evidence', {}).get('tools_used'))}",
        )
        C["4_idempotent_single_record"] = (
            len([d for d in docs if d.get("idempotency_key")
                 == persistence.task_idempotency_key(request, "master")]) == 1,
            f"{len(docs)} document(s) total for this user across both requests",
        )
        C["5_duplicate_execution_prevented"] = (
            second["result"] == "already_running_or_complete"
            and second.get("operation_id") == op_id,
            f"second run returned {second['result']} for operation {second.get('operation_id')}",
        )
        C["6_lease_blocks_a_second_worker"] = (
            leased["result"] == "already_running_or_complete"
            and results["executions_during_leased_run"] == 0,
            f"result={leased['result']}, tool executions during that run="
            f"{results['executions_during_leased_run']}",
        )
        C["7_session_memory_persisted"] = (
            len(recalled) >= 2,
            f"{len(recalled)} message(s) recalled from Mongo",
        )
        C["8_survives_client_restart"] = (
            reread is not None and reread.get("status") == "SUCCEEDED",
            f"re-read after closing the client: {reread and reread.get('status')}",
        )
        C["9_credits_never_debited"] = (
            (stored or {}).get("credit_state") == "NOT_DEBITED",
            f"credit_state={(stored or {}).get('credit_state')} "
            "(internal engineering work must never bill a customer)",
        )
        C["10_production_index_intact"] = (
            prod_index is True,
            f"production unique idempotency index present: {prod_index}",
        )

        log("\n== criteria ==")
        failed = []
        for name, (ok, detail) in C.items():
            log(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
            if not ok:
                failed.append(name)

        report["results"] = results
        report["duration_sec"] = round(time.time() - started, 1)
        report["overall"] = "PASS" if not failed else "FAIL"
        report["failed_criteria"] = failed

        out = guard.REPO_ROOT / "backend" / "acceptance_persistence_report.json"
        out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        log(f"\n== result ==\n  {report['overall']}  ({report['duration_sec']}s)")
        if failed:
            log(f"  failed: {', '.join(failed)}")
        log(f"  evidence written to {out}")
        return 0 if not failed else 1

    finally:
        if probe.exists():
            probe.unlink()
        try:
            await mongo_manager._active_client().drop_database(_db_name)
            log(f"  cleaned up test database {_db_name}")
        except Exception as e:
            log(f"  WARNING: could not drop test database {_db_name}: {e}")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
