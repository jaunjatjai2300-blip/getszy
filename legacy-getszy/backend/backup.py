"""Automated logical backups for Getszy.

Uses only pymongo/bson (no external ``mongodump`` binary required), so it works
in any backend container. ``run_backup()`` writes every collection to
``<BACKUP_DIR>/getszy-<ts>/<collection>.jsonl`` using :func:`bson.json_util.dumps`
so ObjectIds and datetimes survive the round-trip, plus a ``manifest.json``.
Old backups beyond ``BACKUP_RETENTION_DAYS`` are pruned.

``backup_scheduler()`` is an asyncio loop launched from ``server.startup``: it
runs the first backup ~10 minutes after boot, then every ``BACKUP_INTERVAL_HOURS``
(default 4h; was 24h) to bound RPO.

For real persistence on the VPS, mount a volume at the backup directory (set the
``BACKUP_DIR`` env var, default ``/app/backups``) and ideally push copies
offsite. See BACKUP_RESTORE.md.
"""
import asyncio
import glob
import json
import logging
import os
import shutil
from datetime import datetime, timezone

from bson.json_util import dumps as bson_dumps, loads as bson_loads
from cryptography.fernet import Fernet, InvalidToken
from pymongo import ReplaceOne
from db import db

logger = logging.getLogger('getszy')

BACKUP_ROOT = os.environ.get('BACKUP_DIR', '/app/backups')
RETENTION = int(os.environ.get('BACKUP_RETENTION_DAYS', '7'))
# RPO control: how often the background scheduler snapshots the database.
# Default 4h (down from 24h) to bound data-loss exposure during growth.
BACKUP_INTERVAL_SECONDS = int(os.environ.get('BACKUP_INTERVAL_HOURS', '4')) * 3600
# GFS (Grandfather-Father-Son) retention: how many of each tier to keep locally.
# Daily snapshots are kept for RETENTION_DAILY days; weekly (Mondays) for
# RETENTION_WEEKLY weeks; monthly (1st of month) for RETENTION_MONTHLY months.
# The off-site S3 sync mirrors these tiers via its object-key prefix.
RETENTION_DAILY = int(os.environ.get('BACKUP_RETENTION_DAILY', os.environ.get('BACKUP_RETENTION_DAYS', '7')))
RETENTION_WEEKLY = int(os.environ.get('BACKUP_RETENTION_WEEKLY', '5'))
RETENTION_MONTHLY = int(os.environ.get('BACKUP_RETENTION_MONTHLY', '12'))
# Populated by run_backup(); consumed by the RPO/RTO status endpoint + metrics.
LAST_BACKUP = {'ts': None, 'ts_epoch': None, 'dir': None, 'docs': 0}

# ── At-rest encryption ────────────────────────────────────────────────────────
# Backups contain PII (emails, orders, chat logs). When BACKUP_ENCRYPTION_KEY is
# set, every collection file is written as `<name>.jsonl.enc` (Fernet) so
# plaintext PII never touches disk or the off-site bucket. Leave it empty to
# keep the previous plaintext behaviour (only for local/dev).
_cipher = None
_cipher_ready = False


def _get_cipher():
    global _cipher, _cipher_ready
    if _cipher_ready:
        return _cipher
    key = os.environ.get('BACKUP_ENCRYPTION_KEY')
    if key:
        try:
            _cipher = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:  # pragma: no cover - environment dependent
            logger.error(f'backup: invalid BACKUP_ENCRYPTION_KEY: {e}')
            _cipher = None
    _cipher_ready = True
    return _cipher


