"""Behavioral tests for Tier 2 #13 anomaly detection + auto-block.

Uses an in-memory fake DB (no Mongo). Covers:
  - auto-block triggers after FAILED_LOGIN_THRESHOLD recent failures
  - get_anomalies aggregates failed-login + error + blocked data
Run: python -m pytest tests/test_anomaly.py -v
"""
import os
import asyncio

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

import anomaly  # noqa: E402


class FakeCursor:
    def __init__(self, items):
        self._items = items

    def sort(self, *a, **k):
        return self

    def limit(self, n):
        return self

    def __aiter__(self):
        async def gen():
            for i in self._items:
                yield i
        return gen()


class FakeColl:
    def __init__(self, items=None, find_one=None, agg=None):
        self.items = items or []
        self._find_one = find_one
        self._agg = agg or []
        self.inserted = []

    def find(self, q, p=None):
        return FakeCursor(self.items)

    async def find_one(self, q, p=None):
        return self._find_one

    async def insert_one(self, doc):
        self.inserted.append(doc)
        return None

    def aggregate(self, pipeline):
        return FakeCursor(self._agg)


class FakeDB:
    def __init__(self, audit_items=None, audit_agg=None, err_agg=None, blocked=None, users=None):
        self.audit_logs = FakeColl(items=audit_items or [], agg=audit_agg or [])
        self.request_logs = FakeColl(agg=err_agg or [])
        self.blocked_ips = FakeColl(items=blocked or [], find_one=None)
        self.users = FakeColl(items=users or [{'id': 'admin1'}])
        self.notifications = FakeColl()


class FakeManager:
    def __init__(self):
        self.sent = []

    def send_to_user(self, uid, msg):
        self.sent.append((uid, msg))


def test_record_login_failure_auto_blocks_after_threshold(monkeypatch):
    recent = [{'ip': '1.2.3.4', 'email': 'a@b.com', 'ts': '2024-01-01T00:00:00+00:00'} for _ in range(5)]
    db = FakeDB(audit_items=recent, users=[{'id': 'admin1'}])
    anomaly.db = db
    import websocket_manager
    mgr = FakeManager()
    websocket_manager.manager = mgr
    import live_events
    monkeypatch.setattr(live_events, 'broadcast_admin_event', lambda *a, **k: None)

    blocked = asyncio.run(anomaly.record_login_failure('1.2.3.4', 'a@b.com'))

    assert blocked is True
    assert len(db.blocked_ips.inserted) == 1
    assert db.blocked_ips.inserted[0]['ip'] == '1.2.3.4'
    # admin notified
    assert len(db.audit_logs.inserted) == 0  # audit already counted in find
    assert len(mgr.sent) == 1


def test_record_login_failure_no_block_below_threshold(monkeypatch):
    recent = [{'ip': '1.2.3.4', 'email': 'a@b.com', 'ts': '2024-01-01T00:00:00+00:00'} for _ in range(2)]
    db = FakeDB(audit_items=recent)
    anomaly.db = db
    import websocket_manager
    websocket_manager.manager = FakeManager()
    import live_events
    monkeypatch.setattr(live_events, 'broadcast_admin_event', lambda *a, **k: None)

    blocked = asyncio.run(anomaly.record_login_failure('1.2.3.4', 'a@b.com'))
    assert blocked is False
    assert len(db.blocked_ips.inserted) == 0


def test_get_anomalies_aggregates():
    db = FakeDB(
        audit_agg=[{'_id': '1.2.3.4', 'count': 7, 'emails': ['a@b.com']}],
        err_agg=[{'_id': '9.9.9.9', 'errors': 3}],
        blocked=[{'ip': '1.2.3.4', 'reason': 'brute force'}],
    )
    anomaly.db = db
    res = asyncio.run(anomaly.get_anomalies(24))
    assert res['ip_risk'][0]['_id'] == '1.2.3.4'
    assert res['request_errors'][0]['errors'] == 3
    assert res['blocked_ips'][0]['ip'] == '1.2.3.4'
    assert res['window'] == '24h'
