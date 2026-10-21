"""Tests for one-time product-order Razorpay payment capture (no live Mongo).

Patches db + the Razorpay client directly so it runs fast in CI / locally.

Covers the hardened order payment invariants:
- order-create charges the SERVER-side order total (client amount must match)
- order-verify re-fetches the payment from Razorpay and enforces
  amount/currency/order-binding + payment-id idempotency
"""
import asyncio
import hmac
import hashlib
from types import SimpleNamespace

import pytest


@pytest.fixture
def mod():
    import routes_razorpay
    return routes_razorpay


class FakeCollection:
    def __init__(self):
        self.docs = {}
        self.updates = []
        self.inserts = []

    async def find_one(self, q, proj=None):
        if isinstance(q, dict) and q.get('order_number'):
            return self.docs.get(q['order_number'])
        if isinstance(q, dict) and q.get('payment_id'):
            for doc in self.docs.values():
                if doc.get('payment_id') == q['payment_id']:
                    return doc
        return None

    async def insert_one(self, doc):
        self.inserts.append(doc)
        key = doc.get('payment_id') or doc.get('order_number')
        if key is not None:
            self.docs[key] = dict(doc)
        return SimpleNamespace(inserted_id=key)

    async def update_one(self, q, update):
        self.updates.append((q, update))
        if isinstance(q, dict) and q.get('order_number') in self.docs:
            self.docs[q['order_number']].update(update.get('$set', {}))
            return SimpleNamespace(matched_count=1, modified_count=1)
        return SimpleNamespace(matched_count=0, modified_count=0)


class FakeDB:
    def __init__(self):
        self.orders = FakeCollection()
        self.gs_invoices = FakeCollection()
        self.billing_processed_payments = FakeCollection()


class FakeRzClient:
    def __init__(self, payment):
        self.order = self
        self.payment = self
        self._payment = payment

    def create(self, payload):
        return {'id': 'rz_' + str(payload.get('receipt', 'x'))}

    def fetch(self, payment_id):
        return self._payment


def _captured_payment(amount_paise, rz_order_id='rz_ORD1001', currency='INR', status='captured'):
    return {
        'id': 'pay_123',
        'status': status,
        'amount': amount_paise,
        'order_id': rz_order_id,
        'currency': currency,
    }


@pytest.fixture
def setup(mod, monkeypatch):
    db = FakeDB()
    db.orders.docs['ORD1001'] = {
        'order_number': 'ORD1001',
        'user_id': 'u1',
        'payment_status': 'pending',
        'total': 500.0,
        'razorpay_order_id': 'rz_ORD1001',
    }
    monkeypatch.setattr(mod, 'db', db)
    monkeypatch.setattr(
        mod, '_client', lambda: FakeRzClient(_captured_payment(50000)))
    monkeypatched_db = db
    return monkeypatched_db


def _sig(secret, rz_order_id, payment_id):
    msg = f'{rz_order_id}|{payment_id}'.encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()


def test_order_create_unconfigured(mod):
    mod.KEY_ID = ''
    mod.KEY_SECRET = ''
    resp = asyncio.run(mod.order_create(
        type('B', (), {'order_number': 'ORD1001', 'amount': 500.0})(), user={'id': 'u1'}))
    assert resp['configured'] is False


def test_order_create_configured_uses_order_total(mod, setup):
    mod.KEY_ID = 'key_abc'
    mod.KEY_SECRET = 'sec_xyz'
    resp = asyncio.run(mod.order_create(
        type('B', (), {'order_number': 'ORD1001', 'amount': 500.0})(), user={'id': 'u1'}))
    assert resp['configured'] is True
    assert resp['razorpay_order_id'] == 'rz_ORD1001'
    assert resp['amount'] == 500.0
    assert resp['currency'] == 'INR'
    assert setup.orders.docs['ORD1001']['razorpay_order_id'] == 'rz_ORD1001'


def test_order_create_rejects_amount_mismatch(mod, setup):
    mod.KEY_ID = 'key_abc'
    mod.KEY_SECRET = 'sec_xyz'
    with pytest.raises(Exception) as exc_info:
        asyncio.run(mod.order_create(
            type('B', (), {'order_number': 'ORD1001', 'amount': 1.0})(), user={'id': 'u1'}))
    assert 'does not match' in str(exc_info.value)


def test_order_verify_marks_paid(mod, monkeypatch):
    mod.KEY_ID = 'key_abc'
    mod.KEY_SECRET = 'sec_xyz'
    rz_order_id = 'rz_ORD1001'
    payment_id = 'pay_123'
    setup = FakeDB()
    setup.orders.docs['ORD1001'] = {
        'order_number': 'ORD1001', 'user_id': 'u1', 'payment_status': 'pending',
        'total': 500.0, 'razorpay_order_id': rz_order_id,
    }
    monkeypatch.setattr(mod, 'db', setup)
    monkeypatch.setattr(
        mod, '_client', lambda: FakeRzClient(_captured_payment(50000)))
    # neutralise the live-event broadcast import side effects
    import live_events
    monkeypatch.setattr(live_events, 'broadcast_admin_event', lambda *a, **k: None)
    resp = asyncio.run(mod.order_verify(
        type('B', (), {'razorpay_payment_id': payment_id, 'razorpay_order_id': rz_order_id,
                       'razorpay_signature': _sig('sec_xyz', rz_order_id, payment_id),
                       'order_number': 'ORD1001'})(), user={'id': 'u1'}))
    assert resp['ok'] is True
    assert resp['payment_status'] == 'paid'
    assert setup.orders.docs['ORD1001']['payment_status'] == 'paid'
    assert any(i.get('payment_id') == payment_id for i in setup.billing_processed_payments.inserts)


