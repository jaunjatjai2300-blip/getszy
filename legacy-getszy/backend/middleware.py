"""Security middleware — rate limiting, security headers, request logging."""
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window rate limiter (no Redis required)."""

    def __init__(self, app, limit: int = 200, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _clean(self, ip: str, now: float):
        cutoff = now - self.window
        self._hits[ip] = [t for t in self._hits[ip] if t > cutoff]
        if not self._hits[ip]:
            del self._hits[ip]

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else 'unknown'
        now = time.time()
        self._clean(client_ip, now)
        if len(self._hits.get(client_ip, [])) >= self.limit:
            return JSONResponse(
                {'error': 'Rate limit exceeded. Try again in a minute.'},
                status_code=429,
            )
        self._hits[client_ip].append(now)
        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = round(time.time() - start, 4)
        try:
            from db import db
            from datetime import datetime, timezone
            await db.request_logs.insert_one({
                'method': request.method,
                'path': str(request.url.path),
                'status_code': response.status_code,
                'duration': duration,
                'ip': request.client.host if request.client else 'unknown',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
        except Exception:
            pass
        return response
