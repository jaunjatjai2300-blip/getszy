"""Shared async Redis client (connection pool) for distributed state.

Used by the rate-limiter and any other cross-worker state. Connection is lazy
(created at import, connected on first command), so a missing Redis only fails
open at request time, not at boot.
"""
import os
import logging
from redis.asyncio import from_url

logger = logging.getLogger('getszy')

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
redis = from_url(REDIS_URL, encoding='utf-8', decode_responses=True, max_connections=100)


async def check_redis_health():
    try:
        return await redis.ping()
    except Exception as e:
        logger.error(f'redis_connection_failed: {e}')
        return False
