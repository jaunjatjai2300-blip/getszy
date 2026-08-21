"""Regression tests for the Phase-4 production hardening fixes.

Every P0/P1 finding from GETSZY_CTO_AUDIT_PHASE4_FIVE_AREAS.md has at least
one test here. Tests use the same in-memory fake-Mongo pattern established
in test_credit_subscription.py so they are VPS-independent and reproducible
in CI/audit environments.
"""
import os
import sys
import types

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests-32chars-minimum!!')

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import credits as credits_mod


# ═══════════════════════════════════════════════════════════════════════════════
# 1. NEW SKU REGISTRATION (P0-1..P0-4, P1-1)
# ═══════════════════════════════════════════════════════════════════════════════

def test_new_credit_skus_registered():
    """Every uncredited endpoint identified in the audit now has a SKU."""
    required = [
        'saas_blueprint',       # P0-1
        'custom_agent_run',     # P0-2
        'starter_kit',          # P0-3
        'platform_thumbnail',   # P0-4
        'platform_script',      # P0-4
        'platform_scenes',      # P0-4
        'channel_plan',         # P1-1
    ]
    for sku in required:
        assert sku in credits_mod.CREDIT_COSTS, f"SKU {sku!r} missing from CREDIT_COSTS"
        assert credits_mod.CREDIT_COSTS[sku] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 2. REFUND IDEMPOTENCY (P1-3) — the ref_id guard now actually fires
# ═══════════════════════════════════════════════════════════════════════════════

class _RaisingCollection:
    """Simulates the unique-index DuplicateKeyError on the second insert."""

    def __init__(self):
        self._seen: set = set()
        self._rows: list = []

    async def insert_one(self, doc):
        key = (doc.get('user_id'), doc.get('ref_id'), doc.get('type'))
        if doc.get('ref_id') and key in self._seen:
            from pymongo.errors import DuplicateKeyError
            raise DuplicateKeyError('duplicate ref_id')
        if doc.get('ref_id'):
            self._seen.add(key)
        self._rows.append(doc)
        return types.SimpleNamespace(inserted_id=f'x{len(self._rows)}')

    async def update_one(self, flt, upd):
        return types.SimpleNamespace(modified_count=1)


class _UserCollection:
    def __init__(self, credits=100):
        self._doc = {'id': 'u1', 'credits': credits, 'role': 'customer'}

    async def find_one(self, flt, projection=None):
        return dict(self._doc)

    async def find_one_and_update(self, flt, update, return_document=False, projection=None):
        # Apply $inc
        for k, v in update.get('$inc', {}).items():
            self._doc[k] = self._doc.get(k, 0) + v
        return dict(self._doc)


class _FakeDB:
    def __init__(self):
        self.users = _UserCollection()
        self.credit_transactions = _RaisingCollection()


@pytest.fixture
def fake_db(monkeypatch):
    db = _FakeDB()
    monkeypatch.setattr(credits_mod, 'db', db)
    return db


@pytest.mark.asyncio
async def test_refund_with_ref_id_is_idempotent(fake_db):
    """Second refund with the same ref_id is a no-op — no double credit."""
    ref = 'test-ref-abc123'
    bal1 = await credits_mod.refund('u1', 'script', ref_id=ref)
    bal2 = await credits_mod.refund('u1', 'script', ref_id=ref)  # replay
    assert bal1 == bal2  # balance unchanged on replay
    # Only one refund row survived the DuplicateKeyError.
    refunds = [r for r in fake_db.credit_transactions._rows if r['type'] == 'refund']
    assert len(refunds) == 1


@pytest.mark.asyncio
async def test_refund_without_ref_id_still_works_for_backward_compat(fake_db):
    """Legacy callers (if any) that don't pass ref_id are not broken."""
    bal = await credits_mod.refund('u1', 'script', reason='legacy_call')
    assert bal is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 3. INTEGRATIONS COMING-SOON GATE (P0-7)
