# Getszy — Backup & Restore Runbook

Backups are **logical** (collection-level) and produced by `backend/backup.py`
using only pymongo/bson — no external `mongodump` binary required, so they run
in any backend container.

## What gets backed up
- Every MongoDB collection is dumped to
  `<BACKUP_DIR>/getszy-<UTC-timestamp>/<collection>.jsonl` (one BSON/JSON
  document per line, via `bson.json_util` so ObjectIds/datetimes survive).
- A `manifest.json` records the timestamp and per-collection doc counts.
- By default the **7** most recent backups are kept (`BACKUP_RETENTION_DAYS`).
- The scheduler runs the first backup ~10 minutes after the backend starts,
  then **every 24 hours** (launched from `server.startup`).

## Configuration (env vars on the backend container)
| Var | Default | Meaning |
|-----|---------|---------|
| `BACKUP_DIR` | `/app/backups` | Where backups are written |
| `BACKUP_RETENTION_DAYS` | `7` | How many daily backups to keep |

### VPS persistence (important)
The default `/app/backups` lives **inside** the container and is lost on
rebuild. For real durability:

1. Mount a volume to the backup directory, e.g. in `docker-compose.yml`:
   ```yaml
   services:
     backend:
       volumes:
         - /opt/getszy/backups:/app/backups
   ```
2. (Recommended) push copies offsite — e.g. a nightly `rsync`/`rclone` of
   `/opt/getszy/backups` to S3 or another host. The app does **not** do this
   for you.

## Manual backup
```bash
cd /opt/getszy/legacy-getszy
docker compose exec backend python -c "import asyncio,backup; print(asyncio.run(backup.run_backup()))"
```

## Manual restore
Pick the backup directory you want, then:
```bash
cd /opt/getszy/legacy-getszy
docker compose exec backend python -c "import asyncio,backup; asyncio.run(backup.restore_backup('/app/backups/getszy-YYYYMMDD-HHMMSS'))"
```
`restore_backup` upserts each document by `_id`, so it is safe to re-run and
will **not** duplicate documents.

> ⚠️ Restore overwrites existing documents with the same `_id`. Restore into a
> fresh database (or a staging instance) first if you only want to recover a few
> collections, then copy the specific docs back.

## Verification
```bash
# List available backups
ls -1 /opt/getszy/backups

# Sanity-check a backup: count docs per collection
for f in /opt/getszy/backups/getszy-*/manifest.json; do echo "$f"; cat "$f"; done
```

## Notes / limitations
- These are logical backups; for very large datasets prefer a filesystem/oplog
  snapshot of the `mongo` volume as an additional safety net.
- The scheduler is best-effort: if a backup fails it logs an error and tries
  again on the next 24h cycle. Monitor `getszy` logs for `backup ok:` lines.
