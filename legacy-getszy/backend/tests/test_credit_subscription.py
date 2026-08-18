import os
import sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests-32chars-minimum!!')

from datetime import datetime, timezone

import credits as credits_mod
import subscription as sub_mod


# ── In-memory fake Mongo ──────────────────────────────────────────────────────

def _apply_update(doc, update):
    for op, fields in update.items():
        if op == '$inc':
            for k, v in fields.items():
                doc[k] = doc.get(k, 0) + v
        elif op == '$set':
            for k, v in fields.items():
                parts = k.split('.')
                d = doc
                for p in parts[:-1]:
                    cur = d.get(p)
                    if not isinstance(cur, dict):
                        cur = {}
                        d[p] = cur
                    d = cur
                d[parts[-1]] = v
        elif op == '$push':
            for k, v in fields.items():
                doc.setdefault(k, []).append(v)


def _matches(doc, flt):
    for k, v in flt.items():
        if isinstance(v, dict) and '$gte' in v:
            if not (doc.get(k, 0) >= v['$gte']):
                return False
        else:
            if doc.get(k) != v:
                return False
    return True


class _Coll:
    def __init__(self):
        self._by_id = {}

    def _get(self, user_id):
        return self._by_id.setdefault(user_id, {'id': user_id, 'credits': 0,
                                                'role': 'customer', 'subscription': None})

    async def find_one(self, flt, projection=None):
        if 'id' in flt:
            doc = self._by_id.get(flt['id'])
            return dict(doc) if doc else None
        return None

    async def find_one_and_update(self, flt, update, return_document=False, projection=None):
        doc = self._get(flt['id'])
        if not _matches(doc, flt):
            return None
        _apply_update(doc, update)
        return dict(doc)

    async def update_one(self, flt, update, upsert=False):
        doc = self._get(flt['id'])
        _apply_update(doc, update)
        return types.SimpleNamespace(modified_count=1)

    async def insert_one(self, doc):
        return types.SimpleNamespace(inserted_id='x')


class _FDB:
    def __init__(self):
        self.users = _Coll()
        self.credit_transactions = _Coll()
        self.billing_processed_payments = _Coll()


@pytest.fixture
def fake_db(monkeypatch):
    db = _FDB()
    monkeypatch.setattr(credits_mod, 'db', db)
    monkeypatch.setattr(sub_mod, 'db', db)
    return db


# ── grant on subscription ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_grant_plan_grants_pro_credits(fake_db):
    sub = await sub_mod.grant_plan('u1', 'pro', days=30)
    assert sub['plan'] == 'pro'
    assert sub['status'] == 'active'
    bal = await credits_mod.get_balance('u1')
    assert bal == credits_mod.PLAN_CREDIT_GRANT['pro']  # 125


@pytest.mark.asyncio
async def test_grant_plan_grants_elite_credits(fake_db):
    await sub_mod.grant_plan('u1', 'elite', days=30)
    assert await credits_mod.get_balance('u1') == credits_mod.PLAN_CREDIT_GRANT['elite']  # 300


@pytest.mark.asyncio
async def test_start_trial_grants_pro_credits(fake_db):
    user = {'id': 'u1', 'role': 'customer', 'subscription': None}
    await sub_mod.start_trial(user)
    # default effective sub is created as free; trial flips to pro + credits
    bal = await credits_mod.get_balance('u1')
    assert bal == credits_mod.PLAN_CREDIT_GRANT['pro']


# ── subscription ends at zero credits ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_subscription_ends_when_credits_hit_zero(fake_db):
    await sub_mod.grant_plan('u1', 'pro', days=30)  # 125 credits
    # drain the balance with 125x 1-credit actions
    for _ in range(125):
        ok, _, bal = await credits_mod.deduct('u1', 'script')  # cost 1
        assert ok
    assert bal == 0
    ended = await sub_mod.end_subscription_if_no_credits('u1')
    assert ended
    user = await fake_db.users.find_one({'id': 'u1'})
    assert user['subscription']['plan'] == 'free'
    assert user['subscription']['status'] == 'expired'


@pytest.mark.asyncio
async def test_deduct_to_zero_ends_subscription_integration(fake_db):
    await sub_mod.grant_plan('u1', 'pro', days=30)
    # one big action that exactly zeroes the bucket
    ok, _, bal = await credits_mod.deduct('u1', 'faceless_video')  # cost 10 -> 115
    assert ok and bal == 115
    # exhaust remaining 115 with script (cost 1) x115
    for _ in range(115):
        await credits_mod.deduct('u1', 'script')
    final = await fake_db.users.find_one({'id': 'u1'})
    assert final['subscription']['plan'] == 'free'
    assert final['subscription']['status'] == 'expired'


@pytest.mark.asyncio
async def test_admin_bypass_does_not_end_subscription(fake_db):
    await sub_mod.grant_plan('u1', 'pro', days=30)
    user = {'id': 'u1', 'role': 'admin', 'credits': 0}
    ok, _, bal = await credits_mod.deduct('u1', 'script', user=user)
    assert ok is True
    # admin early-returns; subscription untouched
    final = await fake_db.users.find_one({'id': 'u1'})
    assert final['subscription']['plan'] == 'pro'


@pytest.mark.asyncio
async def test_paid_plan_not_expired_by_time_when_credits_remain(fake_db):
    """Credit-exhaustion is the SOLE terminator — a paid plan must NOT downgrade
    just because its calendar period_end has passed (no time cap)."""
    await sub_mod.grant_plan('u1', 'pro', days=30)
    await fake_db.users.update_one(
        {'id': 'u1'},
        {'$set': {'subscription.current_period_end': '2000-01-01T00:00:00+00:00'}},
    )
    user = await fake_db.users.find_one({'id': 'u1'})
    sub = await sub_mod.effective_subscription(user)
    assert sub['plan'] == 'pro'        # NOT downgraded by time
    assert sub['status'] == 'active'