async def run_backup():
    try:
        os.makedirs(BACKUP_ROOT, exist_ok=True)
    except Exception as e:  # pragma: no cover - environment dependent
        logger.error(f'backup: cannot create {BACKUP_ROOT}: {e}')
        return None
    ts = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    out_dir = os.path.join(BACKUP_ROOT, f'getszy-{ts}')
    os.makedirs(out_dir, exist_ok=True)
    try:
        names = await db.list_collection_names()
        manifest = {'ts': ts, 'collections': {}}
        for name in names:
            coll = db[name]
            path = os.path.join(out_dir, f'{name}.jsonl')
            count = 0
            with open(path, 'w', encoding='utf-8') as fh:
                cursor = coll.find({})
                async for doc in cursor:
                    fh.write(bson_dumps(doc) + '\n')
                    count += 1
            cipher = _get_cipher()
            if cipher is not None:
                # Encrypt at rest: plaintext PII never persists on disk or S3.
                with open(path, 'rb') as fh:
                    data = fh.read()
                with open(path + '.enc', 'wb') as fh:
                    fh.write(cipher.encrypt(data))
                os.remove(path)
                manifest['collections'][name] = {'docs': count, 'encrypted': True}
            else:
                manifest['collections'][name] = count
        with open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8') as fh:
            json.dump(manifest, fh, indent=2)
        _prune()
        # Point a stable `latest` symlink at the newest backup so DR runbooks
        # can `restore_backup(os.path.join(BACKUP_ROOT, 'latest'))`.
        try:
            latest = os.path.join(BACKUP_ROOT, 'latest')
            if os.path.islink(latest) or os.path.exists(latest):
                os.unlink(latest)
            os.symlink(out_dir, latest)
        except Exception as e:  # pragma: no cover - environment dependent
            logger.warning(f'backup latest symlink warning: {e}')
        total_docs = sum(manifest['collections'].values())
        epoch = datetime.now(timezone.utc).timestamp()
        LAST_BACKUP.update({'ts': ts, 'ts_epoch': epoch, 'dir': out_dir, 'docs': total_docs})
        # Off-site copy (no-op unless BACKUP_S3_BUCKET is configured). Must never
        # block or fail the local backup.
        try:
            sync_backup_offsite(out_dir)
        except Exception as e:  # pragma: no cover - optional dependency
            logger.warning(f'backup off-site sync warning: {e}')
        try:
            from middleware import set_last_backup_ts
            set_last_backup_ts(epoch)
        except Exception:
            pass
        logger.info(f'backup ok: {out_dir} ({total_docs} docs)')
        return out_dir
    except Exception as e:  # pragma: no cover - environment dependent
        logger.error(f'backup failed: {e}')
        return None


def _prune():
    """GFS retention: keep the newest N daily / weekly / monthly snapshots.

    Tier is derived from each backup's timestamp (1st of month -> monthly,
    Monday -> weekly, otherwise daily) so the scheduler's regular 4h runs
    naturally produce the full GFS set. Older snapshots are removed.
    """
    try:
        dirs = sorted(glob.glob(os.path.join(BACKUP_ROOT, 'getszy-*')))
        buckets = {'daily': [], 'weekly': [], 'monthly': []}
        for d in dirs:
            ts = os.path.basename(d).replace('getszy-', '')
            buckets.setdefault(_backup_tier(ts), []).append(d)
        limits = {'daily': RETENTION_DAILY, 'weekly': RETENTION_WEEKLY, 'monthly': RETENTION_MONTHLY}
        keep = set()
        for tier, paths in buckets.items():
            keep.update(paths[-limits[tier]:])  # newest `limit` per tier
        for d in dirs:
            if d not in keep:
                shutil.rmtree(d, ignore_errors=True)
    except Exception as e:  # pragma: no cover - environment dependent
        logger.warning(f'backup prune warning: {e}')


async def restore_backup(out_dir):
    """Restore a backup directory produced by :func:`run_backup`."""
    out_dir = os.path.abspath(out_dir)
    if not os.path.isdir(out_dir):
        raise ValueError(f'not a directory: {out_dir}')
    files = sorted(glob.glob(os.path.join(out_dir, '*.jsonl*')))
    if not files:
        raise ValueError(f'no backup files in {out_dir}')
    cipher = _get_cipher()
    restored = 0
    batch = 1000
    for path in files:
        base = os.path.basename(path)
        if base.endswith('.enc'):
            name = os.path.splitext(base[:-4])[0]  # strip .enc then .jsonl
        else:
            name = os.path.splitext(base)[0]
        coll = db[name]
        ops = []
        with open(path, 'rb') as fh:
            raw = fh.read()
        if base.endswith('.enc'):
            if cipher is None:
                raise RuntimeError('BACKUP_ENCRYPTION_KEY is required to restore an encrypted backup')
            try:
                raw = cipher.decrypt(raw)
            except InvalidToken as e:
                raise RuntimeError(f'backup decryption failed (wrong key?): {e}')
        text = raw.decode('utf-8')
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            doc = bson_loads(line)
            if '_id' not in doc:
                continue
            ops.append(ReplaceOne({'_id': doc['_id']}, doc, upsert=True))
            if len(ops) >= batch:
                await coll.bulk_write(ops, ordered=False)
                restored += len(ops)
                ops = []
        if ops:
            await coll.bulk_write(ops, ordered=False)
            restored += len(ops)
    logger.info(f'restore complete from {out_dir}: {restored} docs')
    return restored


