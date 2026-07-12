"""Production middleware: rate limiting, security headers, request logging."""
import time
import logging
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger('getszy.middleware')

# Simple in-memory rate limiter (per-IP)
_rate_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 100  # requests per window
RATE_WINDOW = 60  # seconds


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else 'unknown'
        now = time.time()

        # Clean old entries
        _rate_store[client_ip] = [
            t for t in _rate_store[client_ip] if now - t < RATE_WINDOW
        ]

        if len(_rate_store[client_ip]) >= RATE_LIMIT:
            logger.warning(f'Rate limit exceeded for {client_ip}')
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429,
                media_type='application/json',
            )

        _rate_store[client_ip].append(now)
        return await call_next(request)


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
