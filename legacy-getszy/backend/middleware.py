"""Security middleware — rate limiting, security headers, request logging."""
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


def real_client_ip(request: Request) -> str:
    """Resolve the true client IP even behind a proxy / Cloudflare.

    Cloudflare populates `CF-Connecting-IP`; generic proxies use
    `X-Forwarded-For` (comma-separated, client first). Falls back to the
    direct peer (e.g. localhost / direct VPS traffic).
    """
    cf = request.headers.get('cf-connecting-ip')
    if cf:
        return cf.strip()
    fwd = request.headers.get('x-forwarded-for')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.client.host if request.client else 'unknown'


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
        client_ip = real_client_ip(request)
        now = time.time()
        self._clean(client_ip, now)
        if len(self._hits.get(client_ip, [])) >= self.limit:
            try:
                from db import db
                await db.blocked_ips.insert_one({
                    'id': uuid.uuid4().hex,
                    'ip': client_ip,
                    'reason': 'Rate limit exceeded',
                    'severity': 'medium',
                    'created_at': datetime.now(timezone.utc).isoformat(),
                })
            except Exception:
                pass
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


# ─────────────────────────────────────────────────────────────────────────────
# Per-user AI-endpoint rate limiter (defense against LLM cost-exhaustion attacks)
# In-memory sliding window keyed by user id. For multi-worker deployments, swap
# this dict for a shared store (Redis) so the limit is enforced across workers.
# ─────────────────────────────────────────────────────────────────────────────
_AI_HITS: dict[str, list[float]] = defaultdict(list)
AI_RATE_LIMIT = int(os.environ.get('AI_RATE_LIMIT_PER_USER', '30'))
AI_RATE_WINDOW = int(os.environ.get('AI_RATE_WINDOW_SEC', '60'))


def ai_rate_limit_allowed(identifier: str, limit: int = AI_RATE_LIMIT, window: int = AI_RATE_WINDOW) -> bool:
    """Return True if `identifier` is still allowed; records the hit otherwise."""
    now = time.time()
    hits = _AI_HITS[identifier]
    cutoff = now - window
    _AI_HITS[identifier] = [t for t in hits if t > cutoff]
    if len(_AI_HITS[identifier]) >= limit:
        return False
    _AI_HITS[identifier].append(now)
    return True


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = round(time.time() - start, 4)
        # Fire-and-forget: never block the response on a Mongo write.
        try:
            import asyncio
            from db import db
            from datetime import datetime, timezone

            async def _write():
                try:
                    await db.request_logs.insert_one({
                        'method': request.method,
                        'path': str(request.url.path),
                        'status_code': response.status_code,
                        'duration': duration,
                        'ip': real_client_ip(request),
                        'level': 'info',
                        'message': f"{request.method} {request.url.path} -> {response.status_code}",
                        'time': datetime.now(timezone.utc).isoformat(),
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                    })
                except Exception:
                    pass

            asyncio.create_task(_write())
        except Exception:
            pass
        return response