def last_backup_info():
    """Metadata about the most recent successful backup (for RPO/RTO status)."""
    return dict(LAST_BACKUP)


# ─────────────────────────────────────────────────────────────────────────────
# Optional off-site sync (S3 / S3-compatible: AWS, R2, Wasabi, MinIO).
# Active only when BACKUP_S3_BUCKET is set; never blocks the local backup.
# GFS tiers (monthly/weekly/daily) are encoded in the object-key prefix so a
# bucket lifecycle policy can expire older tiers independently.
# ─────────────────────────────────────────────────────────────────────────────
def _offsite_config():
    bucket = os.environ.get('BACKUP_S3_BUCKET')
    if not bucket:
        return None
    return {
        'bucket': bucket,
        'endpoint': os.environ.get('BACKUP_S3_ENDPOINT_URL') or None,
        'region': os.environ.get('BACKUP_S3_REGION', 'us-east-1'),
        'prefix': os.environ.get('BACKUP_S3_PREFIX', 'getszy-backups').strip('/'),
    }


def _backup_tier(ts):
    """GFS tier: monthly on the 1st, weekly on Monday, otherwise daily."""
    try:
        d = datetime.strptime(ts, '%Y%m%d-%H%M%S')
    except Exception:
        return 'daily'
    if d.day == 1:
        return 'monthly'
    if d.weekday() == 0:
        return 'weekly'
    return 'daily'


def sync_backup_offsite(out_dir):
    cfg = _offsite_config()
    if not cfg:
        return False
    try:
        import boto3
    except ImportError:
        logger.warning('backup: boto3 not installed; skipping off-site sync')
        return False
    try:
        name = os.path.basename(out_dir)
        tier = _backup_tier(name)
        client = boto3.client('s3', endpoint_url=cfg['endpoint'], region_name=cfg['region'])
        prefix = f"{cfg['prefix']}/{tier}/{name}"
        for root, _, files in os.walk(out_dir):
            for f in files:
                local = os.path.join(root, f)
                rel = os.path.relpath(local, out_dir)
                client.upload_file(local, cfg['bucket'], f"{prefix}/{rel}")
        logger.info(f'backup off-site sync ok: s3://{cfg["bucket"]}/{prefix}')
        return True
    except Exception as e:  # pragma: no cover - depends on env/creds
        logger.error(f'backup off-site sync failed: {e}')
        return False


def restore_from_offsite(tier, name, dest_dir):
    """Download an off-site backup tier to dest_dir for disaster recovery."""
    cfg = _offsite_config()
    if not cfg:
        raise RuntimeError('BACKUP_S3_BUCKET is not configured')
    import boto3
    client = boto3.client('s3', endpoint_url=cfg['endpoint'], region_name=cfg['region'])
    prefix = f"{cfg['prefix']}/{tier}/{name}"
    paginator = client.get_paginator('list_objects_v2')
    os.makedirs(dest_dir, exist_ok=True)
    found = 0
    for page in paginator.paginate(Bucket=cfg['bucket'], Prefix=prefix):
        for obj in page.get('Contents', []):
            rel = obj['Key'][len(prefix):].lstrip('/')
            target = os.path.join(dest_dir, rel)
            os.makedirs(os.path.dirname(target) or dest_dir, exist_ok=True)
            client.download_file(cfg['bucket'], obj['Key'], target)
            found += 1
    if not found:
        raise FileNotFoundError(f'no off-site objects under {prefix}')
    return dest_dir


async def backup_scheduler():
    await asyncio.sleep(600)
    while True:
        try:
            await run_backup()
        except Exception as e:  # pragma: no cover - environment dependent
            logger.error(f'backup scheduler error: {e}')
        await asyncio.sleep(BACKUP_INTERVAL_SECONDS)
