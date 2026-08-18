import os, sys, jwt
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests-32chars-minimum!!')

from datetime import datetime, timezone, timedelta


# ─────────────────────────────────────────────────────────────────────────────
# AUTHENTICATION — JWT attacks
# ─────────────────────────────────────────────────────────────────────────────

def _make_creds(token: str):
    class Creds:
        credentials = token
    return Creds()


class _FakeDB:
    def __init__(self, role='admin'):
        self._role = role
        self.users = self
    async def find_one(self, *a, **k):
        return {'id': 'u1', 'role': self._role, 'name': 'T', 'email': 't@x.com'}


@pytest.mark.asyncio
async def test_jwt_forged_secret_rejected(monkeypatch):
    import auth
    monkeypatch.setattr(auth, 'db', _FakeDB())
    forged = jwt.encode({'sub': 'u1', 'role': 'admin', 'exp': datetime.now(timezone.utc) + timedelta(days=1)},
                        'a-different-secret', algorithm='HS256')
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await auth.get_current_user(_make_creds(forged))


@pytest.mark.asyncio
async def test_jwt_expired_rejected(monkeypatch):
    import auth
    monkeypatch.setattr(auth, 'db', _FakeDB())
    expired = jwt.encode({'sub': 'u1', 'exp': datetime.now(timezone.utc) - timedelta(days=1)},
                         auth.JWT_SECRET, algorithm='HS256')
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await auth.get_current_user(_make_creds(expired))


@pytest.mark.asyncio
async def test_jwt_alg_none_rejected(monkeypatch):
    import auth
    monkeypatch.setattr(auth, 'db', _FakeDB())
    none_token = jwt.encode({'sub': 'u1', 'role': 'admin'}, key='', algorithm='none')
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await auth.get_current_user(_make_creds(none_token))


@pytest.mark.asyncio
async def test_jwt_role_escalation_blocked_via_db(monkeypatch):
    import auth
    db = _FakeDB(role='customer')
    monkeypatch.setattr(auth, 'db', db)
    token = jwt.encode({'sub': 'u1', 'role': 'admin', 'exp': datetime.now(timezone.utc) + timedelta(days=1)},
                       auth.JWT_SECRET, algorithm='HS256')
    user = await auth.get_current_user(_make_creds(token))
    assert user['role'] == 'customer'  # DB wins, not token
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await auth.get_current_admin(user)


# ─────────────────────────────────────────────────────────────────────────────
# INPUT — NoSQL injection on login (email is typed str; operator objects rejected)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_nosql_injection_rejected(monkeypatch):
    import routes_auth
    class FakeColl:
        async def find_one(self, flt, proj=None):
            return None
    class FakeDB:
        users = FakeColl()
    monkeypatch.setattr(routes_auth, 'db', FakeDB())
    from pydantic import ValidationError
    from models import LoginIn
    with pytest.raises(ValidationError):
        LoginIn(email={'$gt': ''}, password='x')


# ─────────────────────────────────────────────────────────────────────────────
# INPUT — calculate tool cannot execute code (strict allowlist before eval)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_calculate_blocks_code_injection():
    from tools import execute_tool
    out = await execute_tool('calculate', {'expression': '__import__("os").system("echo pwned")'})
    assert 'unsupported characters' in out
    out2 = await execute_tool('calculate', {'expression': '1+1'})
    assert out2 == '2'


# ─────────────────────────────────────────────────────────────────────────────
# AUTHORIZATION — agent history scoped to the authenticated user (no IDOR)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_history_scoped_to_user(monkeypatch):
    import routes_agents
    captured = {}
    class FakeCur:
        def __init__(self, items): self.items = items
        def sort(self, *a, **k): return self
        def limit(self, n): return self
        def __aiter__(self):
            async def g():
                for i in self.items: yield i
            return g()
    class FakeDB:
        def __init__(self): self.agent_chats = self
        def find(self, q, proj=None):
            captured['q'] = q
            return FakeCur([])
    monkeypatch.setattr(routes_agents, 'db', FakeDB())
    await routes_agents.agent_history('business-advisor', user={'id': 'victim-123'})
    assert captured['q']['user_id'] == 'victim-123'


# ─────────────────────────────────────────────────────────────────────────────
# INPUT — path traversal on cached media serving is blocked
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_media_file_blocks_traversal():
    import routes_media
    from fastapi import HTTPException
    for bad in ('../secret', '/etc/passwd'):
        with pytest.raises(HTTPException):
            await routes_media.serve_cached(bad)


# ─────────────────────────────────────────────────────────────────────────────
# AI SECURITY — destructive intent cannot delete without a valid target
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_chat_delete_requires_target(monkeypatch):
    import ai_chat
    class ChatDB:
        deleted = False
        class products:
            @staticmethod
            async def find_one(*a, **k): return None
            @staticmethod
            async def delete_one(*a, **k):
                ChatDB.deleted = True
                return type('R', (), {'deleted_count': 1})()
        class categories:
            @staticmethod
            async def find_one(*a, **k): return None
    monkeypatch.setattr(ai_chat, 'db', ChatDB())
    # Model returns a delete with an empty target -> must be rejected, not executed
    result = await ai_chat.execute_intent({'intent': 'delete_product', 'params': {'product_query': ''}})
    assert result.get('ok') is False
    assert ChatDB.deleted is False


# ─────────────────────────────────────────────────────────────────────────────
# AI SECURITY — public builder preview must be CSP-sandboxed (no stored XSS)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_builder_preview_is_csp_sandboxed(monkeypatch):
    import routes_builder
    class FakeColl:
        async def find_one(self, *a, **k):
            return {'html_content': '<script>alert(1)</script><h1>hi</h1>'}
    class FakeDB:
        builder_projects = FakeColl()
    monkeypatch.setattr(routes_builder, 'db', FakeDB())
    resp = await routes_builder.preview_project('pid1')
    assert 'sandbox' in resp.headers.get('Content-Security-Policy', '')

