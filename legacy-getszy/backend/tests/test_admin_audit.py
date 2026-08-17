"""Behavioral tests for Tier 0 #3: searchable audit trail.

Mocks `db` (no live Mongo). Proves:
  - GET /admin/audit-logs returns {items, total}
  - admin actions (refund) write a refund_issued audit event
Run: python -m pytest tests/test_admin_audit.py -v
"""
import os
import re
import asyncio

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

import routes_admin  # noqa: E402
import routes_cart_orders  # noqa: E402


class FakeCursor:
    def __init__(self, items):
        self.items = list(items)

    def sort(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    async def to_list(self, length=None):
        return list(self.items)[:length] if length else list(self.items)

    def __aiter__(self):
        async def gen():
            for x in self.items:
                yield x
        return gen()


class FakeColl:
    def __init__(self, items=None, capture=None):
        self.items = list(items or [])
        self.capture = capture

    def find(self, query=None, projection=None):
        items = self.items
        if query and '$or' in query:
            ors = query['$or']

            def matches(it):
                for cond in ors:
                    for field, spec in cond.items():
                        rx = spec.get('$regex') if isinstance(spec, dict) else None
                        if rx and re.search(rx, str(it.get(field, '')), re.I):
                            return True
                return False
            items = [it for it in items if matches(it)]
        return FakeCursor(items)

    async def find_one(self, *a, **k):
        return self.items[0] if self.items else None

    async def insert_one(self, doc):
        if self.capture is not None:
            self.capture.append(doc)
        return doc

    async def update_one(self, *a, **k):
        return None


class FakeDB:
    def __init__(self, **cols):
        for k, v in cols.items():
            setattr(self, k, v)


def test_audit_logs_view_shape_and_search():
    logs = FakeColl([
        {'id': '1', 'admin_id': 'a', 'action': 'refund_issued',
         'detail': 'Refunded 100', 'level': 'info', 'created_at': '2024-01-01'},
        {'id': '2', 'admin_id': 'b', 'action': 'gst_config_updated',
         'detail': 'GST updated', 'level': 'info', 'created_at': '2024-01-02'},
    ])
    routes_admin.db = FakeDB(audit_logs=logs)

    async def run():
        return await routes_admin.get_audit_logs(limit=10, q='refund')
    res = asyncio.run(run())
    assert 'items' in res and 'total' in res
    # q='refund' should narrow to the refund_issued record only
    assert len(res['items']) == 1
    assert res['items'][0]['action'] == 'refund_issued'


def test_refund_writes_audit_event():
    audit_cap = []
    fake_db = FakeDB(
        orders=FakeColl([{'id': 'o1', 'order_number': 'ORD-1'}]),
        refunds=FakeColl(capture=[]),
        audit_logs=FakeColl(capture=audit_cap),
    )
    routes_cart_orders.db = fake_db

    async def run():
        return await routes_cart_orders.process_refund(
            routes_cart_orders.RefundIn(order_id='o1', amount=100.0, reason='bad'),
            {'id': 'admin1', 'email': 'a@x.com'},
        )
    asyncio.run(run())

    assert any(e['action'] == 'refund_issued' for e in audit_cap)
    assert any('ORD-1' in e.get('detail', '') for e in audit_cap)
