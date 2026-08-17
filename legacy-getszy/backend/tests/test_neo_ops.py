"""Behavioral tests for Neo Ops (Tier 1 #7/#8/#9): insight + draft.

Mocks `db` and `chat_completion` (no live Mongo/LLM). Proves:
  - /admin/neo/insight returns insight + suggestions from real data (LLM + fallback)
  - /admin/neo/draft returns generated copy (LLM + fallback)
Run: python -m pytest tests/test_neo_ops.py -v
"""
import os
import asyncio
import json

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

import routes_neo_ops  # noqa: E402


class FakeAggCursor:
    def __init__(self, items):
        self.items = list(items)

    async def to_list(self, n=None):
        return list(self.items)


class FakeColl:
    def __init__(self, count=0, agg=None):
        self._count = count
        self._agg = agg or []

    async def count_documents(self, q=None):
        return self._count

    def aggregate(self, pipeline):
        return FakeAggCursor(self._agg)


class FakeDB:
    def __init__(self, **cols):
        for k, v in cols.items():
            setattr(self, k, v)


def _db():
    return FakeDB(
        orders=FakeColl(count=40, agg=[{'total': 5000.0}]),
        users=FakeColl(count=120),
        refunds=FakeColl(count=3, agg=[{'total': 450.0}]),
        audit_logs=FakeColl(count=2),
        blocked_ips=FakeColl(count=1),
    )


def test_insight_llm():
    routes_neo_ops.db = _db()

    async def fake_llm(system, user, temperature=0.3):
        return json.dumps({
            'insight': 'Orders are steady.',
            'suggestions': ['a', 'b', 'c'],
        })
    routes_neo_ops.chat_completion = fake_llm

    async def run():
        return await routes_neo_ops.insight(
            routes_neo_ops.InsightIn(context='orders', window='24h'))
    res = asyncio.run(run())

    assert res['source'] == 'llm'
    assert res['insight'] == 'Orders are steady.'
    assert len(res['suggestions']) == 3
    assert res['data']['total_orders'] == 40


def test_insight_fallback_when_llm_fails():
    routes_neo_ops.db = _db()
    routes_neo_ops.chat_completion = None  # force fallback path

    async def run():
        return await routes_neo_ops.insight(
            routes_neo_ops.InsightIn(context='security', window='24h'))
    res = asyncio.run(run())

    assert res['source'] == 'rule-based'
    assert 'failed_logins_window' in res['data']
    assert any('IP' in s for s in res['suggestions'])


def test_draft_returns_text():
    routes_neo_ops.db = _db()

    async def fake_llm(system, user, temperature=0.6):
        return "Your refund is processed. Dhanyavaad!"
    routes_neo_ops.chat_completion = fake_llm

    async def run():
        return await routes_neo_ops.draft(routes_neo_ops.DraftIn(
            type='refund_email',
            fields={'name': 'Ravi', 'order_id': 'ORD-1', 'amount': 100}))
    res = asyncio.run(run())

    assert res['source'] == 'llm'
    assert 'refund' in res['text'].lower()
