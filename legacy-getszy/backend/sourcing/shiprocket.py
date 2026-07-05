"""Shiprocket integration for Indian 5-6 day shipping.

Key-gated. Without SHIPROCKET_EMAIL / SHIPROCKET_PASSWORD set, UI shows
'configure to enable' but the rest of the app works.
"""
import os
import httpx
from typing import Optional

SR_BASE = 'https://apiv2.shiprocket.in/v1/external'
SR_EMAIL = os.environ.get('SHIPROCKET_EMAIL', '').strip()
SR_PASS = os.environ.get('SHIPROCKET_PASSWORD', '').strip()

_token_cache: dict = {'token': None}


def is_configured() -> bool:
    return bool(SR_EMAIL and SR_PASS)


async def get_token() -> Optional[str]:
    if not is_configured():
        return None
    if _token_cache.get('token'):
        return _token_cache['token']
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                f'{SR_BASE}/auth/login',
                json={'email': SR_EMAIL, 'password': SR_PASS},
            )
            r.raise_for_status()
            token = r.json().get('token')
            _token_cache['token'] = token
            return token
    except Exception:
        return None


async def create_shipment(order: dict) -> dict:
    if not is_configured():
        return {'status': 'not_configured', 'message': 'Shiprocket not configured. Add SHIPROCKET_EMAIL and SHIPROCKET_PASSWORD.'}
    token = await get_token()
    if not token:
        return {'status': 'auth_failed'}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f'{SR_BASE}/orders/create/adhoc',
                json=order,
                headers={'Authorization': f'Bearer {token}'},
            )
            r.raise_for_status()
            return {'status': 'ok', 'data': r.json()}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


async def track(awb: str) -> dict:
    if not is_configured():
        return {'status': 'not_configured'}
    token = await get_token()
    if not token:
        return {'status': 'auth_failed'}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(
                f'{SR_BASE}/courier/track/awb/{awb}',
                headers={'Authorization': f'Bearer {token}'},
            )
            r.raise_for_status()
            return {'status': 'ok', 'data': r.json()}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
