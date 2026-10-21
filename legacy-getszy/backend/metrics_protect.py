"""Protect the Prometheus `/metrics` endpoint from public access.

The metrics route is unauthenticated by design (Prometheus scrapes it). This
middleware blocks any request that does not originate from localhost or the
internal Docker network (172.x / 10.x / 192.168.x), so the telemetry can only be
read from inside the cluster.
"""
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from redis_rate_limit import _client_ip

logger = logging.getLogger('getszy')

INTERNAL_PREFIXES = ('127.0.0.1', '::1', '172.', '10.', '192.168.')


class MetricsProtectionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path == '/metrics':
            client_ip = _client_ip(request)
            is_internal = any(client_ip.startswith(p) for p in INTERNAL_PREFIXES)
            if not is_internal:
                logger.warning(f'metrics_access_denied: {client_ip}')
                return JSONResponse(
                    status_code=403,
                    content={'detail': 'Forbidden: Metrics access restricted to internal network.'},
                )
        return await call_next(request)
