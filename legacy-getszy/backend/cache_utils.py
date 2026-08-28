"""Bounded LRU cache with memory budget, eviction, and statistics.

Replaces the previous unbounded dict cache. Every entry is estimated by
byte-cost; when the cache exceeds the configured maximum entries OR maximum
estimated bytes, the least-recently-used entries are evicted until both
limits are respected.

Design constraints:
- Process-local (single backend container)
- Thread-safe via asyncio-safe operations (single event loop)
- Never caches secrets, approval tokens, or mutable auth state
- Namespace isolation via key prefix
- Cache statistics for observability
"""
from __future__ import annotations

import sys
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any


# ── Configuration ─────────────────────────────────────────────────────────────
_MAX_ENTRIES = 512
_MAX_BYTES = 8 * 1024 * 1024  # 8 MB estimated ceiling
_DEFAULT_TTL = 60  # seconds


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expired: int = 0
    total_sets: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'expired': self.expired,
            'total_sets': self.total_sets,
            'hit_rate': round(self.hit_rate, 4),
        }


class BoundedLRUCache:
    """Ordered-dict based LRU with TTL, byte budget, and entry cap.

    Bytes are estimated via ``sys.getsizeof`` on the value; for complex
    objects the estimate is rough but sufficient to prevent runaway memory.
    """

    def __init__(self, max_entries: int = _MAX_ENTRIES, max_bytes: int = _MAX_BYTES):
        self._max_entries = max_entries
        self._max_bytes = max_bytes
        self._data: OrderedDict[str, tuple[float, Any, int, int]] = OrderedDict()
        # key -> (stored_at, value, ttl, est_bytes)
        self._current_bytes = 0
        self.stats = CacheStats()

    def _estimate_bytes(self, value: Any) -> int:
        try:
            return sys.getsizeof(value)
        except Exception:
            return 256  # conservative fallback

    def _evict(self) -> None:
        """Evict oldest entries until within both limits."""
        while self._data:
            if len(self._data) <= self._max_entries and self._current_bytes <= self._max_bytes:
                break
            _key, (_, _, _, est) = self._data.popitem(last=False)
            self._current_bytes -= est
            self.stats.evictions += 1

    def get(self, key: str) -> Any | None:
        entry = self._data.get(key)
        if entry is None:
            self.stats.misses += 1
            return None
        stored_at, value, ttl, est = entry
        if time.time() - stored_at >= ttl:
            self._data.pop(key)
            self._current_bytes -= est
            self.stats.expired += 1
            self.stats.misses += 1
            return None
        # Move to end (most recently used)
        self._data.move_to_end(key)
        self.stats.hits += 1
        return value

    def set(self, key: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
        est = self._estimate_bytes(value)
        # If key already exists, remove old entry first
        if key in self._data:
            old = self._data.pop(key)
            self._current_bytes -= old[3]
        self._data[key] = (time.time(), value, ttl, est)
        self._current_bytes += est
        self.stats.total_sets += 1
        # Evict after adding to handle overflows
        self._evict()

    def invalidate(self, prefix: str) -> int:
        """Remove all keys starting with *prefix*. Returns count removed."""
        removed = 0
        for key in list(self._data.keys()):
            if key.startswith(prefix):
                _, _, _, est = self._data.pop(key)
                self._current_bytes -= est
                removed += 1
        return removed

    def clear(self) -> None:
        self._data.clear()
        self._current_bytes = 0

    def __len__(self) -> int:
        return len(self._data)

    @property
    def estimated_bytes(self) -> int:
        return self._current_bytes

    def info(self) -> dict:
        return {
            'entries': len(self._data),
            'max_entries': self._max_entries,
            'estimated_bytes': self._current_bytes,
            'max_bytes': self._max_bytes,
            'stats': self.stats.to_dict(),
        }


# ── Module-level singleton ────────────────────────────────────────────────────
_cache = BoundedLRUCache()


def cache_get(key: str) -> Any | None:
    """Get a value from the bounded LRU cache. Returns None on miss/expiry."""
    return _cache.get(key)


def cache_set(key: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
    """Store a value in the bounded LRU cache."""
    _cache.set(key, value, ttl)


def cache_key(*parts: Any) -> str:
    """Build a colon-delimited cache key."""
    return ":".join("" if p is None else str(p) for p in parts)


def cache_invalidate(prefix: str) -> int:
    """Invalidate all keys matching a prefix. Returns count removed."""
    return _cache.invalidate(prefix)


def cache_info() -> dict:
    """Return cache statistics for observability."""
    return _cache.info()


def cache_clear() -> None:
    """Clear all cache entries."""
    _cache.clear()
