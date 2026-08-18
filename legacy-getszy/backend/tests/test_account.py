import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

from fastapi import HTTPException


class FakeColl:
    def __init__(self): self.docs = []
    async def find_one(self, flt, projection=None):
        for d in self.docs:
            if all(d.get(k) == v for k, v in flt.items()):
                return d
        return None
    async def update_one(self, flt, update):
        for d in self.docs:
            if all(d.get(k) == v for k, v in flt.items()):
                for k, v in update.get('$set', {}).items():
                    d[k] = v
                return
    def find(self, flt=None, projection=None):
        return []


class FakeDB:
    def __init__(self): self.users = FakeColl()


@pytest.fixture
def patch_account(monkeypatch):
    import routes_auth
    fdb = FakeDB()
    user = {'id': 'u1', 'name': 'Old Name', 'email': 'u@getszy.com', 'password_hash': 'oldhash', 'phone': None}
    monkeypatch.setattr(routes_auth, 'db', fdb)
    monkeypatch.setattr(routes_auth, 'get_current_user', lambda: user)
    async def fake_me(u):
        return {'name': u.get('name'), 'email': u.get('email')}
    monkeypatch.setattr(routes_auth, 'me', fake_me)
    return fdb, user


@pytest.mark.asyncio
async def test_update_me(patch_account):
    import routes_auth
    from models import ProfileUpdate
    fdb, user = patch_account
    fdb.users.docs.append(dict(user))
    out = await routes_auth.update_me(ProfileUpdate(name='New Name', phone='123'), user=user)
    assert out['name'] == 'New Name'
    assert fdb.users.docs[0]['name'] == 'New Name'
    assert fdb.users.docs[0]['phone'] == '123'


@pytest.mark.asyncio
async def test_change_password_ok(patch_account, monkeypatch):
    import routes_auth
    from models import PasswordChange
    fdb, user = patch_account
    fdb.users.docs.append(dict(user))
    monkeypatch.setattr(routes_auth, 'verify_password', lambda cur, hashed: cur == 'oldpass')
    monkeypatch.setattr(routes_auth, 'hash_password', lambda p: 'hashed_' + p)
    out = await routes_auth.change_password(
        PasswordChange(current_password='oldpass', new_password='Newpass1'), user=user)
    assert out == {'ok': True}
    assert fdb.users.docs[0]['password_hash'] == 'hashed_Newpass1'


@pytest.mark.asyncio
async def test_change_password_wrong_current(patch_account, monkeypatch):
    import routes_auth
    from models import PasswordChange
    fdb, user = patch_account
    fdb.users.docs.append(dict(user))
    monkeypatch.setattr(routes_auth, 'verify_password', lambda cur, hashed: False)
    monkeypatch.setattr(routes_auth, 'hash_password', lambda p: p)
    with pytest.raises(HTTPException) as exc:
        await routes_auth.change_password(
            PasswordChange(current_password='x', new_password='Newpass1'), user=user)
    assert exc.value.status_code == 400
