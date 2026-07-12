"""Redis connection and utilities — caching, sessions, pub/sub, queues."""
import os
import json
import logging
from typing import Any, Optional

logger = logging.getLogger('getszy.redis')

REDIS_URL = os.environ.get('REDIS_URL', 'redis://redis:6379/0')

# Lazy connection
_redis = None
_pubsub = None


async def get_redis():
    """Get Redis connection (lazy init)."""
    global _redis
    if _redis is None:
        try:
            import redis.asyncio as aioredis
            _redis = aioredis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )
            await _redis.ping()
            logger.info(f'Redis connected: {REDIS_URL}')
        except Exception as e:
            logger.warning(f'Redis unavailable ({e}), falling back to no-cache')
            _redis = _FakeRedis()
    return _redis


class _FakeRedis:
    """Fallback when Redis is unavailable — no-op, everything still works."""

    async def get(self, key): return None
    async def set(self, key, value, **kw): return True
    async def setex(self, key, ttl, value): return True
    async def delete(self, *keys): return 0
    async def exists(self, key): return 0
    async def expire(self, key, ttl): return True
    async def keys(self, pattern): return []
    async def hget(self, name, key): return None
    async def hset(self, name, key=None, value=None, mapping=None): return 0
    async def hgetall(self, name): return {}
    async def hdel(self, name, *keys): return 0
    async def lpush(self, name, *values): return 0
    async def rpush(self, name, *values): return 0
    async def lpop(self, name): return None
    async def lrange(self, name, start, end): return []
    async def llen(self, name): return 0
    async def publish(self, channel, message): return 0
    async def subscribe(self, *channels): return _FakePubSub()
    async def incr(self, key): return 1
    async def decr(self, key): return -1
    async def ping(self): return True
    async def close(self): pass


class _FakePubSub:
    async def get_message(self, timeout=None): return None
    async def unsubscribe(self, *channels): pass
    async def close(self): pass


# ── Caching helpers ──────────────────────────────────────────────────────────

CACHE_SHORT = 60       # 1 min
CACHE_MEDIUM = 300     # 5 min
CACHE_LONG = 3600      # 1 hour
CACHE_DAY = 86400      # 24 hours


async def cache_get(key: str) -> Optional[Any]:
    """Get cached value (JSON deserialized)."""
    r = await get_redis()
    val = await r.get(f'gs:{key}')
    if val is not None:
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val
    return None


async def cache_set(key: str, value: Any, ttl: int = CACHE_MEDIUM) -> bool:
    """Set cache value (JSON serialized)."""
    r = await get_redis()
    try:
        serialized = json.dumps(value, default=str)
        await r.setex(f'gs:{key}', ttl, serialized)
        return True
    except Exception as e:
        logger.warning(f'cache_set failed: {e}')
        return False


async def cache_delete(*keys: str) -> int:
    """Delete cached keys."""
    r = await get_redis()
    return await r.delete(*[f'gs:{k}' for k in keys])


async def cache_clear(pattern: str = 'gs:*') -> int:
    """Clear all cache matching pattern."""
    r = await get_redis()
    keys = await r.keys(pattern)
    if keys:
        return await r.delete(*keys)
    return 0


# ── Session helpers ──────────────────────────────────────────────────────────

async def session_set(user_id: str, data: dict, ttl: int = 86400) -> bool:
    """Store user session."""
    return await cache_set(f'session:{user_id}', data, ttl)


async def session_get(user_id: str) -> Optional[dict]:
    """Get user session."""
    return await cache_get(f'session:{user_id}')


async def session_delete(user_id: str) -> bool:
    """Delete user session."""
    r = await get_redis()
    await r.delete(f'gs:session:{user_id}')
    return True


# ── Rate limiting helpers ────────────────────────────────────────────────────

async def rate_limit_check(key: str, limit: int, window: int) -> dict:
    """Check rate limit. Returns {allowed: bool, remaining: int, retry_after: int}."""
    r = await get_redis()
    full_key = f'gs:rl:{key}'
    try:
        current = await r.incr(full_key)
        if current == 1:
            await r.expire(full_key, window)
        remaining = max(0, limit - current)
        return {
            'allowed': current <= limit,
            'remaining': remaining,
            'retry_after': window if current > limit else 0,
        }
    except Exception:
        return {'allowed': True, 'remaining': limit, 'retry_after': 0}


# ── Pub/Sub helpers ──────────────────────────────────────────────────────────

async def pubsub_publish(channel: str, message: dict):
    """Publish message to channel."""
    r = await get_redis()
    await r.publish(f'gs:{channel}', json.dumps(message, default=str))


async def pubsub_subscribe(channel: str):
    """Subscribe to channel. Returns pubsub object."""
    r = await get_redis()
    pubsub = await r.subscribe(f'gs:{channel}')
    return pubsub


# ── Queue helpers ────────────────────────────────────────────────────────────

async def queue_push(queue_name: str, task: dict) -> int:
    """Push task to queue."""
    r = await get_redis()
    return await r.rpush(f'gs:queue:{queue_name}', json.dumps(task, default=str))


async def queue_pop(queue_name: str) -> Optional[dict]:
    """Pop task from queue (blocking)."""
    r = await get_redis()
    val = await r.lpop(f'gs:queue:{queue_name}')
    if val:
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


async def queue_len(queue_name: str) -> int:
    """Get queue length."""
    r = await get_redis()
    return await r.llen(f'gs:queue:{queue_name}')


# ── Counters ─────────────────────────────────────────────────────────────────

async def counter_increment(key: str, amount: int = 1) -> int:
    """Increment counter."""
    r = await get_redis()
    return await r.incr(f'gs:counter:{key}', amount)


async def counter_get(key: str) -> int:
    """Get counter value."""
    r = await get_redis()
    val = await r.get(f'gs:counter:{key}')
    return int(val) if val else 0
