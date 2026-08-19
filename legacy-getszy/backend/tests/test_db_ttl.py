import os
import sys
import json
import glob
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests-32chars-minimum!!')

from datetime import datetime, timezone
from bson import ObjectId

from retention import _stamp_doc, _install_createdAt_stamp
import backup as backup_mod


# ─────────────────────────────────────────────────────────────────────────────
# _stamp_doc — the core TTL-stamping logic
# ─────────────────────────────────────────────────────────────────────────────

def test_stamp_adds_bson_date_for_ttl_collection():
    out = _stamp_doc({'topic': 'x'}, 'video_jobs')
    assert 'createdAt' in out
    assert isinstance(out['createdAt'], datetime)
    assert out['topic'] == 'x'


def test_stamp_skips_non_ttl_collection():
    assert 'createdAt' not in _stamp_doc({'email': 'a@b.com'}, 'users')


def test_stamp_does_not_overwrite_existing_createdAt():
    existing = datetime(2020, 1, 1, tzinfo=timezone.utc)
    out = _stamp_doc({'createdAt': existing}, 'video_jobs')
    assert out['createdAt'] is existing


def test_stamp_ignores_non_dict():
    assert _stamp_doc('not a dict', 'video_jobs') == 'not a dict'


# ─────────────────────────────────────────────────────────────────────────────
# _install_createdAt_stamp — wires stamping into motor's insert_one
# ─────────────────────────────────────────────────────────────────────────────

class _FakeColl:
    def __init__(self, name):
        self.name = name
        self.inserted = []

    async def insert_one(self, doc, *a, **k):
        self.inserted.append(doc)
        return doc


@pytest.mark.asyncio
async def test_class_patch_stamps_ttl_inserts_only(monkeypatch):
    import motor.motor_asyncio as mm
    # Redirect the motor class the patcher imports to our fake
    monkeypatch.setattr(mm, 'AsyncIOMotorCollection', _FakeColl)
    _install_createdAt_stamp()

    ttl = _FakeColl('video_jobs')
    await ttl.insert_one({'topic': 'hello'})
    assert len(ttl.inserted) == 1
    assert isinstance(ttl.inserted[0]['createdAt'], datetime)

    non_ttl = _FakeColl('users')
    await non_ttl.insert_one({'email': 'a@b.com'})
    assert 'createdAt' not in non_ttl.inserted[0]


# ─────────────────────────────────────────────────────────────────────────────
# backup / restore round-trip (pure pymongo, no external binary)
# ─────────────────────────────────────────────────────────────────────────────

class _FCursor:
    def __init__(self, docs):
        self._docs = docs
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i >= len(self._docs):
            raise StopAsyncIteration
        d = self._docs[self._i]
        self._i += 1
        return d


class _FColl:
    def __init__(self):
        self._store = []
        self._replaced = []

    def find(self, q=None):
        return _FCursor(self._store)

    async def replace_one(self, flt, doc, upsert=False):
        self._replaced.append(doc)
        return types.SimpleNamespace(upserted_id=doc.get('_id'))

    async def insert_one(self, doc):
        self._store.append(doc)
        return doc

    async def bulk_write(self, operations, **kwargs):
        # Minimal stand-in so restore_backup() (which uses ReplaceOne via
        # coll.bulk_write) can exercise the round-trip against the fake DB.
        # pymongo stores op fields in private attrs: _filter, _doc, _upsert.
        for op in operations:
            flt = getattr(op, '_filter', None) or getattr(op, 'filter', {})
            doc = getattr(op, '_doc', None)
            if doc is not None:
                upsert = getattr(op, '_upsert', False) or getattr(op, 'upsert', False)
                await self.replace_one(flt, doc, upsert=upsert)
            else:
                ins = getattr(op, '_doc', None) or getattr(op, 'document', None)
                if ins is not None:
                    await self.insert_one(ins)
        return types.SimpleNamespace(upserted_count=0, modified_count=0, inserted_count=0)


class _FDB:
    def __init__(self):
        self._c = {}

    def __getattr__(self, name):
        if name not in self._c:
            self._c[name] = _FColl()
        return self._c[name]

    def __getitem__(self, name):
        if name not in self._c:
            self._c[name] = _FColl()
        return self._c[name]

    async def list_collection_names(self):
        return list(self._c.keys())


@pytest.mark.asyncio
async def test_backup_restore_roundtrip(tmp_path, monkeypatch):
    src = _FDB()
    src._c['widgets'] = _FColl()
    src.widgets._store = [
        {'_id': ObjectId(), 'name': 'a', 'n': 1},
        {'_id': ObjectId(), 'name': 'b', 'when': datetime(2021, 1, 1, tzinfo=timezone.utc)},
    ]
    monkeypatch.setattr(backup_mod, 'db', src)
    monkeypatch.setenv('BACKUP_DIR', str(tmp_path))
    monkeypatch.setenv('BACKUP_RETENTION_DAYS', '3')

    out = await backup_mod.run_backup()
    assert out and os.path.isdir(out)

    jsonl = glob.glob(os.path.join(out, '*.jsonl'))
    assert any('widgets.jsonl' in f for f in jsonl)

    manifest = json.load(open(os.path.join(out, 'manifest.json')))
    assert manifest['collections']['widgets'] == 2

    # Restore into a fresh database and confirm docs survive (incl. datetimes)
    dst = _FDB()
    monkeypatch.setattr(backup_mod, 'db', dst)
    restored = await backup_mod.restore_backup(out)
    assert restored == 2
    assert len(dst.widgets._replaced) == 2
    assert isinstance(dst.widgets._replaced[1]['when'], datetime)
