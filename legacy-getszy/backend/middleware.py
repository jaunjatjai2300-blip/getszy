"""Security middleware — rate limiting, security headers, request logging."""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else 'unknown'
        try:
            from redis_cache import check_rate_limit
            allowed = await check_rate_limit(f'ip:{client_ip}', limit=200, window=60)
            if not allowed:
                return JSONResponse({'error': 'Rate limit exceeded. Try again in a minute.'}, status_code=429)
        except Exception:
            pass
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
