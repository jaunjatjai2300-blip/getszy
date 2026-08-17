"""Tests for one-time product-order Razorpay payment capture (no live Mongo).

Patches db + the Razorpay client directly so it runs fast in CI / locally.
"""
import asyncio
import hmac
import hashlib

import pytest


@pytest.fixture
def mod():
    import routes_razorpay
    return routes_razorpay


class FakeCollection:
    def __init__(self):
        self.docs = {}
        self.updates = []

    async def find_one(self, q, proj=None):
        if isinstance(q, dict) and q.get('order_number'):
            return self.docs.get(q['order_number'])
        return None

    async def update_one(self, q, update):
        self.updates.append((q, update))
        if isinstance(q, dict) and q.get('order_number') in self.docs:
            self.docs[q['order_number']].update(update.get('$set', {}))
        return None


class FakeDB:
    def __init__(self):
        self.orders = FakeCollection()
        self.gs_invoices = FakeCollection()


class FakeRzClient:
    def __init__(self):
        self.order = self

    def create(self, payload):
        return {'id': 'rz_' + str(payload.get('receipt', 'x'))}


@pytest.fixture
def setup(mod, monkeypatch):
    db = FakeDB()
    db.orders.docs['ORD1001'] = {'order_number': 'ORD1001', 'user_id': 'u1', 'payment_status': 'pending'}
    monkeypatch.setattr(mod, 'db', db)
    monkeypatch.setattr(mod, '_client', lambda: FakeRzClient())
    return db


def _sig(secret, rz_order_id, payment_id):
    msg = f'{rz_order_id}|{payment_id}'.encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def test_order_create_unconfigured(mod):
    mod.KEY_ID = ''
    mod.KEY_SECRET = ''
    resp = asyncio.run(mod.order_create(
        type('B', (), {'order_number': 'ORD1001', 'amount': 500.0})(), user={'id': 'u1'}))
    assert resp['configured'] is False


def test_order_create_configured(mod, setup):
    mod.KEY_ID = 'key_abc'
    mod.KEY_SECRET = 'sec_xyz'
    resp = asyncio.run(mod.order_create(
        type('B', (), {'order_number': 'ORD1001', 'amount': 500.0})(), user={'id': 'u1'}))
    assert resp['configured'] is True
    assert resp['razorpay_order_id'] == 'rz_ORD1001'
    assert resp['key_id'] == 'key_abc'


def test_order_verify_marks_paid(mod, setup):
    mod.KEY_ID = 'key_abc'
    mod.KEY_SECRET = 'sec_xyz'
    rz_order_id = 'rz_ORD1001'
    payment_id = 'pay_123'
    sig = _sig('sec_xyz', rz_order_id, payment_id)
    # neutralise the live-event broadcast import side effects
    import live_events
    monkeypatch = _Monkey()
    monkeypatch.set(live_events, 'broadcast_admin_event', lambda *a, **k: None)
    resp = asyncio.run(mod.order_verify(
        type('B', (), {'razorpay_payment_id': payment_id, 'razorpay_order_id': rz_order_id,
                       'razorpay_signature': sig, 'order_number': 'ORD1001'})(), user={'id': 'u1'}))
    assert resp['ok'] is True
    assert resp['payment_status'] == 'paid'
    assert setup.orders.docs['ORD1001']['payment_status'] == 'paid'


def test_order_verify_bad_signature(mod, setup):
    import pytest as _pytest
    mod.KEY_ID = 'key_abc'
    mod.KEY_SECRET = 'sec_xyz'
    with _pytest.raises(Exception):
        asyncio.run(mod.order_verify(
            type('B', (), {'razorpay_payment_id': 'pay_123', 'razorpay_order_id': 'rz_ORD1001',
                           'razorpay_signature': 'deadbeef', 'order_number': 'ORD1001'})(), user={'id': 'u1'}))


class _Monkey:
    def set(self, obj, attr, val):
        self._orig = (obj, attr, getattr(obj, attr))
        setattr(obj, attr, val)

    def __del__(self):
        try:
            setattr(*self._orig[:2], self._orig[2])
        except Exception:
            pass
