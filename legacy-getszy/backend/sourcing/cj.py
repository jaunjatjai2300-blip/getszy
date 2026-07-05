"""CJ Dropshipping API client (lazy / key-gated).

When CJ_API_KEY env var is not set we return graceful 'not configured' responses
so the UI works in preview mode. Production: user sets the env var on VPS.
"""
import os
import httpx
from typing import Optional

CJ_API_BASE = 'https://developers.cjdropshipping.com/api2.0/v1'
CJ_API_KEY = os.environ.get('CJ_API_KEY', '').strip()
CJ_EMAIL = os.environ.get('CJ_EMAIL', '').strip()


def is_configured() -> bool:
    return bool(CJ_API_KEY and CJ_EMAIL)


async def auth_token() -> Optional[str]:
    if not is_configured():
        return None
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                f'{CJ_API_BASE}/authentication/getAccessToken',
                json={'email': CJ_EMAIL, 'password': CJ_API_KEY},
            )
            r.raise_for_status()
            data = r.json()
            return (data.get('data') or {}).get('accessToken')
    except Exception:
        return None


async def search_products(keyword: str, page: int = 1) -> dict:
    if not is_configured():
        return {'status': 'not_configured', 'message': 'CJ Dropshipping API key not set. Add CJ_EMAIL and CJ_API_KEY env vars.', 'items': []}
    token = await auth_token()
    if not token:
        return {'status': 'auth_failed', 'message': 'Could not authenticate with CJ Dropshipping', 'items': []}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                f'{CJ_API_BASE}/product/list',
                params={'pageNum': page, 'pageSize': 20, 'productNameEn': keyword},
                headers={'CJ-Access-Token': token},
            )
            r.raise_for_status()
            data = r.json()
            return {'status': 'ok', 'items': (data.get('data') or {}).get('list', [])}
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'items': []}


async def create_order(order_payload: dict) -> dict:
    if not is_configured():
        return {'status': 'not_configured', 'message': 'CJ Dropshipping not configured'}
    token = await auth_token()
    if not token:
        return {'status': 'auth_failed'}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f'{CJ_API_BASE}/shopping/order/createOrderV2',
                json=order_payload,
                headers={'CJ-Access-Token': token},
            )
            r.raise_for_status()
            return {'status': 'ok', 'data': r.json()}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
