"""Behavioral tests for Tier 2 #11 automation engine + routes.

Covers the pure logic (conditions/rule matching) and an end-to-end
run of a 'notify' action against an in-memory fake DB (no Mongo needed).
Run: python -m pytest tests/test_automations.py -v
"""
import os
import asyncio

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

import automation_engine  # noqa: E402
import routes_automations  # noqa: E402


# ── Fake DB / manager ─────────────────────────────────────────────────────────
class FakeCursor:
    def __init__(self, items):
        self._items = items

    def sort(self, *a, **k):
        return self

    def __aiter__(self):
        async def gen():
            for i in self._items:
                yield i
        return gen()


class FakeColl:
    def __init__(self):
        self.inserted = []
        self.rules = []

    def find(self, q, projection=None):
        if 'trigger' in q:
            trig = q.get('trigger')
            return FakeCursor([r for r in self.rules if r.get('enabled') and r.get('trigger') == trig])
        if q.get('role') == 'admin':
            return FakeCursor([{'id': 'admin1'}, {'id': 'admin2'}])
        return FakeCursor([])

    async def insert_one(self, doc):
        self.inserted.append(doc)
        return None

    async def update_one(self, *a, **k):
        return None

    async def delete_one(self, *a, **k):
        return None


class FakeDB:
    def __init__(self):
        self.automations = FakeColl()
        self.users = FakeColl()
        self.notifications = FakeColl()
        self.automation_logs = FakeColl()
        self.automation_tags = FakeColl()


class FakeManager:
    def __init__(self):
        self.sent = []

    def send_to_user(self, uid, msg):
        self.sent.append((uid, msg))


# ── Pure logic ────────────────────────────────────────────────────────────────
def test_evaluate_condition_numeric_and_string():
    assert automation_engine.evaluate_condition({'field': 'total', 'op': '>', 'value': 5000}, {'total': 9000}) is True
    assert automation_engine.evaluate_condition({'field': 'total', 'op': '>', 'value': 5000}, {'total': 100}) is False
    assert automation_engine.evaluate_condition({'field': 'email', 'op': 'contains', 'value': '@'}, {'email': 'a@b.com'}) is True
    assert automation_engine.evaluate_condition({'field': 'name', 'op': '==', 'value': 'neo'}, {'name': 'neo'}) is True


def test_match_rule_trigger_and_conditions():
    rule = {
        'enabled': True,
        'trigger': 'order_created',
        'match': 'all',
        'conditions': [{'field': 'total', 'op': '>', 'value': 5000}],
        'actions': [],
    }
    assert automation_engine.match_rule(rule, 'order_created', {'total': 9000}) is True
    assert automation_engine.match_rule(rule, 'order_created', {'total': 100}) is False
    assert automation_engine.match_rule(rule, 'refund_issued', {'total': 9000}) is False
    assert automation_engine.match_rule({**rule, 'enabled': False}, 'order_created', {'total': 9000}) is False


# ── End-to-end run ──────────────────────────────────────────────────────────────
def test_run_automations_notify_action():
    fake = FakeDB()
    rule = {
        'id': 'r1',
        'name': 'Big order alert',
        'enabled': True,
        'trigger': 'order_created',
        'conditions': [{'field': 'total', 'op': '>', 'value': 5000}],
        'actions': [{'type': 'notify', 'title': 'Big order!', 'message': 'High value', 'type_notif': 'warn'}],
    }
    fake.automations.rules = [rule]

    automation_engine.db = fake
    import websocket_manager
    mgr = FakeManager()
    websocket_manager.manager = mgr

    results = asyncio.run(automation_engine.run_automations('order_created', {'total': 9999, 'order_number': 'ORD-1'}))

    assert len(results) == 1
    assert results[0]['rule_id'] == 'r1'
    # 2 admins notified
    assert len(fake.notifications.inserted) == 2
    assert fake.notifications.inserted[0]['title'] == 'Big order!'
    assert len(mgr.sent) == 2
    # automation run logged
    assert len(fake.automation_logs.inserted) == 1


def test_routes_automations_triggers_endpoint():
    # import side-effect proves module loads; triggers endpoint returns list
    data = routes_automations.AVAILABLE_TRIGGERS
    assert 'order_created' in data and 'refund_issued' in data
