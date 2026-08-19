"""Distributed sliding-window rate limiter backed by Redis.

Replaces the previous in-memory limiter (which reset on restart and was not shared
across workers). Uses a Redis sorted-set sliding window inside a transactional
pipeline so increments are atomic across processes.

By default this middleware FAILS OPEN (request proceeds if Redis is unavailable) and
trusts only the real peer IP. Set RATE_LIMIT_TRUST_PROXY=1 when Getszy sits behind a
known proxy (e.g. Cloudflare/caddy) so X-Forwarded-For / CF-Connecting-IP are honored,
and set RATE_LIMIT_FAIL_CLOSED=1 to return 503 instead of proceeding when Redis is down.
"""
import os
import time
import logging
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from redis_client import redis

logger = logging.getLogger('getszy')

# When True, honor CF-Connecting-IP / X-Forwarded-For (only safe behind a trusted proxy).
TRUST_PROXY = os.environ.get('RATE_LIMIT_TRUST_PROXY', '').strip().lower() in ('1', 'true', 'yes', 'on')
# When True, return 503 instead of allowing the request when Redis is unreachable.
FAIL_CLOSED = os.environ.get('RATE_LIMIT_FAIL_CLOSED', '').strip().lower() in ('1', 'true', 'yes', 'on')

# Paths that must never be throttled.
EXEMPT_PATHS = {
    '/health', '/healthz', '/metrics', '/health/llm',
    '/docs', '/openapi.json', '/favicon.ico',
}


def _client_ip(request: Request) -> str:
    peer = request.client.host if request.client else 'unknown'
    if not TRUST_PROXY:
        # Never trust client-supplied headers unless explicitly behind a trusted proxy.
        return peer
    return (
        request.headers.get('CF-Connecting-IP')
        or request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        or peer
    )


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 200):
        super().__init__(app)
        self.limit = requests_per_minute
        self.window = 60  # seconds

    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS or redis is None:
            return await call_next(request)

        client_ip = _client_ip(request)
        key = f'rate_limit:global:{client_ip}'
        current_time = time.time()
        window_start = current_time - self.window

        try:
            pipe = await redis.pipeline(transaction=True)
            pipe.zremrangebyscore(key, 0, window_start)   # drop stale timestamps
            pipe.zcard(key)                                # count in window
            pipe.zadd(key, {str(current_time): current_time})  # record this hit
            pipe.expire(key, self.window)                 # keep keys tidy
            results = await pipe.execute()

            request_count = results[1]
            if request_count >= self.limit:
                raise HTTPException(
                    status_code=429,
                    detail='Too many requests. Please try again later.',
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'redis_rate_limit_error: {e}')
            if FAIL_CLOSED:
                raise HTTPException(
                    status_code=503,
                    detail='Rate limiting unavailable. Please try again later.',
                )

        return await call_next(request)
