"""Tests for catalog caching + Cache-Control headers (no live Mongo needed).

Patches the DB layer directly so it runs fast in CI and locally.
"""
import asyncio

import pytest


@pytest.fixture
def router():
    import routes_catalog
    return routes_catalog


class FakeCursor:
    def __init__(self, data):
        self.data = data

    def limit(self, n):
        return self

    def to_list(self, n):
        fut = asyncio.Future()
        fut.set_result(self.data[:n])
        return fut


def _future(value):
    fut = asyncio.Future()
    fut.set_result(value)
    return fut


def test_list_categories_cache_header(router, monkeypatch):
    cat = {'id': 'c1', 'name': 'Sarees', 'slug': 'sarees', 'is_active': True}

    def fake_find(self, q, *a, **k):
        if q == {}:
            return FakeCursor([cat])
        return FakeCursor([])

    monkeypatch.setattr(router.db.categories.__class__, 'find', fake_find)
    monkeypatch.setattr(router.db.products.__class__, 'count_documents', lambda *a, **k: _future(7))

    resp = asyncio.run(router.list_categories())
    assert resp.status_code == 200
    assert 'max-age=300' in resp.headers.get('Cache-Control', '')
    body = resp.body.decode()
    assert 'Sarees' in body
    assert '7' in body  # product_count


def test_list_products_cache_header(router, monkeypatch):
    product = {
        'id': 'p1', 'name': 'Test Saree', 'slug': 'test-saree',
        'price': 1999.0, 'category': 'sarees', 'is_active': True,
        'is_featured': True, 'is_digital': False, 'stock': 5,
    }

    def fake_find(self, q, *a, **k):
        return FakeCursor([product])

    monkeypatch.setattr(router.db.products.__class__, 'find', fake_find)

    resp = asyncio.run(router.list_products())
    assert resp.status_code == 200
    assert 'max-age=60' in resp.headers.get('Cache-Control', '')
    body = resp.body.decode()
    assert 'Test Saree' in body


def test_list_products_featured_filter(router, monkeypatch):
    featured = {'id': 'f1', 'name': 'Featured', 'is_active': True, 'is_featured': True}
    other = {'id': 'f2', 'name': 'Plain', 'is_active': True, 'is_featured': False}

    captured = {}

    def fake_find(self, q, *a, **k):
        captured['q'] = q
        data = [featured] if q.get('is_featured') is True else [other]
        return FakeCursor(data)

    monkeypatch.setattr(router.db.products.__class__, 'find', fake_find)

    resp = asyncio.run(router.list_products(featured=True))
    assert 'is_featured' in captured['q']
    assert resp.status_code == 200
    assert 'Featured' in resp.body.decode()
