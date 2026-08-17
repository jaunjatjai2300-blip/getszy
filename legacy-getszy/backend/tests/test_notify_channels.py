"""Behavioral tests for Tier 3 multi-channel dispatch (email + WhatsApp).

SMTP and HTTP are mocked; logic + config-driven channel selection verified.
Run: python -m pytest tests/test_notify_channels.py -v
"""
import os
import asyncio

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

import notify_channels  # noqa: E402


class FakeSMTP:
    def __init__(self, *a, **k):
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, *a, **k):
        pass

    def send_message(self, msg):
        self.sent.append(msg)


class FakeResp:
    def __init__(self):
        self.status = 200

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeColl:
    def __init__(self, data=None):
        self._data = data

    async def find_one(self, q, p=None):
        return self._data


class FakeDB:
    def __init__(self, cfg):
        self.notification_config = FakeColl(cfg)


def test_dispatch_email_sent_when_configured(monkeypatch):
    notify_channels.db = FakeDB({'email_enabled': True, 'smtp_host': 'smtp.test', 'smtp_user': 'u', 'smtp_pass': 'p'})
    smtp = FakeSMTP()
    monkeypatch.setattr(notify_channels.smtplib, 'SMTP_SSL', lambda *a, **k: smtp)
    res = asyncio.run(notify_channels.dispatch('Hi', 'Body', emails=['a@b.com']))
    assert res['email'] == 'sent'
    assert len(smtp.sent) == 1


def test_dispatch_whatsapp_sent_when_configured(monkeypatch):
    notify_channels.db = FakeDB({'whatsapp_enabled': True, 'whatsapp_api_url': 'https://wa.test', 'whatsapp_token': 't'})
    called = {}
    import urllib.request

    def fake_urlopen(req, timeout=8):
        called['url'] = req.full_url
        called['data'] = req.data
        return FakeResp()

    monkeypatch.setattr(notify_channels.urllib.request, 'urlopen', fake_urlopen)
    res = asyncio.run(notify_channels.dispatch('Hi', 'Body', phones=['919999999999']))
    assert res['whatsapp'] == 'sent'
    assert called.get('url') == 'https://wa.test'


def test_dispatch_not_configured_returns_skipped():
    notify_channels.db = FakeDB({})
    res = asyncio.run(notify_channels.dispatch('Hi', 'Body', emails=['a@b.com'], phones=['919999999999']))
    assert res['email'] == 'not_configured'
    assert res['whatsapp'] == 'not_configured'