def test_order_verify_rejects_one_rupee_attack(mod, monkeypatch):
    """The CVE of this module: pay Rs 1 for a Rs 500 order must be refused."""
    mod.KEY_ID = 'key_abc'
    mod.KEY_SECRET = 'sec_xyz'
    payment_id = 'pay_123'
    setup = FakeDB()
    setup.orders.docs['ORD1001'] = {
        'order_number': 'ORD1001', 'user_id': 'u1', 'payment_status': 'pending',
        'total': 500.0, 'razorpay_order_id': 'rz_ORD1001',
    }
    monkeypatch.setattr(mod, 'db', setup)
    monkeypatch.setattr(
        mod, '_client', lambda: FakeRzClient(_captured_payment(100)))  # paid Rs 1
    import live_events
    monkeypatch.setattr(live_events, 'broadcast_admin_event', lambda *a, **k: None)
    with pytest.raises(Exception) as exc_info:
        asyncio.run(mod.order_verify(
            type('B', (), {'razorpay_payment_id': payment_id, 'razorpay_order_id': 'rz_ORD1001',
                           'razorpay_signature': _sig('sec_xyz', 'rz_ORD1001', payment_id),
                           'order_number': 'ORD1001'})(), user={'id': 'u1'}))
    assert 'does not match' in str(exc_info.value)
    assert setup.orders.docs['ORD1001']['payment_status'] == 'pending'


def test_order_verify_rejects_foreign_razorpay_order_id(mod, monkeypatch):
    mod.KEY_ID = 'key_abc'
    mod.KEY_SECRET = 'sec_xyz'
    payment_id = 'pay_123'
    setup = FakeDB()
    setup.orders.docs['ORD1001'] = {
        'order_number': 'ORD1001', 'user_id': 'u1', 'payment_status': 'pending',
        'total': 500.0, 'razorpay_order_id': 'rz_REAL',
    }
    monkeypatch.setattr(mod, 'db', setup)
    monkeypatch.setattr(
        mod, '_client', lambda: FakeRzClient(_captured_payment(50000)))
    import live_events
    monkeypatch.setattr(live_events, 'broadcast_admin_event', lambda *a, **k: None)
    with pytest.raises(Exception) as exc_info:
        asyncio.run(mod.order_verify(
            type('B', (), {'razorpay_payment_id': payment_id, 'razorpay_order_id': 'rz_FORGED',
                           'razorpay_signature': _sig('sec_xyz', 'rz_FORGED', payment_id),
                           'order_number': 'ORD1001'})(), user={'id': 'u1'}))
    assert 'does not belong' in str(exc_info.value)


def test_order_verify_marks_paid_once_for_replay(mod, monkeypatch):
    mod.KEY_ID = 'key_abc'
    mod.KEY_SECRET = 'sec_xyz'
    payment_id = 'pay_123'
    setup = FakeDB()
    setup.orders.docs['ORD1001'] = {
        'order_number': 'ORD1001', 'user_id': 'u1', 'payment_status': 'paid',
        'total': 500.0, 'razorpay_order_id': 'rz_ORD1001',
        'razorpay_payment_id': payment_id,
    }
    setup.billing_processed_payments.docs[payment_id] = {
        'payment_id': payment_id, 'user_id': 'u1', 'order_number': 'ORD1001',
    }
    monkeypatch.setattr(mod, 'db', setup)
    monkeypatch.setattr(
        mod, '_client', lambda: FakeRzClient(_captured_payment(50000)))
    import live_events
    monkeypatch.setattr(live_events, 'broadcast_admin_event', lambda *a, **k: None)
    resp = asyncio.run(mod.order_verify(
        type('B', (), {'razorpay_payment_id': payment_id, 'razorpay_order_id': 'rz_ORD1001',
                       'razorpay_signature': _sig('sec_xyz', 'rz_ORD1001', payment_id),
                       'order_number': 'ORD1001'})(), user={'id': 'u1'}))
    assert resp['ok'] is True
    assert resp['payment_status'] == 'paid'


def test_order_verify_bad_signature(mod, monkeypatch):
    mod.KEY_ID = 'key_abc'
    mod.KEY_SECRET = 'sec_xyz'
    with pytest.raises(Exception):
        asyncio.run(mod.order_verify(
            type('B', (), {'razorpay_payment_id': 'pay_123', 'razorpay_order_id': 'rz_ORD1001',
                           'razorpay_signature': 'deadbeef', 'order_number': 'ORD1001'})(), user={'id': 'u1'}))
