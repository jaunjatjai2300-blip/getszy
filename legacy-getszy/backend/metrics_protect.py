"""Protect the Prometheus `/metrics` endpoint from public access.

The metrics route is unauthenticated by design (Prometheus scrapes it). This
middleware blocks any request that does not originate from localhost or the
internal Docker network (172.x / 10.x / 192.168.x), so the telemetry can only be
read from inside the cluster.
"""
import logging
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger('getszy')

INTERNAL_PREFIXES = ('127.0.0.1', '::1', '172.', '10.', '192.168.')


def _client_ip(request: Request) -> str:
    return (
        request.headers.get('CF-Connecting-IP')
        or request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        or (request.client.host if request.client else '')
    )


class MetricsProtectionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == '/metrics':
            client_ip = _client_ip(request)
            is_internal = any(client_ip.startswith(p) for p in INTERNAL_PREFIXES)
            if not is_internal:
                logger.warning(f'metrics_access_denied: {client_ip}')
                raise HTTPException(
                    status_code=403,
                    detail='Forbidden: Metrics access restricted to internal network.',
                )
        return await call_next(request)
