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


# ─────────────────────────────────────────────────────────────────────────────
# Prometheus metrics (optional — requires prometheus_client)
# Exposes http_requests_total{method,status} + http_request_duration_seconds so
# Prometheus can scrape /metrics and drive the production alert rules.
# ─────────────────────────────────────────────────────────────────────────────
_METRICS_SKIP_PATHS = {'/metrics', '/docs', '/openapi.json', '/health', '/healthz'}

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    _PROM_AVAILABLE = True
except Exception:  # pragma: no cover - dependency optional in some envs
    _PROM_AVAILABLE = False
    generate_latest = None
    CONTENT_TYPE_LATEST = 'text/plain; version=0.0.4'
    REQUEST_COUNT = REQUEST_LATENCY = REQUESTS_IN_PROGRESS = None


if _PROM_AVAILABLE:
    REQUEST_COUNT = Counter(
        'http_requests_total',
        'Total HTTP requests handled by the Getszy backend.',
        ['method', 'status'],
    )
    REQUEST_LATENCY = Histogram(
        'http_request_duration_seconds',
        'HTTP request latency in seconds.',
        ['method'],
    )
    REQUESTS_IN_PROGRESS = Gauge(
        'http_requests_in_progress',
        'Number of HTTP requests currently being processed.',
    )
    # Domain metrics consumed by the production alert rules (alerts.yml).
    VIDEO_JOBS_PENDING = Gauge(
        'video_factory_jobs_pending',
        'Number of video-factory jobs awaiting/cloning/rendering.',
    )
    VIDEO_JOBS_COMPLETED = Counter(
        'video_factory_jobs_completed_total',
        'Total video-factory jobs completed successfully.',
    )
    OLLAMA_FAILURES = Counter(
        'ollama_inference_failures_total',
        'Total local/Ollama inference failures or timeouts.',
    )
    LAST_BACKUP_TS = Gauge(
        'getszy_last_backup_timestamp_seconds',
        'Unix timestamp (seconds) of the last successful automated backup.',
    )


def set_video_jobs_pending(n: int):
    if _PROM_AVAILABLE:
        try:
            VIDEO_JOBS_PENDING.set(int(n))
        except Exception:
            pass


def inc_video_jobs_completed():
    if _PROM_AVAILABLE:
        try:
            VIDEO_JOBS_COMPLETED.inc()
        except Exception:
            pass


def inc_ollama_failure():
    if _PROM_AVAILABLE:
        try:
            OLLAMA_FAILURES.inc()
        except Exception:
            pass


def set_last_backup_ts(ts: float):
    if _PROM_AVAILABLE:
        try:
            LAST_BACKUP_TS.set(float(ts))
        except Exception:
            pass


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Export request counters / latency for Prometheus scraping."""

    async def dispatch(self, request: Request, call_next):
        if not _PROM_AVAILABLE or request.url.path in _METRICS_SKIP_PATHS:
            return await call_next(request)
        method = request.method
        REQUESTS_IN_PROGRESS.inc()
        start = time.time()
        try:
            response = await call_next(request)
        finally:
            REQUESTS_IN_PROGRESS.dec()
        REQUEST_LATENCY.labels(method=method).observe(time.time() - start)
        REQUEST_COUNT.labels(method=method, status=response.status_code).inc()
        return response
