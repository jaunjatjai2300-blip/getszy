#!/usr/bin/env python3
"""DR failover drill — measure Recovery Time Objective (RTO) by restoring a
backup into a target database and timing it.

Usage:
  python scripts/dr_drill.py \
      --backup /opt/getszy/legacy-getszy/backend/backups/latest \
      --mongo mongodb://localhost:27017 \
      --db getszy_drill

It sets MONGO_URL/DB_NAME *before* importing backup so the module-level db
handle points at the drill target, then times restore_backup().
"""
import argparse
import asyncio
import os
import sys
import time


def main() -> int:
    ap = argparse.ArgumentParser(description="Getszy DR failover RTO drill")
    ap.add_argument("--backup", required=True, help="Backup directory (or 'latest' symlink)")
    ap.add_argument("--mongo", default=os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    ap.add_argument("--db", default="getszy_drill")
    ap.add_argument("--rto-target", type=float, default=180.0, help="RTO target in seconds")
    args = ap.parse_args()

    os.environ["MONGO_URL"] = args.mongo
    os.environ["DB_NAME"] = args.db
    # Ensure backups during the drill don't clobber production backup dir.
    os.environ.setdefault("BACKUP_DIR", "/tmp/getszy_dr_drill_backups")

    backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
    sys.path.insert(0, backend_dir)
    import backup  # noqa: E402

    start = time.time()
    restored = asyncio.run(backup.restore_backup(args.backup))
    elapsed = time.time() - start

    print("=== Getszy DR Failover Drill ===")
    print(f"Source backup : {args.backup}")
    print(f"Target DB     : {args.db} @ {args.mongo}")
    print(f"Docs restored : {restored}")
    print(f"Measured RTO  : {elapsed:.2f}s (target <= {args.rto_target:.0f}s)")
    passed = elapsed <= args.rto_target
    print(f"RESULT        : {'PASS' if passed else 'REVIEW'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
