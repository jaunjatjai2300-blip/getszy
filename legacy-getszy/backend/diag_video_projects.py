"""Diagnose stuck video-factory projects.

Tells you exactly why a project is stuck at "processing" (dead chain vs. live
chain vs. render stage), and whether recovery would reset it on restart.

Usage (run from legacy-getszy/backend with .env loaded):
    python diag_video_projects.py                 # list all projects + stuck verdict
    python diag_video_projects.py <project_id>   # detailed diagnosis for one
"""
import asyncio
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

CHAIN_STALE_SECS = int(os.environ.get("VF_CHAIN_STALE_SECS", "900"))

from db import db


def _age(iso):
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int((datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return None


async def diagnose(pid=None):
    query = {"id": pid} if pid else {}
    cursor = db.video_projects.find(query, {"_id": 0})
    n = 0
    async for p in cursor:
        n += 1
        status = p.get("status")
        rs = p.get("render_status")
        hb = p.get("chain_heartbeat") or p.get("updated_at")
        age = _age(hb)
        stages = p.get("stages") or {}
        has_stages = bool(stages)
        reasons = []

        if status in ("processing", "created"):
            reasons.append(f"chain status='{status}'")
            if age is None:
                reasons.append("no heartbeat/updated_at -> cannot prove liveness (will be reset)")
            elif age > CHAIN_STALE_SECS:
                reasons.append(f"chain heartbeat {age}s old (> {CHAIN_STALE_SECS}s stale -> will be reset)")
            else:
                reasons.append(f"chain heartbeat {age}s old (LIVE, within stale window)")
        if rs in ("queued", "generating_images", "generating_voice", "assembling"):
            reasons.append(f"render_status='{rs}' (recovery resets on restart)")
        if status == "error":
            reasons.append(f"already errored: {p.get('errors')}")

        verdict = "STUCK -> recovery will reset + refund on restart" if reasons else "OK"
        print(f"\n--- {p.get('id')} ---")
        print(f"  title         : {p.get('title')}")
        print(f"  status        : {status}")
        print(f"  render_status : {rs}")
        print(f"  stages        : {list(stages.keys()) if has_stages else 'none'}")
        print(f"  heartbeat_age : {age}s" if age is not None else "  heartbeat_age : n/a")
        print(f"  refunded      : {p.get('refunded')}")
        print(f"  verdict       : {verdict}")
        for r in reasons:
            print(f"    - {r}")
    if n == 0:
        print("No matching video projects found.")


if __name__ == "__main__":
    pid = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(diagnose(pid))
