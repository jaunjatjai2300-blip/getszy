import os, sys, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests-32chars-minimum!!')


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE — atomic credit deduction under concurrent requests
# (User's exact question: can Request A + Request B simultaneously corrupt balance?)
# ─────────────────────────────────────────────────────────────────────────────

class _AtomicFakeDB:
    """Models MongoDB's atomic find_one_and_update: a single op checks the
    `credits >= cost` filter and applies $inc — no interleaved read/modify/write."""
    def __init__(self, credits):
        self._credits = credits
        self.users = self
        self.credit_transactions = self

    async def find_one(self, flt, projection=None):
        return {'id': 'u1', 'role': 'customer', 'credits': self._credits}

    async def find_one_and_update(self, flt, update, return_document=None, projection=None):
        gte = (flt.get('credits') or {}).get('$gte')
        if gte is not None and self._credits < gte:
            return None  # precondition failed -> no mutation (real DB behaviour)
        if '$inc' in update:
            self._credits += update['$inc'].get('credits', 0)
        return {'credits': self._credits}

    async def insert_one(self, doc):
        return None


@pytest.mark.asyncio
async def test_deduct_atomic_under_concurrency(monkeypatch):
    import credits
    db = _AtomicFakeDB(credits=100)
    monkeypatch.setattr(credits, 'db', db)
    # Two requests arrive "simultaneously" for a 2-credit action each.
    r1, r2 = await asyncio.gather(
        credits.deduct('u1', 'image'),   # cost 2
        credits.deduct('u1', 'image'),   # cost 2
    )
    # Balance must be exactly 96, never negative, never double-counted.
    assert db._credits == 96
    assert all(ok for ok, _, _ in (r1, r2))


@pytest.mark.asyncio
async def test_deduct_never_goes_negative(monkeypatch):
    import credits
    db = _AtomicFakeDB(credits=3)
    monkeypatch.setattr(credits, 'db', db)
    ok, msg, _ = await credits.deduct('u1', 'image')  # cost 2 -> ok, bal 1
    assert ok is True
    ok2, _, _ = await credits.deduct('u1', 'image')    # cost 2 -> bal would be -1 -> rejected
    assert ok2 is False
    assert db._credits == 1


# ─────────────────────────────────────────────────────────────────────────────
# SECURITY (residual fixes) — SSRF URL validator + per-user AI rate limiter
# ─────────────────────────────────────────────────────────────────────────────

def test_is_safe_url_blocks_private_and_loopback():
    import routes_growth as g
    assert g.is_safe_url('http://127.0.0.1/admin') is False
    assert g.is_safe_url('http://localhost') is False
    assert g.is_safe_url('http://169.254.169.254/latest') is False
    assert g.is_safe_url('http://10.0.0.5') is False
    assert g.is_safe_url('ftp://example.com') is False
    assert g.is_safe_url('https://8.8.8.8') is True  # public IP, no DNS needed


def test_ai_rate_limiter_enforces_per_user_cap():
    import asyncio
    import time
    from middleware import ai_rate_limit_allowed
    key = f'testuser_{time.time()}'

    async def _run():
        for _ in range(30):
            assert await ai_rate_limit_allowed(key, limit=30, window=60) is True
        assert await ai_rate_limit_allowed(key, limit=30, window=60) is False

    asyncio.run(_run())
