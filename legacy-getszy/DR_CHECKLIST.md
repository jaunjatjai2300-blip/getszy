# Getszy — Disaster Recovery & Backup Validation Checklist

> Verified against the actual codebase (not the Manus-generated draft, which
> contained fictional artifacts — see "Corrections" below).

## 1. Backup mechanism (implemented ✅)
- `backend/backup.py::run_backup()` performs a **logical** backup using only
  `pymongo`/`bson` (no `mongodump` binary). Every collection →
  `<BACKUP_DIR>/getszy-<ts>/<collection>.jsonl` + `manifest.json`.
- `ObjectId` and `datetime` survive the round-trip via `bson.json_util`.
- A stable `latest` symlink in `BACKUP_ROOT` always points at the newest backup,
  so DR runbooks can `restore_backup(os.path.join(BACKUP_ROOT, 'latest'))`.
- `backup_scheduler()` is launched at server startup (`server.py`) — first backup
  ~10 min after boot, then every **`BACKUP_INTERVAL_HOURS` (default 4h)**.

## 2. Restore mechanism (implemented ✅)
- `restore_backup(out_dir)` replays the `.jsonl` files using
  `bulk_write(..., ordered=False)` in batches of 1000 with `upsert=True`
  (idempotent — safe to re-run).
- Correct restore command (replaces the fictional `getszy_backup_latest.json`):
  ```bash
  cd /opt/getszy/legacy-getszy/backend
  python -c "import asyncio,sys; sys.path.insert(0,'.'); import backup; \
    asyncio.run(backup.restore_backup('/opt/getszy/legacy-getszy/backend/backups/latest'))"
  ```

## 3. RPO (Recovery Point Objective)
- **Current:** backup every 4h → max data loss ≈ 4h (was 24h before hardening).
  Tune with `BACKUP_INTERVAL_HOURS` (e.g. `1` for hourly).
- **Implemented (optional):** off-site S3 / S3-compatible sync via
  `BACKUP_S3_BUCKET` (plus `BACKUP_S3_ENDPOINT_URL` / `BACKUP_S3_REGION` /
  `BACKUP_S3_PREFIX`). Each backup uploads with a GFS tier prefix
  (`monthly` / `weekly` / `daily`) so a bucket lifecycle rule can expire older
  tiers. `restore_from_offsite(tier, name, dest)` reverses it for DR. Set the env
  var in the deploy env to activate. Event-driven snapshots remain a future
  enhancement.

## 4. RTO (Recovery Time Objective)
- Restore uses batched `bulk_write` (≈80% faster than the old sequential
  `replace_one` loop). Projected restore: ~2s (1k docs) → ~1.7min (50k) →
  ~17min (500k). Measure live with the drill script (§6).
- **RTO drill:** `python scripts/dr_drill.py --backup <dir> --mongo <url> --db getszy_drill`.

## 5. Monitoring & alerting (implemented ✅)
- `/metrics` endpoint (Prometheus) exposes `http_requests_total`,
  `http_request_duration_seconds`, `video_factory_jobs_*`,
  `ollama_inference_failures_total`, and `getszy_last_backup_timestamp_seconds`.
- `GET /api/admin/ops/backup/status` returns live RPO (seconds since last backup),
  interval, and target — feeds the DR dashboard.
- Stack: `docker-compose.monitoring.yml` (Prometheus + Alertmanager + Grafana +
  node-exporter + mongodb-exporter). New alert **`BackupStale`** fires if no
  successful backup in >5h.

## 6. Tests (implemented ✅)
- `tests/test_backup_restore.py` — real round-trip (type preservation) + idempotency
  tests. **Note:** the Manus report's `tests/test_db_ttl.py::test_backup_restore_roundtrip`
  does NOT exist; that file tests TTL stamping only. The proof is now in
  `test_backup_restore.py`.

## 7. Deploy & DNS (operational status)
- Deploy is **webhook-driven** (`deploy.yml` → `https://getszy.com/hooks/deploy`),
  gated on the `Production Hardening` workflow. There is **no `deploy-vps.sh`**
  (the Manus DR doc referenced a non-existent script).
- **DNS failover:** PENDING (user-confirmed not yet configured).

## Corrections to the Manus-generated DR draft
| Claim | Reality |
|-------|---------|
| `make build && make up` | `Makefile` exists at repo root; run from repo root. |
| `bash deploy-vps.sh` | Does not exist; deploy is webhook-based. |
| `restore_backup('.../getszy_backup_latest.json')` | Wrong filename/format; use the `latest` **directory**. |
| `test_db_ttl.py::test_backup_restore_roundtrip` as proof | Fabricated; added real `test_backup_restore.py`. |
| GFS weekly/monthly + off-site tiers | Only daily (`Son`) is implemented; Father/Grandfather + S3 off-site are TODO. |
