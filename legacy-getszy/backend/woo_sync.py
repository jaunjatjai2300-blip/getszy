"""WooCommerce integration — sync products, orders, inventory."""
import os
import httpx
import logging
import hashlib
import hmac
from base64 import b64encode

logger = logging.getLogger('getszy.woocommerce')

WOO_URL = os.environ.get('WOO_URL', '')
WOO_KEY = os.environ.get('WOO_CONSUMER_KEY', '')
WOO_SECRET = os.environ.get('WOO_CONSUMER_SECRET', '')


def _auth():
    return (WOO_KEY, WOO_SECRET)


async def _woo_get(endpoint: str, params: dict = None) -> dict:
    if not WOO_URL:
        return {'error': 'WooCommerce not configured. Set WOO_URL env var.'}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f'{WOO_URL}/wp-json/wc/v3/{endpoint}',
            auth=_auth(),
            params=params or {},
        )
        resp.raise_for_status()
        return resp.json()


async def _woo_post(endpoint: str, data: dict) -> dict:
    if not WOO_URL:
        return {'error': 'WooCommerce not configured'}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f'{WOO_URL}/wp-json/wc/v3/{endpoint}',
            auth=_auth(),
            json=data,
        )
        resp.raise_for_status()
        return resp.json()


async def _woo_put(endpoint: str, data: dict) -> dict:
    if not WOO_URL:
        return {'error': 'WooCommerce not configured'}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.put(
            f'{WOO_URL}/wp-json/wc/v3/{endpoint}',
            auth=_auth(),
            json=data,
        )
        resp.raise_for_status()
        return resp.json()


# ── Products ─────────────────────────────────────────────────────────────────

async def sync_products(per_page: int = 50, page: int = 1) -> dict:
    """Fetch products from WooCommerce."""
    data = await _woo_get('products', {'per_page': per_page, 'page': page})
    if isinstance(data, dict) and 'error' in data:
        return data
    return {
        'products': [
            {
                'id': p['id'],
                'name': p['name'],
                'slug': p['slug'],
                'price': p['price'],
                'stock_quantity': p.get('stock_quantity', 0),
                'status': p['status'],
                'images': [img['src'] for img in p.get('images', [])],
            }
            for p in data
        ],
        'count': len(data),
    }


async def sync_product_to_woo(product: dict) -> dict:
    """Push a Getszy product to WooCommerce."""
    woo_data = {
        'name': product['name'],
        'regular_price': str(product['price']),
        'description': product.get('description', ''),
        'short_description': product.get('description', '')[:200],
        'manage_stock': True,
        'stock_quantity': product.get('stock', 0),
        'status': 'publish' if product.get('is_active', True) else 'draft',
        'images': [{'src': img} for img in product.get('images', [])],
    }
    return await _woo_post('products', woo_data)


# ── Orders ───────────────────────────────────────────────────────────────────

async def sync_orders(status: str = 'any', per_page: int = 50) -> dict:
    """Fetch orders from WooCommerce."""
    data = await _woo_get('orders', {'status': status, 'per_page': per_page})
    if isinstance(data, dict) and 'error' in data:
        return data
    return {
        'orders': [
            {
                'id': o['id'],
                'number': o['number'],
                'status': o['status'],
                'total': o['total'],
                'customer_id': o.get('customer_id'),
                'items_count': o.get('items_count', 0),
                'date_created': o['date_created'],
            }
            for o in data
        ],
        'count': len(data),
    }


# ── Inventory ────────────────────────────────────────────────────────────────

async def update_stock(product_id: int, quantity: int) -> dict:
    """Update stock quantity for a WooCommerce product."""
    return await _woo_put(f'products/{product_id}', {
        'stock_quantity': quantity,
        'manage_stock': True,
    })


# ── Status ───────────────────────────────────────────────────────────────────

async def check_connection() -> dict:
    """Check if WooCommerce is reachable."""
    if not WOO_URL:
        return {'connected': False, 'error': 'WOO_URL not set'}
    try:
        data = await _woo_get('system_status')
        if isinstance(data, dict) and 'error' in data:
            return {'connected': False, 'error': data['error']}
        return {'connected': True, 'store_url': WOO_URL, 'version': data.get('wc_version', 'unknown')}
    except Exception as e:
        return {'connected': False, 'error': str(e)}
