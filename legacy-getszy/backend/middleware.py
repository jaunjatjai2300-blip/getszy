"""Security middleware — security headers, per-user AI rate limit, request logging.

NOTE: the global request rate limiter lives in `redis_rate_limit.py`
(`RedisRateLimitMiddleware`) and is Redis-backed so the limit is enforced
across all workers. The old in-memory `RateLimitMiddleware` was removed: it
was never registered (dead code) and reset on restart, which gave a false
impression that multi-worker rate limiting was broken. Do not reintroduce an
in-memory global limiter here.
"""
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


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
# Per-user AI-endpoint rate limiter (defense against LLM cost-exhaustion attacks).
# Redis-backed so the limit is enforced across ALL workers (one user cannot
# drain the shared Groq daily quota and 503 everyone else). Falls back to a
# per-worker in-memory window ONLY when Redis is unavailable, so local/dev and
# CI still get best-effort protection without a Redis dependency.
# ─────────────────────────────────────────────────────────────────────────────
from redis_client import redis as _ai_redis

_AI_HITS: dict[str, list[float]] = defaultdict(list)
AI_RATE_LIMIT = int(os.environ.get('AI_RATE_LIMIT_PER_USER', '30'))
AI_RATE_WINDOW = int(os.environ.get('AI_RATE_WINDOW_SEC', '60'))


async def ai_rate_limit_allowed(identifier: str, limit: int = AI_RATE_LIMIT, window: int = AI_RATE_WINDOW) -> bool:
    """Return True if `identifier` is still allowed; records the hit otherwise.

    Uses a Redis sorted-set sliding window (atomic pipeline) when Redis is
    reachable, otherwise a per-worker in-memory best-effort window.
    """
    if _ai_redis is not None:
        try:
            now = time.time()
            key = f'ai_ratelimit:{identifier}'
            pipe = _ai_redis.pipeline(transaction=True)
            pipe.zremrangebyscore(key, 0, now - window)   # drop stale hits
            pipe.zcard(key)                                # count in window
            pipe.zadd(key, {str(now): now})               # record this hit
            pipe.expire(key, window)                      # keep keys tidy
            results = await pipe.execute()
            return results[1] < limit
        except Exception:
            # Redis hiccup → fall through to in-memory best-effort (fail soft).
            pass
    # In-memory fallback (per-worker): used in dev/CI or when Redis is down.
    now = time.time()
    hits = _AI_HITS[identifier]
    cutoff = now - window
    _AI_HITS[identifier] = [t for t in hits if t > cutoff]
    if len(_AI_HITS[identifier]) >= limit:
        return False
    _AI_HITS[identifier].append(now)
    return True


# Bounded request-log writer: under DDoS we must not spawn one unbounded
# asyncio task + Mongo insert per request (that self-amplifies into OOM).
# Cap concurrent log writes; drop the log (never the response) when saturated.
_LOG_MAX_CONCURRENT = int(os.environ.get('REQUEST_LOG_MAX_CONCURRENT', '50'))
_log_semaphore = None
_log_inflight = 0
_log_lock = None


def _get_log_gate():
    global _log_semaphore, _log_lock
    if _log_semaphore is None:
        import asyncio
        _log_semaphore = asyncio.Semaphore(_LOG_MAX_CONCURRENT)
        _log_lock = asyncio.Lock()
    return _log_semaphore, _log_lock


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = round(time.time() - start, 4)
        # Fire-and-forget but BOUNDED: never block the response on a Mongo write,
        # and never let logging tasks grow without limit under load.
        try:
            sem, lock = _get_log_gate()
            async with lock:
                if _log_inflight >= _LOG_MAX_CONCURRENT:
                    return response  # saturated — drop the log, keep the response
                _log_inflight += 1

            async def _write():
                try:
                    async with sem:
                        from db import db
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
                finally:
                    async with lock:
                        global _log_inflight
                        _log_inflight = max(0, _log_inflight - 1)

            import asyncio
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
