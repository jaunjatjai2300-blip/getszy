import os, sys, re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')


class FakeCursor:
    def __init__(self, items): self.items = items
    def sort(self, *a, **k): return self
    def __aiter__(self):
        async def gen():
            for i in self.items: yield i
        return gen()


class FakeColl:
    def __init__(self): self.docs = []; self.last_filter = None; self.last_regex = None; self.last_find = None
    async def find_one(self, flt, projection=None):
        self.last_filter = flt
        if isinstance(flt.get('name'), dict) and '$regex' in flt['name']:
            self.last_regex = flt['name']['$regex']
        for d in self.docs:
            if all(d.get(k) == v for k, v in flt.items() if k not in ('name',)):
                return d
        return None
    async def insert_one(self, doc): self.docs.append(doc)
    async def update_one(self, flt, update):
        for d in self.docs:
            if all(d.get(k) == v for k, v in flt.items()):
                for k, v in update.get('$set', {}).items():
                    d[k] = v
                return
    def find(self, flt=None, projection=None):
        self.last_find = flt
        flt = flt or {}
        return FakeCursor([d for d in self.docs if all(d.get(k) == v for k, v in flt.items() if k != 'name')])


class FakeDB:
    def __init__(self):
        self.products = FakeColl()
        self.categories = FakeColl()
        self.orders = FakeColl()
        self.suppliers = FakeColl()
        self.enrollments = FakeColl()


@pytest.fixture
def patch(monkeypatch):
    import ai_chat
    f = FakeDB()
    monkeypatch.setattr(ai_chat, 'db', f)
    return f


@pytest.mark.asyncio
async def test_update_product_query_is_escaped(patch):
    import ai_chat
    patch.products.docs.append({'id': 'p1', 'name': 'Real Product', 'price': 10})
    await ai_chat.execute_intent({'intent': 'update_product', 'params': {'product_query': '.*', 'updates': {'price': 99}}})
    regex_used = patch.products.last_regex
    assert regex_used == re.escape('.*')
    assert regex_used != '.*'  # raw metacharacters must NOT reach Mongo


@pytest.mark.asyncio
async def test_delete_product_query_is_escaped(patch):
    import ai_chat
    patch.products.docs.append({'id': 'p2', 'name': 'Delete Me'})
    await ai_chat.execute_intent({'intent': 'delete_product', 'params': {'product_query': '(test'}})
    regex_used = patch.products.last_regex
    assert regex_used == re.escape('(test')


@pytest.mark.asyncio
async def test_list_products_search_is_escaped(patch):
    import ai_chat
    await ai_chat.execute_intent({'intent': 'list_products', 'params': {'search': '.*$'}})
    name_filter = patch.products.last_find.get('name')
    assert name_filter['$regex'] == re.escape('.*$')