# ═══════════════════════════════════════════════════════════════════════════════

def test_no_integration_is_available_by_default():
    """Beta ships with zero integrations enabled."""
    import routes_integrations as ri
    assert ri.AVAILABLE_INTEGRATIONS == set(), (
        'AVAILABLE_INTEGRATIONS must be empty for the beta; add ids explicitly '
        'once each has real OAuth + encrypted credential storage.'
    )
    # Every catalog entry should map to _is_available() -> False right now.
    for integ in ri.INTEGRATIONS:
        assert ri._is_available(integ['id']) is False


@pytest.mark.asyncio
async def test_connect_endpoint_rejects_unavailable_integration(monkeypatch):
    """The API must refuse to store credentials for unavailable integrations —
    even if the frontend is bypassed with curl."""
    import routes_integrations as ri

    # Fake db.integration_waitlist so the waitlist upsert doesn't blow up.
    class _Coll:
        rows = []
        async def update_one(self, flt, upd, upsert=False):
            _Coll.rows.append((flt, upd))
            return types.SimpleNamespace(modified_count=1)

    class _FakeDB:
        integration_waitlist = _Coll()

    monkeypatch.setattr(ri, 'db', _FakeDB())

    from fastapi import HTTPException
    payload = ri.ConnectIn(integration_id='gmail', credentials={'api_key': 'ATTACKER'})
    user = {'id': 'u1', 'email': 'u1@example.com'}
    with pytest.raises(HTTPException) as exc_info:
        await ri.connect_integration(payload, user=user)
    assert exc_info.value.status_code == 503
    assert 'coming soon' in exc_info.value.detail.lower()
    # Waitlist entry created, but NO credentials were persisted anywhere.
    assert len(_Coll.rows) == 1
    for _flt, upd in _Coll.rows:
        set_doc = upd.get('$set', {})
        assert 'credentials' not in set_doc
        assert 'api_key' not in str(set_doc)
        assert 'ATTACKER' not in str(set_doc)


@pytest.mark.asyncio
async def test_waitlist_endpoint_stores_no_credentials(monkeypatch):
    import routes_integrations as ri

    class _Coll:
        rows = []
        async def update_one(self, flt, upd, upsert=False):
            _Coll.rows.append((flt, upd))
            return types.SimpleNamespace(modified_count=1)

    class _FakeDB:
        integration_waitlist = _Coll()

    monkeypatch.setattr(ri, 'db', _FakeDB())
    payload = ri.WaitlistIn(integration_id='slack')
    user = {'id': 'u1'}
    result = await ri.integration_waitlist(payload, user=user)
    assert result['ok'] is True
    assert result['waitlisted'] is True
    for _flt, upd in _Coll.rows:
        assert 'credentials' not in upd.get('$set', {})


# ═══════════════════════════════════════════════════════════════════════════════
# 4. MOCK ENDPOINTS RETURN 501 (P0-5, P0-6)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_reels_render_returns_501(monkeypatch):
    """/creator/platform/reels/{id}/render must no longer fake success."""
    import routes_creator_platform as rcp

    class _Coll:
        async def find_one(self, flt):
            return {'id': flt['id'], 'user_id': flt['user_id'], 'script': 'hi'}

    class _FakeDB:
        creator_reels = _Coll()

    monkeypatch.setattr(rcp, 'db', _FakeDB())
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await rcp.render_reel(reel_id='r1', user={'id': 'u1'})
    assert exc_info.value.status_code == 501


@pytest.mark.asyncio
async def test_batch_render_returns_501():
    import routes_creator_platform as rcp
    from fastapi import HTTPException
    payload = rcp.BatchRenderIn(items=[{'x': 1}], template='default')
    with pytest.raises(HTTPException) as exc_info:
        await rcp.batch_render(payload, user={'id': 'u1'})
    assert exc_info.value.status_code == 501


