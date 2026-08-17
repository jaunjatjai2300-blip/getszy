import os, sys, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

from models import SignupIn


class FakeCursor:
    def __init__(self, items): self.items = items
    def sort(self, *a, **k): return self
    def __aiter__(self):
        async def gen():
            for i in self.items: yield i
        return gen()


class FakeColl:
    def __init__(self): self.docs = []
    async def find_one(self, flt, projection=None):
        for d in self.docs:
            if all(d.get(k) == v for k, v in flt.items()):
                return d
        return None
    async def insert_one(self, doc): self.docs.append(doc)
    async def update_one(self, flt, update):
        for d in self.docs:
            if all(d.get(k) == v for k, v in flt.items()):
                for k, v in update.get('$inc', {}).items():
                    d[k] = d.get(k, 0) + v
                for k, v in update.get('$set', {}).items():
                    d[k] = v
                return
    def find(self, flt=None, projection=None):
        flt = flt or {}
        items = [d for d in self.docs if all(d.get(k) == v for k, v in flt.items())]
        return FakeCursor(items)


class FakeDB:
    def __init__(self):
        self.users = FakeColl()
        self.referrals = FakeColl()


@pytest.fixture
def patch_db(monkeypatch):
    import routes_auth
    fdb = FakeDB()
    monkeypatch.setattr(routes_auth, 'db', fdb)
    return fdb


@pytest.mark.asyncio
async def test_signup_credits_referrer(patch_db):
    import routes_auth
    from models import User
    # Seed a referrer
    referrer = User(name='Ref Person', email='ref@getszy.com', password_hash='x', referral_code='GSREFER')
    await patch_db.users.insert_one(referrer.model_dump())

    res = await routes_auth.signup(SignupIn(
        name='New User', email='new@getszy.com', password='Passw0rd!', ref='gsrefer'
    ))
    assert res['user']['referral_code']
    # Referrer credited
    ref = await patch_db.users.find_one({'email': 'ref@getszy.com'})
    assert ref['credits'] == 50
    assert ref['referral_rewards'] == 50
    # Referral record stored
    assert len(patch_db.referrals.docs) == 1
    rec = patch_db.referrals.docs[0]
    assert rec['referrer_id'] == referrer.id
    assert rec['reward_credits'] == 50
    assert rec['status'] == 'credited'


@pytest.mark.asyncio
async def test_my_referrals_endpoint(patch_db):
    import routes_auth
    from models import User
    referrer = User(name='Ref Person', email='ref@getszy.com', password_hash='x', referral_code='GSREFER', referral_rewards=50)
    await patch_db.users.insert_one(referrer.model_dump())
    await routes_auth.signup(SignupIn(name='New User', email='new@getszy.com', password='Passw0rd!', ref='GSREFER'))

    out = await routes_auth.my_referrals(user={'id': referrer.id, 'name': 'Ref Person', 'referral_code': 'GSREFER', 'referral_rewards': 50})
    assert out['referral_code'] == 'GSREFER'
    assert out['referral_link'].endswith('?ref=GSREFER')
    assert out['total_referred'] == 1
    assert out['rewards_earned'] == 50
    assert len(out['referred']) == 1
    assert out['referred'][0]['name'] == 'New User'
