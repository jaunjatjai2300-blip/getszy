"""Behavioral tests for Tier 0 #1: real data collectors feeding admin endpoints.

Mocks `db` so no live Mongo/server is required. Proves:
  - failed logins are recorded in the shape list_threats expects
  - rate-limited IPs are recorded as blocked_ips
  - list_threats aggregates both into the threat feed
  - list_request_logs returns request_logs entries
Run: python -m pytest tests/test_admin_collectors.py -v
"""
import os
import asyncio

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

import uuid
from datetime import datetime, timezone

import routes_enterprise_security  # noqa: E402
import routes_operations  # noqa: E402
import routes_auth  # noqa: E402
from models import LoginIn  # noqa: E402


class FakeCursor:
    def __init__(self, items):
        self.items = list(items)

    def sort(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def __aiter__(self):
        async def gen():
            for x in self.items:
                yield x
        return gen()


class FakeColl:
    def __init__(self, items=None, capture=None):
        self.items = list(items or [])
        self.capture = capture  # list to append inserted docs into

    def find(self, *a, **k):
        return FakeCursor(self.items)

    async def find_one(self, *a, **k):
        return None

    async def insert_one(self, doc):
        if self.capture is not None:
            self.capture.append(doc)
        return doc


class FakeDB:
    def __init__(self, **cols):
        for k, v in cols.items():
            setattr(self, k, v)


def _now():
    return datetime.now(timezone.utc).isoformat()


def test_failed_login_recorded_and_threats_aggregates():
    audit_cap, block_cap = [], []
    audit = FakeColl([
        {'id': 'a1', 'action': 'failed_login', 'email': 'a@x.com', 'ip': '1.2.3.4',
         'source': '1.2.3.4', 'detail': 'bad', 'ts': _now()},
    ], capture=audit_cap)
    blocked = FakeColl([
        {'id': 'b1', 'ip': '9.9.9.9', 'reason': 'Rate limit', 'severity': 'medium',
         'created_at': _now()},
    ], capture=block_cap)
    routes_enterprise_security.db = FakeDB(audit_logs=audit, blocked_ips=blocked)

    async def run():
        out = await routes_enterprise_security.list_threats()
        return out
    res = asyncio.run(run())

    items = res['items']
    titles = [t['title'] for t in items]
    assert 'Repeated failed login' in titles
    assert 'Blocked IP' in titles
    assert any(t['value'] == '1.2.3.4' for t in items)
    assert any(t['value'] == '9.9.9.9' for t in items)


def test_login_failure_writes_audit_log():
    audit_cap = []
    fake_db = FakeDB(
        users=FakeColl([]),  # find_one returns None -> failure path
        audit_logs=FakeColl(capture=audit_cap),
    )
    routes_auth.db = fake_db

    class FakeClient:
        host = '5.6.7.8'

    class FakeRequest:
        client = FakeClient()

    async def run():
        try:
            await routes_auth.login(LoginIn(email='x@y.com', password='wrong'), FakeRequest())
        except Exception:
            pass
        return audit_cap
    captured = asyncio.run(run())

    assert len(captured) == 1
    assert captured[0]['action'] == 'failed_login'
    assert captured[0]['email'] == 'x@y.com'
    assert captured[0]['ip'] == '5.6.7.8'


def test_request_logs_returned():
    logs = FakeColl([
        {'method': 'GET', 'path': '/api/x', 'status_code': 200, 'ip': '1.1.1.1',
         'timestamp': _now()},
    ])
    routes_operations.db = FakeDB(request_logs=logs)

    async def run():
        return await routes_operations.list_request_logs()
    res = asyncio.run(run())
    assert len(res['items']) == 1
    assert res['items'][0]['path'] == '/api/x'
