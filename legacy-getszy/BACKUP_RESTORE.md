# Getszy — Backup and Restore Runbook

Getszy creates **logical MongoDB backups** using `backend/backup.py`; no `mongodump` binary is required. Each run writes BSON-safe JSON Lines collection exports and a `manifest.json`. The backend starts the scheduler approximately ten minutes after boot and then runs every **four hours** by default. This establishes a target application-data RPO of under four hours, subject to monitoring and successful off-site copy verification.

> **Scope.** Logical backups preserve application collections, ObjectIds, and datetimes. They do not replace a replica-set snapshot or a separately managed backup of uploaded/generated assets. Docker volumes and provider credentials must be protected independently.

## Backup contents and retention

Each run creates `<BACKUP_DIR>/getszy-<UTC-timestamp>/`. Every MongoDB collection is exported as `<collection>.jsonl`; the manifest records the backup timestamp and collection counts. When encryption is enabled, files are stored as `<collection>.jsonl.enc` and the manifest records the count plus encryption state.

Getszy uses grandfather-father-son retention. Daily backups are retained for seven days, Monday backups for five weeks, and first-of-month backups for twelve months unless the corresponding environment variables are changed. The scheduler updates the `latest` symlink atomically after a successful local backup.

| Environment variable | Production value or default | Purpose |
|---|---:|---|
| `BACKUP_DIR` | `/app/backups` | Location in the backend container for logical backup folders. |
| `BACKUP_INTERVAL_HOURS` | `4` | Target backup interval; use a positive integer. |
| `BACKUP_RETENTION_DAILY` | `7` | Daily GFS retention count. |
| `BACKUP_RETENTION_WEEKLY` | `5` | Weekly GFS retention count. |
| `BACKUP_RETENTION_MONTHLY` | `12` | Monthly GFS retention count. |
| `BACKUP_ENCRYPTION_KEY` | **Required in production** | Fernet key used to encrypt every collection export before it is retained or uploaded. |
| `BACKUP_S3_BUCKET` | Recommended | Enables S3-compatible off-site sync following every successful local backup. |
| `BACKUP_S3_ENDPOINT_URL` | Optional | Endpoint for Cloudflare R2, Wasabi, MinIO, or another S3-compatible service. |
| `BACKUP_S3_REGION` | `us-east-1` | S3 client region. |
| `BACKUP_S3_PREFIX` | `getszy-backups` | Object-key prefix; Getszy adds daily, weekly, or monthly tier paths. |

## Docker persistence configuration

The primary Compose deployment keeps generated media and logical database exports on named volumes. Confirm the backend service has both mounts and never remove these volumes during an application redeploy.

```yaml
services:
  backend:
    volumes:
      - backend_media:/app/backend/media
      - backup_data:/app/backups

volumes:
  backend_media:
  backup_data:
```

The `backend_media:/app/backend/media` volume preserves generated customer media. It is **not** a substitute for the `/app/backups` database backup volume or the off-site S3 copy. On a single VPS, configure `BACKUP_S3_BUCKET` before public launch; a same-host Docker volume alone cannot recover from host loss.

## Production configuration

Generate a dedicated encryption key once, store it only in the VPS `.env` file or a secrets manager, and keep an offline escrow copy under restricted access. Losing this key makes encrypted backups unrecoverable.

```bash
cd /opt/getszy/legacy-getszy
python3 - <<'PY'
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
PY
```

Add the value and off-site destination to `/opt/getszy/legacy-getszy/.env` without committing the file:

```dotenv
BACKUP_INTERVAL_HOURS=4
BACKUP_ENCRYPTION_KEY=PASTE_THE_GENERATED_FERNET_KEY
BACKUP_S3_BUCKET=getszy-production-backups
BACKUP_S3_REGION=ap-south-1
BACKUP_S3_PREFIX=getszy-backups
# Set only for R2, Wasabi, MinIO, or another S3-compatible provider.
# BACKUP_S3_ENDPOINT_URL=https://<provider-endpoint>
```

The AWS SDK uses the standard credential chain. For an S3-compatible provider, supply its access key and secret as environment variables or attach an instance role; do not place them in source control. After editing `.env`, apply it with a controlled rolling deployment:

```bash
cd /opt/getszy/legacy-getszy
docker compose up -d --force-recreate backend
```

## Manual backup and verification

Run a manual backup after every deployment that changes the backup implementation or its environment. A success prints a path inside `/app/backups`; then inspect both local files and backend logs for the `backup off-site sync ok:` message when S3 sync is configured.

```bash
cd /opt/getszy/legacy-getszy
docker compose exec backend python -c "import asyncio, backup; print(asyncio.run(backup.run_backup()))"
docker compose exec backend sh -lc 'readlink -f /app/backups/latest && cat /app/backups/latest/manifest.json'
docker compose logs --since 15m backend | grep -E 'backup ok:|backup off-site sync ok:|backup failed:'
```

For a basic off-site listing with AWS CLI credentials available on the VPS:

```bash
aws s3 ls "s3://${BACKUP_S3_BUCKET}/${BACKUP_S3_PREFIX}/" --recursive | tail -30
```

## Restore drill — staging first

Never begin a production restore without identifying the incident commander, taking a current snapshot, and recording the selected backup. Test the exact restore in staging at least quarterly and measure the elapsed time against the RTO target.

1. Start a **staging** Getszy stack with an empty MongoDB database and the same `BACKUP_ENCRYPTION_KEY`.
2. Select a local backup, or download an off-site folder into an empty local directory with `restore_from_offsite`.
3. Restore the folder into staging, then sign in and validate users, orders, credit transactions, and recent media metadata.

```bash
cd /opt/getszy/legacy-getszy
# Restore the newest local backup into the database used by this backend container.
docker compose exec backend python -c "import asyncio, backup; print(asyncio.run(backup.restore_backup('/app/backups/latest')))"
```

For an off-site backup, first copy the exact tier/name into `/app/restore/getszy-YYYYMMDD-HHMMSS`; then call `restore_backup` against that directory. `restore_from_offsite(tier, name, dest_dir)` is available inside `backend/backup.py` for this purpose. It uses paths such as `getszy-backups/daily/getszy-YYYYMMDD-HHMMSS/`.

> **Warning:** Restore upserts documents by `_id`. It overwrites matching documents but does not remove records created after the backup. For a full rollback, restore to a fresh database or stop writes and explicitly rebuild the target database using an approved change plan.

## Operational checks and ownership

The on-call owner must investigate any failed backup, stale backup metric, missing S3 confirmation, or failed restore drill immediately. Alerting should page when the last successful backup is older than the configured four-hour interval plus operational tolerance. Record every restore drill with: backup timestamp, encrypted/off-site state, database record counts, application smoke-test result, start/finish time, and follow-up actions.

| Control | Owner | Cadence | Evidence |
|---|---|---|---|
| Local encrypted backup succeeds | Platform on-call | Every 4 hours | Backend log and manifest. |
| Off-site sync succeeds | Platform on-call | Every 4 hours | S3 log confirmation and object listing. |
| Restore into staging | CTO / platform owner | Quarterly and before major launch | Drill record, data checks, elapsed RTO. |
| Encryption-key escrow test | CTO / security owner | Every 6 months | Controlled recovery test; never paste keys in tickets. |
| GFS retention review | Platform owner | Monthly | Volume capacity and S3 lifecycle review. |
