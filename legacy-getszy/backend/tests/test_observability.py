"""Tests for Tier 2 #14 observability/SLA aggregation (no Mongo)."""
import os
import asyncio

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

import routes_observability  # noqa: E402


class FakeCursor:
    def __init__(self, items):
        self._items = items

    def __aiter__(self):
        async def gen():
            for i in self._items:
                yield i
        return gen()


class FakeColl:
    def __init__(self, data=None):
        self._data = data or []

    def aggregate(self, pipeline):
        return FakeCursor(self._data)

    async def count_documents(self, q):
        return 0


class FakeDB:
    def __init__(self, agg):
        self.request_logs = FakeColl(agg)
        for n in ('users', 'orders', 'products', 'gs_invoices', 'automations'):
            setattr(self, n, FakeColl())


def test_compute_sla_aggregates_correctly():
    lats = list(range(1, 101))  # 1..100 ms
    routes_observability.db = FakeDB([{'total': 100, 'errors': 5, 'latencies': lats}])
    sla = asyncio.run(routes_observability.compute_sla(24))
    assert sla['total'] == 100
    assert sla['errors'] == 5
    assert sla['error_rate'] == 5.0
    assert sla['uptime_pct'] == 95.0
    assert sla['p95_ms'] == 95  # 95th percentile of 1..100 is 95


def test_compute_sla_empty():
    routes_observability.db = FakeDB([])
    sla = asyncio.run(routes_observability.compute_sla(24))
    assert sla['total'] == 0
    assert sla['uptime_pct'] == 100.0
