"""Production middleware: rate limiting, security headers, request logging."""
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger('getszy.middleware')

RATE_LIMIT = 100  # requests per window
RATE_WINDOW = 60  # seconds


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from redis_cache import rate_limit_check
        client_ip = request.client.host if request.client else 'unknown'
        key = f'{client_ip}:{request.url.path[:50]}'

        result = await rate_limit_check(key, RATE_LIMIT, RATE_WINDOW)

        if not result['allowed']:
            logger.warning(f'Rate limit exceeded for {client_ip}')
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429,
                media_type='application/json',
                headers={
                    'Retry-After': str(result['retry_after']),
                    'X-RateLimit-Limit': str(RATE_LIMIT),
                    'X-RateLimit-Remaining': '0',
                },
            )

        response = await call_next(request)
        response.headers['X-RateLimit-Limit'] = str(RATE_LIMIT)
        response.headers['X-RateLimit-Remaining'] = str(result['remaining'])
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            f'{request.method} {request.url.path} '
            f'status={response.status_code} duration={duration:.3f}s'
        )
        return response
