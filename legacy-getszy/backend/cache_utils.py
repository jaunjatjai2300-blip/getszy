"""Lightweight in-memory TTL cache for read-heavy public endpoints.

This avoids hammering MongoDB on every storefront page load. Cache entries
are keyed by caller-supplied strings and auto-expire after a TTL. It is
process-local (fine for a single backend container) and intentionally simple.
"""
import time

_CACHE: dict[str, tuple[float, object, int]] = {}


def cache_get(key: str):
    hit = _CACHE.get(key)
    if not hit:
        return None
    stored_at, value, ttl = hit
    if time.time() - stored_at >= ttl:
        _CACHE.pop(key, None)
        return None
    return value


def cache_set(key: str, value, ttl: int = 60):
    _CACHE[key] = (time.time(), value, ttl)


def cache_key(*parts) -> str:
    return ":".join("" if p is None else str(p) for p in parts)


def cache_invalidate(prefix: str):
    for k in list(_CACHE.keys()):
        if k.startswith(prefix):
            _CACHE.pop(k, None)