@pytest.mark.asyncio
async def test_workflow_execute_returns_501(monkeypatch):
    import routes_build_studio as rbs

    class _Coll:
        async def find_one(self, flt):
            return {'id': flt['id'], 'user_id': flt['user_id'], 'nodes': [1, 2, 3]}

    class _FakeDB:
        build_projects = _Coll()

    monkeypatch.setattr(rbs, 'db', _FakeDB())
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await rbs.execute_workflow(workflow_id='w1', user={'id': 'u1'})
    assert exc_info.value.status_code == 501


@pytest.mark.asyncio
async def test_marketplace_install_returns_501():
    import routes_build_studio as rbs
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await rbs.install_template(template_id='saas-starter', user={'id': 'u1'})
    assert exc_info.value.status_code == 501


# ═══════════════════════════════════════════════════════════════════════════════
# 5. INSUFFICIENT BALANCE RETURNS 402 (P0-1..P0-4)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_saas_create_requires_credits(monkeypatch):
    """P0-1: /saas/create must reject a zero-balance customer before any LLM call."""
    import routes_build_studio as rbs

    class _Users:
        async def find_one(self, flt, projection=None):
            return {'id': 'u1', 'role': 'customer', 'credits': 0}

        async def find_one_and_update(self, *a, **k):
            return None  # deduct filter fails on zero balance

    class _Txn:
        async def insert_one(self, *a, **k):
            return types.SimpleNamespace(inserted_id='x')

    class _FakeDB:
        users = _Users()
        credit_transactions = _Txn()
        build_projects = _Txn()

    monkeypatch.setattr(credits_mod, 'db', _FakeDB())
    monkeypatch.setattr(rbs, 'db', _FakeDB())

    from fastapi import HTTPException
    payload = rbs.SaaSIn(name='X', description='Y')
    user = {'id': 'u1', 'role': 'customer'}
    with pytest.raises(HTTPException) as exc_info:
        await rbs.create_saas(payload, user=user)
    assert exc_info.value.status_code == 402
    assert 'credits' in exc_info.value.detail.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# 6. IDOR SANITY (Cross-user isolation)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_get_build_project_scopes_by_user(monkeypatch):
    """User B cannot fetch User A's build project even if they know its id."""
    import routes_build_studio as rbs

    stored = {'id': 'p1', 'user_id': 'userA', 'name': 'Secret'}

    class _Coll:
        async def find_one(self, flt, projection=None):
            # Enforce both filters — this is exactly what the real Mongo query does.
            if flt.get('id') == stored['id'] and flt.get('user_id') == stored['user_id']:
                return dict(stored)
            return None

    class _FakeDB:
        build_projects = _Coll()

    monkeypatch.setattr(rbs, 'db', _FakeDB())

    from fastapi import HTTPException
    # User B tries to read User A's project — must 404, not leak the doc.
    with pytest.raises(HTTPException) as exc_info:
        await rbs.get_build_project(project_id='p1', user={'id': 'userB'})
    assert exc_info.value.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# 7. CHANNEL/PLAN ENDPOINT HAS CREDIT GATE (P1-1)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_channel_plan_requires_credits(monkeypatch):
    import routes_builder as rb

    class _Users:
        async def find_one(self, flt, projection=None):
            return {'id': 'u1', 'role': 'customer', 'credits': 0}

        async def find_one_and_update(self, *a, **k):
            return None

    class _Txn:
        async def insert_one(self, *a, **k):
            return types.SimpleNamespace(inserted_id='x')

    class _FakeDB:
        users = _Users()
        credit_transactions = _Txn()
        channel_plans = _Txn()

    monkeypatch.setattr(credits_mod, 'db', _FakeDB())
    monkeypatch.setattr(rb, 'db', _FakeDB())

    from fastapi import HTTPException
    payload = rb.ChannelPlanIn(niche='cooking')
    with pytest.raises(HTTPException) as exc_info:
        await rb.channel_plan(payload, user={'id': 'u1', 'role': 'customer'})
    assert exc_info.value.status_code == 402
