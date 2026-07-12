"""WooCommerce sync — products, orders, inventory."""
import os
import httpx
import logging
import base64
from typing import Optional

logger = logging.getLogger('getszy.woo')

WC_URL = os.environ.get('WOO_URL', '').strip()
WC_KEY = os.environ.get('WOO_CONSUMER_KEY', '').strip()
WC_SECRET = os.environ.get('WOO_CONSUMER_SECRET', '').strip()


def _auth():
    if not WC_URL or not WC_KEY or not WC_SECRET:
        return None
    cred = base64.b64encode(f'{WC_KEY}:{WC_SECRET}'.encode()).decode()
    return {'Authorization': f'Basic {cred}', 'Content-Type': 'application/json'}


async def get_products(page: int = 1, per_page: int = 20) -> dict:
    headers = _auth()
    if not headers:
        return {'error': 'WooCommerce not configured', 'products': []}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f'{WC_URL}/wp-json/wc/v3/products', headers=headers, params={'page': page, 'per_page': per_page})
            if resp.status_code == 200:
                return {'products': resp.json(), 'total': int(resp.headers.get('X-WP-Total', 0))}
            return {'error': f'WC returned {resp.status_code}'}
    except Exception as e:
        return {'error': str(e)}


async def get_orders(status: str = 'any', page: int = 1, per_page: int = 20) -> dict:
    headers = _auth()
    if not headers:
        return {'error': 'WooCommerce not configured', 'orders': []}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f'{WC_URL}/wp-json/wc/v3/orders', headers=headers, params={'status': status, 'page': page, 'per_page': per_page})
            if resp.status_code == 200:
                return {'orders': resp.json(), 'total': int(resp.headers.get('X-WP-Total', 0))}
            return {'error': f'WC returned {resp.status_code}'}
    except Exception as e:
        return {'error': str(e)}


async def get_inventory() -> dict:
    headers = _auth()
    if not headers:
        return {'error': 'WooCommerce not configured', 'items': []}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f'{WC_URL}/wp-json/wc/v3/products', headers=headers, params={'per_page': 100, 'stock_status': 'instock'})
            if resp.status_code == 200:
                products = resp.json()
                items = [{'id': p['id'], 'name': p['name'], 'stock': p.get('stock_quantity', 0), 'price': p.get('price', '0')} for p in products]
                return {'items': items}
            return {'error': f'WC returned {resp.status_code}'}
    except Exception as e:
        return {'error': str(e)}
