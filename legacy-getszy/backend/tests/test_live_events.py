"""Behavioral tests for Tier 2 #10 live ops: event broadcaster + WS endpoint.

Mocks the WS manager (no live socket). Proves:
  - broadcast_admin_event pushes to the 'admin-live' channel
  - routes_ws now imports cleanly and exposes /ws/admin-live (bug fix)
Run: python -m pytest tests/test_live_events.py -v
"""
import os
import asyncio

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

import live_events  # noqa: E402
import routes_ws  # noqa: E402


class FakeManager:
    def __init__(self):
        self.sent = []

    def broadcast(self, channel, message):
        self.sent.append((channel, message))

    def connect(self, *a, **k):
        pass

    def disconnect(self, *a, **k):
        pass


def test_broadcast_admin_event_channels_admin_live():
    fm = FakeManager()
    live_events.manager = fm

    live_events.broadcast_admin_event('order_created', {'order_number': 'ORD-9'})

    assert len(fm.sent) == 1
    channel, msg = fm.sent[0]
    assert channel == 'admin-live'
    assert msg['type'] == 'order_created'
    assert msg['payload']['order_number'] == 'ORD-9'
    assert 'ts' in msg


def test_ws_admin_live_route_registered():
    paths = [(getattr(r, 'path', ''), getattr(r, 'endpoint', None)) for r in routes_ws.router.routes]
    assert any('admin-live' in p for p, _ in paths)
