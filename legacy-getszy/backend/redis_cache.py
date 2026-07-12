"""Redis-based caching, sessions, pub/sub, rate limiting, queues, counters."""
import os
import json
import asyncio
from typing import Any, Optional

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
_pool = None


async def _get_pool():
    global _pool
    if _pool is None:
        try:
            import redis.asyncio as aioredis
            _pool = aioredis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=3)
        except Exception:
            return None
    return _pool


async def get(key: str) -> Optional[str]:
    r = await _get_pool()
    if not r:
        return None
    try:
        return await r.get(key)
    except Exception:
        return None


async def set(key: str, value: str, ttl: int = 3600):
    r = await _get_pool()
    if not r:
        return
    try:
        await r.set(key, value, ex=ttl)
    except Exception:
        pass


async def delete(key: str):
    r = await _get_pool()
    if not r:
        return
    try:
        await r.delete(key)
    except Exception:
        pass


async def cache_get(key: str) -> Optional[Any]:
    val = await get(f"cache:{key}")
    if val:
        try:
            return json.loads(val)
        except Exception:
            return val
    return None


async def cache_set(key: str, value: Any, ttl: int = 3600):
    await set(f"cache:{key}", json.dumps(value, default=str), ttl)


async def session_get(session_id: str) -> Optional[dict]:
    val = await get(f"session:{session_id}")
    if val:
        try:
            return json.loads(val)
        except Exception:
            return None
    return None


async def session_set(session_id: str, data: dict, ttl: int = 86400):
    await set(f"session:{session_id}", json.dumps(data, default=str), ttl)


async def session_delete(session_id: str):
    await delete(f"session:{session_id}")


async def publish(channel: str, message: str):
    r = await _get_pool()
    if not r:
        return
    try:
        await r.publish(channel, message)
    except Exception:
        pass


async def subscribe(channel: str):
    r = await _get_pool()
    if not r:
        return
    try:
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)
        return pubsub
    except Exception:
        return None


async def incr(key: str, ttl: int = 86400) -> int:
    r = await _get_pool()
    if not r:
        return 0
    try:
        val = await r.incr(key)
        if val == 1:
            await r.expire(key, ttl)
        return val
    except Exception:
        return 0


async def queue_push(queue_name: str, item: str):
    r = await _get_pool()
    if not r:
        return
    try:
        await r.rpush(f"queue:{queue_name}", item)
    except Exception:
        pass


async def queue_pop(queue_name: str, timeout: int = 0) -> Optional[str]:
    r = await _get_pool()
    if not r:
        return None
    try:
        if timeout:
            result = await r.blpop(f"queue:{queue_name}", timeout=timeout)
            return result[1] if result else None
        return await r.lpop(f"queue:{queue_name}")
    except Exception:
        return None


async def queue_len(queue_name: str) -> int:
    r = await _get_pool()
    if not r:
        return 0
    try:
        return await r.llen(f"queue:{queue_name}")
    except Exception:
        return 0


async def check_rate_limit(identifier: str, limit: int = 100, window: int = 60) -> bool:
    r = await _get_pool()
    if not r:
        return True
    try:
        key = f"ratelimit:{identifier}"
        current = await r.incr(key)
        if current == 1:
            await r.expire(key, window)
        return current <= limit
    except Exception:
        return True
