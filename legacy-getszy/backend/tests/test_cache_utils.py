"""Pure-logic tests for the in-memory TTL cache (no Mongo required)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cache_utils import cache_get, cache_set, cache_key, cache_invalidate


def test_set_get():
    cache_set('k1', [1, 2, 3], ttl=60)
    assert cache_get('k1') == [1, 2, 3]


def test_key_builder():
    assert cache_key('products', None, 'x', True, 8) == 'products::x:True:8'


def test_expiry():
    cache_set('k2', 'v', ttl=-1)
    assert cache_get('k2') is None


def test_invalidate():
    cache_set('products:abc', 'x', ttl=60)
    cache_set('products:def', 'y', ttl=60)
    cache_invalidate('products')
    assert cache_get('products:abc') is None
    assert cache_get('products:def') is None
