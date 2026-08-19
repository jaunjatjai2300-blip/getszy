import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests-32chars-minimum!!')
os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('DB_NAME', 'getszy_backup_test')

from datetime import datetime, timezone
from bson import ObjectId

import backup as backup_mod


def _tmp_backup_dir():
    d = tempfile.mkdtemp(prefix='bktest_')
    backup_mod.BACKUP_ROOT = d
    return d


@pytest.mark.integration
@pytest.mark.asyncio
async def test_backup_restore_roundtrip_preserves_types():
    """Backup -> drop -> restore must return ObjectId/datetime intact (RPO data integrity)."""
    from db import db
    coll = db['backup_rt']
    await coll.delete_many({})
    oid = ObjectId()
    when = datetime(2021, 6, 15, 12, 30, tzinfo=timezone.utc)
    await coll.insert_one({'_id': oid, 'name': 'hello', 'when': when, 'n': 42})

    backup_dir = _tmp_backup_dir()
    out = await backup_mod.run_backup()
    assert out, 'run_backup produced no output dir'

    await coll.delete_many({})
    assert await coll.count_documents({}) == 0

    restored = await backup_mod.restore_backup(os.path.join(backup_dir, 'latest'))
    assert restored >= 1

    doc = await coll.find_one({'_id': oid})
    assert doc is not None, 'restored document missing'
    assert doc['name'] == 'hello'
    assert isinstance(doc['when'], datetime)
    assert doc['when'] == when  # datetime preserved exactly
    assert doc['n'] == 42
    await coll.delete_many({})


@pytest.mark.integration
@pytest.mark.asyncio
async def test_restore_is_idempotent():
    """Re-running restore must not create duplicate documents."""
    from db import db
    coll = db['backup_idem']
    await coll.delete_many({})
    await coll.insert_one({'_id': ObjectId(), 'v': 1})

    backup_dir = _tmp_backup_dir()
    await backup_mod.run_backup()
    await coll.delete_many({})
    await backup_mod.restore_backup(os.path.join(backup_dir, 'latest'))
    first = await coll.count_documents({})
    assert first == 1

    await backup_mod.restore_backup(os.path.join(backup_dir, 'latest'))
    assert await coll.count_documents({}) == first
    await coll.delete_many({})


def test_backup_tier_logic():
    """GFS tier selection: 1st -> monthly, Monday -> weekly, else daily."""
    assert backup_mod._backup_tier('20260101-000000') == 'monthly'
    # 2026-06-15 is a Monday -> weekly
    assert backup_mod._backup_tier('20260615-120000') == 'weekly'
    # 2026-06-17 is a Wednesday -> daily
    assert backup_mod._backup_tier('20260617-120000') == 'daily'


def test_offsite_sync_is_noop_without_bucket():
    """Without BACKUP_S3_BUCKET the off-site sync is a safe no-op."""
    import os as _os
    _os.environ.pop('BACKUP_S3_BUCKET', None)
    assert backup_mod.sync_backup_offsite('/nonexistent/path') is False
