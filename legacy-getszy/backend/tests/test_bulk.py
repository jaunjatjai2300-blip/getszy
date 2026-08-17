"""Behavioral tests for Tier 2 #12 bulk operations (backend only).

Mocks db; verifies batch updates + audit logging. No auth/Mongo needed.
Run: python -m pytest tests/test_bulk.py -v
"""
import os
import asyncio

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

import routes_bulk  # noqa: E402


class FakeResult:
    def __init__(self, n):
        self.matched_count = n


class FakeColl:
    def __init__(self, find=None):
        self._find = find or {}
        self.inserted = []
        self.updates = 0

    async def update_many(self, q, u):
        return FakeResult(2 if 'id' in q.get('$in', {}) or True else 0)

    async def find_one(self, q, p=None):
        return self._find

    async def update_one(self, q, u):
        self.updates += 1
        return FakeResult(1)

    async def insert_one(self, doc):
        self.inserted.append(doc)
        return None


class FakeDB:
    def __init__(self, order=None):
        self.orders = FakeColl(find=order)
        self.users = FakeColl()
        self.refunds = FakeColl()
        self.audit_logs = FakeColl()


def test_bulk_order_status_updates_and_audits():
    db = FakeDB()
    routes_bulk.db = db
    res = asyncio.run(routes_bulk.bulk_order_status(
        routes_bulk.OrderStatusBulk(ids=['o1', 'o2'], status='shipped'), {'email': 'a@admin'}))
    assert res['ok'] is True
    assert res['matched'] == 2
    assert len(db.audit_logs.inserted) == 1
    assert db.audit_logs.inserted[0]['action'] == 'bulk_order_status'


def test_bulk_order_refund_creates_refund_records():
    order = {'id': 'o1', 'order_number': 'ORD-1', 'total': 500}
    db = FakeDB(order=order)
    routes_bulk.db = db
    res = asyncio.run(routes_bulk.bulk_order_refund(
        routes_bulk.RefundBulk(ids=['o1'], reason='bad'), {'email': 'a@admin'}))
    assert res['refunded'] == 1
    assert len(db.refunds.inserted) == 1
    assert db.refunds.inserted[0]['amount'] == 500
    assert db.orders.updates == 1


def test_bulk_user_role_validates():
    import pytest
    db = FakeDB()
    routes_bulk.db = db
    with pytest.raises(Exception):
        asyncio.run(routes_bulk.bulk_user_role(
            routes_bulk.UserRoleBulk(ids=['u1'], role='supervillain'), {'email': 'a@admin'}))
