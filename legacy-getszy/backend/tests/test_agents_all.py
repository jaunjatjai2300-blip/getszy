import sys, os, types
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest

# In-memory fakes
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
    def __init__(self, items=None):
        self._items = items or []
    def find(self, *a, **k):
        return FakeCursor(self._items)

class FakeDB:
    def __init__(self):
        self.custom_agents = FakeColl([])

@pytest.fixture
def patch_db(monkeypatch):
    import routes_agents
    monkeypatch.setattr(routes_agents, 'db', FakeDB())
    yield

@pytest.mark.asyncio
async def test_all_agents_aggregates(patch_db):
    from routes_agents import all_agents
    res = await all_agents(user={'id': 'u1'})
    assert set(res.keys()) >= {'expert', 'workforce', 'vibecoders', 'custom', 'total'}
    # 7 expert + 10 workforce + 8 vibecoders (no custom for this user)
    assert len(res['expert']) == 7
    assert len(res['workforce']) == 10
    assert len(res['vibecoders']) == 8
    assert len(res['custom']) == 0
    assert res['total'] == 25
    assert all(a.get('type') == 'expert' for a in res['expert'])
    assert all(a.get('type') == 'workforce' for a in res['workforce'])
    assert all(a.get('type') == 'vibecoders' for a in res['vibecoders'])

@pytest.mark.asyncio
async def test_all_agents_includes_custom(patch_db):
    from routes_agents import all_agents, db
    db.custom_agents = FakeColl([
        {'id': 'c1', 'name': 'My Bot', 'role': 'helper', 'color': '#fff', 'icon': 'star', 'user_id': 'u1', 'created_at': 1}
    ])
    res = await all_agents(user={'id': 'u1'})
    assert len(res['custom']) == 1
    assert res['custom'][0]['id'] == 'c1'
    assert res['custom'][0]['type'] == 'custom'
    assert res['total'] == 26
