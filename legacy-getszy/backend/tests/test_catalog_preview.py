"""Tests for the public product preview endpoint (no auth required).

These run without a live MongoDB by patching the DB layer directly on the
route module, so they execute fast in CI and locally.
"""
import asyncio
import importlib

import pytest


@pytest.fixture
def router():
    import routes_catalog
    return routes_catalog


def _resolved(value):
    fut = asyncio.Future()
    fut.set_result(value)
    return fut


def test_preview_404_when_missing(router, monkeypatch):
    async def fake_find(*a, **k):
        return None
    monkeypatch.setattr(router.db.products.__class__, 'find_one', fake_find)
    resp = asyncio.run(router.preview_product('nope'))
    assert resp.status_code == 404
    assert 'Product Not Found' in resp.body.decode()


def test_preview_200_with_product(router, monkeypatch):
    product = {
        'id': 'p1',
        'name': 'Test Saree',
        'slug': 'test-saree',
        'description': 'A beautiful test saree with rich detail.',
        'price': 1999.0,
        'category': 'sarees',
        'stock': 5,
        'images': ['https://example.com/a.jpg', 'https://example.com/b.jpg'],
        'is_active': True,
    }

    async def fake_find(*a, **k):
        return product
    monkeypatch.setattr(router.db.products.__class__, 'find_one', fake_find)

    resp = asyncio.run(router.preview_product('p1'))
    body = resp.body.decode()
    assert resp.status_code == 200
    assert 'Test Saree' in body
    assert '₹1,999' in body
    assert 'In Stock' in body
    assert 'application/ld+json' in body  # SEO structured data
    assert 'thumbnails' in body            # multiple images => gallery
    assert 'https://getszy.com/product/test-saree' in body


def test_preview_out_of_stock(router, monkeypatch):
    product = {
        'id': 'p2', 'name': 'Out', 'price': 10.0, 'stock': 0,
        'category': 'misc', 'images': [], 'is_active': True,
    }

    async def fake_find(*a, **k):
        return product
    monkeypatch.setattr(router.db.products.__class__, 'find_one', fake_find)
    resp = asyncio.run(router.preview_product('p2'))
    body = resp.body.decode()
    assert 'Out of Stock' in body
    assert '₹10' in body
