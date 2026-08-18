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
from pymongo import ReplaceOne
from db import db

logger = logging.getLogger('getszy')

BACKUP_ROOT = os.environ.get('BACKUP_DIR', '/app/backups')
RETENTION = int(os.environ.get('BACKUP_RETENTION_DAYS', '7'))
# RPO control: how often the background scheduler snapshots the database.
# Default 4h (down from 24h) to bound data-loss exposure during growth.
BACKUP_INTERVAL_SECONDS = int(os.environ.get('BACKUP_INTERVAL_HOURS', '4')) * 3600
# Populated by run_backup(); consumed by the RPO/RTO status endpoint + metrics.
LAST_BACKUP = {'ts': None, 'ts_epoch': None, 'dir': None, 'docs': 0}


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
        try:
            from middleware import set_last_backup_ts
            set_last_backup_ts(epoch)
        except Exception:
            pass
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
        logger.info(f'backup ok: {out_dir} ({total_docs} docs)')
        return out_dir
    except Exception as e:  # pragma: no cover - environment dependent
        logger.error(f'backup failed: {e}')
        return None


def _prune():
    try:
        dirs = sorted(glob.glob(os.path.join(BACKUP_ROOT, 'getszy-*')))
        while len(dirs) > RETENTION:
            old = dirs.pop(0)
            shutil.rmtree(old, ignore_errors=True)
    except Exception as e:  # pragma: no cover - environment dependent
        logger.warning(f'backup prune warning: {e}')


async def restore_backup(out_dir):
    """Restore a backup directory produced by :func:`run_backup`."""
    out_dir = os.path.abspath(out_dir)
    if not os.path.isdir(out_dir):
        raise ValueError(f'not a directory: {out_dir}')
    files = sorted(glob.glob(os.path.join(out_dir, '*.jsonl')))
    if not files:
        raise ValueError(f'no .jsonl files in {out_dir}')
    restored = 0
    batch = 1000
    for path in files:
        name = os.path.splitext(os.path.basename(path))[0]
        coll = db[name]
        ops = []
        with open(path, 'r', encoding='utf-8') as fh:
            for line in fh:
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


async def backup_scheduler():
    await asyncio.sleep(600)
    while True:
        try:
            await run_backup()
        except Exception as e:  # pragma: no cover - environment dependent
            logger.error(f'backup scheduler error: {e}')
        await asyncio.sleep(BACKUP_INTERVAL_SECONDS)
