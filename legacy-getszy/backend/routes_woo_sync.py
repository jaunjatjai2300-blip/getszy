import uuid
import httpx
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_admin
from db import db
from woo_sync import get_products, get_orders, get_inventory, WC_URL, WC_KEY, WC_SECRET, _auth

router = APIRouter(prefix='/admin/woo-sync', tags=['woo-sync'])


def _now():
    return datetime.now(timezone.utc).isoformat()


def _uid():
    return str(uuid.uuid4())


class ProductPushIn(BaseModel):
    name: Optional[str] = None
    regular_price: Optional[str] = None
    description: Optional[str] = None
    stock_quantity: Optional[int] = None
    stock_status: Optional[str] = None


class OrderStatusIn(BaseModel):
    status: str


class InventoryAdjustIn(BaseModel):
    stock_quantity: int
    stock_status: Optional[str] = 'instock'


class WebhookRegisterIn(BaseModel):
    name: str = 'Getszy Sync'
    topic: str = 'order.created'
    delivery_url: str = ''
    secret: Optional[str] = None


class FullSyncIn(BaseModel):
    products: bool = True
    orders: bool = True
    inventory: bool = True
    customers: bool = True
    coupons: bool = True


# ── Connection ──

@router.get('/status')
async def woo_status(_=Depends(get_current_admin)):
    if not WC_URL or not WC_KEY or not WC_SECRET:
        raise HTTPException(400, 'WooCommerce not configured')
    headers = _auth()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f'{WC_URL}/wp-json/wc/v3/system_status', headers=headers)
            if resp.status_code != 200:
                return {'connected': False, 'error': f'WC returned {resp.status_code}'}
            data = resp.json()
            product_count = await db.woo_products.estimated_document_count()
            order_count = await db.woo_orders.estimated_document_count()
            return {
                'connected': True,
                'store': {
                    'name': data.get('settings', {}).get('store_name', ''),
                    'url': WC_URL,
                    'version': data.get('version', ''),
                    'currency': data.get('settings', {}).get('currency', ''),
                },
                'product_count': product_count,
                'order_count': order_count,
            }
    except Exception as e:
        return {'connected': False, 'error': str(e)}


# ── Products ──

@router.get('/products')
async def list_wc_products(page: int = 1, per_page: int = 20, _=Depends(get_current_admin)):
    result = await get_products(page=page, per_page=per_page)
    if 'error' in result:
        raise HTTPException(502, result['error'])
    for p in result['products']:
        await db.woo_products.update_one({'wc_id': p['id']}, {'$set': {
            'wc_id': p['id'],
            'name': p.get('name', ''),
            'slug': p.get('slug', ''),
            'status': p.get('status', ''),
            'price': p.get('price', ''),
            'regular_price': p.get('regular_price', ''),
            'sale_price': p.get('sale_price', ''),
            'description': p.get('description', ''),
            'short_description': p.get('short_description', ''),
            'stock_quantity': p.get('stock_quantity'),
            'stock_status': p.get('stock_status', ''),
            'categories': [c.get('name', '') for c in p.get('categories', [])],
            'images': [i.get('src', '') for i in p.get('images', [])],
            'sku': p.get('sku', ''),
            'weight': p.get('weight', ''),
            'dimensions': p.get('dimensions', {}),
            'attributes': p.get('attributes', []),
            'updated_at': _now(),
        }}, upsert=True)
    return result


@router.post('/products/sync')
async def sync_products(_=Depends(get_current_admin)):
    created, updated, conflicts = 0, 0, 0
    page = 1
    all_wc_products = []
    while True:
        result = await get_products(page=page, per_page=100)
        if 'error' in result:
            raise HTTPException(502, result['error'])
        products = result['products']
        if not products:
            break
        all_wc_products.extend(products)
        if len(products) < 100:
            break
        page += 1

    wc_ids = set()
    for p in all_wc_products:
        wc_ids.add(p['id'])
        existing = await db.woo_products.find_one({'wc_id': p['id']})
        doc = {
            'wc_id': p['id'],
            'name': p.get('name', ''),
            'slug': p.get('slug', ''),
            'status': p.get('status', ''),
            'price': p.get('price', ''),
            'regular_price': p.get('regular_price', ''),
            'sale_price': p.get('sale_price', ''),
            'description': p.get('description', ''),
            'short_description': p.get('short_description', ''),
            'stock_quantity': p.get('stock_quantity'),
            'stock_status': p.get('stock_status', ''),
            'categories': [c.get('name', '') for c in p.get('categories', [])],
            'images': [i.get('src', '') for i in p.get('images', [])],
            'sku': p.get('sku', ''),
            'weight': p.get('weight', ''),
            'dimensions': p.get('dimensions', {}),
            'attributes': p.get('attributes', []),
            'synced_at': _now(),
        }
        if existing:
            updated += 1
        else:
            created += 1
        await db.woo_products.update_one({'wc_id': p['id']}, {'$set': doc}, upsert=True)

    local_products = await db.products.find({}, {'_id': 0}).to_list(5000)
    headers = _auth()
    if headers:
        for lp in local_products:
            sku = lp.get('sku', lp.get('id', ''))
            matched = False
            for wp in all_wc_products:
                if wp.get('sku') == sku or wp.get('name') == lp.get('name', ''):
                    matched = True
                    break
            if not matched:
                try:
                    async with httpx.AsyncClient(timeout=30) as client:
                        resp = await client.post(f'{WC_URL}/wp-json/wc/v3/products', headers=headers, json={
                            'name': lp.get('name', ''),
                            'regular_price': str(lp.get('price', '0')),
                            'description': lp.get('description', ''),
                            'sku': sku,
                            'manage_stock': True,
                            'stock_quantity': lp.get('stock', 0),
                        })
                        if resp.status_code in (200, 201):
                            created += 1
                        else:
                            conflicts += 1
                except Exception:
                    conflicts += 1

    await db.woo_sync_logs.insert_one({
        'id': _uid(), 'action': 'products_sync', 'status': 'completed',
        'details': {'created': created, 'updated': updated, 'conflicts': conflicts},
        'timestamp': _now(),
    })
    return {'created': created, 'updated': updated, 'conflicts': conflicts, 'total_wc': len(all_wc_products)}


@router.get('/products/{product_id}')
async def get_wc_product(product_id: int, _=Depends(get_current_admin)):
    headers = _auth()
    if not headers:
        raise HTTPException(400, 'WC not configured')
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f'{WC_URL}/wp-json/wc/v3/products/{product_id}', headers=headers)
        if resp.status_code != 200:
            raise HTTPException(502, f'WC returned {resp.status_code}')
        return resp.json()


@router.post('/products/{product_id}/push')
async def push_product(product_id: int, body: ProductPushIn, _=Depends(get_current_admin)):
    headers = _auth()
    if not headers:
        raise HTTPException(400, 'WC not configured')
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.put(f'{WC_URL}/wp-json/wc/v3/products/{product_id}', headers=headers, json=payload)
        if resp.status_code != 200:
            raise HTTPException(502, f'WC returned {resp.status_code}')
        data = resp.json()
        await db.woo_products.update_one({'wc_id': product_id}, {'$set': {
            'name': data.get('name', ''),
            'price': data.get('price', ''),
            'description': data.get('description', ''),
            'stock_quantity': data.get('stock_quantity'),
            'stock_status': data.get('stock_status', ''),
            'updated_at': _now(),
        }})
        return data


# ── Orders ──

@router.get('/orders')
async def list_wc_orders(status: str = 'any', page: int = 1, per_page: int = 20, _=Depends(get_current_admin)):
    result = await get_orders(status=status, page=page, per_page=per_page)
    if 'error' in result:
        raise HTTPException(502, result['error'])
    for o in result['orders']:
        await db.woo_orders.update_one({'wc_id': o['id']}, {'$set': {
            'wc_id': o['id'],
            'number': o.get('number', ''),
            'status': o.get('status', ''),
            'total': o.get('total', '0'),
            'currency': o.get('currency', ''),
            'customer_id': o.get('customer_id', 0),
            'billing': o.get('billing', {}),
            'shipping': o.get('shipping', {}),
            'line_items': o.get('line_items', []),
            'payment_method': o.get('payment_method', ''),
            'payment_method_title': o.get('payment_method_title', ''),
            'date_created': o.get('date_created', ''),
            'date_modified': o.get('date_modified', ''),
            'updated_at': _now(),
        }}, upsert=True)
    return result


@router.post('/orders/sync')
async def sync_orders(_=Depends(get_current_admin)):
    total_synced = 0
    for order_status in ['pending', 'processing', 'on-hold', 'completed', 'cancelled', 'refunded', 'failed']:
        page = 1
        while True:
            result = await get_orders(status=order_status, page=page, per_page=100)
            if 'error' in result:
                break
            orders = result['orders']
            if not orders:
                break
            for o in orders:
                await db.woo_orders.update_one({'wc_id': o['id']}, {'$set': {
                    'wc_id': o['id'],
                    'number': o.get('number', ''),
                    'status': o.get('status', ''),
                    'total': o.get('total', '0'),
                    'currency': o.get('currency', ''),
                    'customer_id': o.get('customer_id', 0),
                    'billing': o.get('billing', {}),
                    'shipping': o.get('shipping', {}),
                    'line_items': o.get('line_items', []),
                    'payment_method': o.get('payment_method', ''),
                    'payment_method_title': o.get('payment_method_title', ''),
                    'date_created': o.get('date_created', ''),
                    'date_modified': o.get('date_modified', ''),
                    'synced_at': _now(),
                }}, upsert=True)
                total_synced += 1
            if len(orders) < 100:
                break
            page += 1

    await db.woo_sync_logs.insert_one({
        'id': _uid(), 'action': 'orders_sync', 'status': 'completed',
        'details': {'total_synced': total_synced},
        'timestamp': _now(),
    })
    return {'total_synced': total_synced}


@router.get('/orders/{order_id}')
async def get_wc_order(order_id: int, _=Depends(get_current_admin)):
    headers = _auth()
    if not headers:
        raise HTTPException(400, 'WC not configured')
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f'{WC_URL}/wp-json/wc/v3/orders/{order_id}', headers=headers)
        if resp.status_code != 200:
            raise HTTPException(502, f'WC returned {resp.status_code}')
        return resp.json()


@router.post('/orders/{order_id}/status')
async def update_order_status(order_id: int, body: OrderStatusIn, _=Depends(get_current_admin)):
    headers = _auth()
    if not headers:
        raise HTTPException(400, 'WC not configured')
    valid = ['pending', 'processing', 'on-hold', 'completed', 'cancelled', 'refunded', 'failed']
    if body.status not in valid:
        raise HTTPException(400, f'Invalid status. Must be one of: {valid}')
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.put(f'{WC_URL}/wp-json/wc/v3/orders/{order_id}', headers=headers, json={'status': body.status})
        if resp.status_code != 200:
            raise HTTPException(502, f'WC returned {resp.status_code}')
        data = resp.json()
        await db.woo_orders.update_one({'wc_id': order_id}, {'$set': {
            'status': body.status,
            'updated_at': _now(),
        }})
        return {'order_id': order_id, 'status': body.status, 'updated': True}


# ── Inventory ──

@router.get('/inventory')
async def get_wc_inventory(_=Depends(get_current_admin)):
    result = await get_inventory()
    if 'error' in result:
        raise HTTPException(502, result['error'])
    for item in result['items']:
        await db.woo_inventory.update_one({'wc_id': item['id']}, {'$set': {
            'wc_id': item['id'],
            'name': item['name'],
            'stock': item['stock'],
            'price': item['price'],
            'updated_at': _now(),
        }}, upsert=True)
    return result


@router.post('/inventory/sync')
async def sync_inventory(_=Depends(get_current_admin)):
    wc_to_local, local_to_wc = 0, 0
    headers = _auth()

    if headers:
        page = 1
        while True:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(f'{WC_URL}/wp-json/wc/v3/products', headers=headers,
                                           params={'per_page': 100, 'page': page})
                    if resp.status_code != 200:
                        break
                    products = resp.json()
                    if not products:
                        break
                    for p in products:
                        await db.woo_inventory.update_one({'wc_id': p['id']}, {'$set': {
                            'wc_id': p['id'],
                            'name': p.get('name', ''),
                            'stock': p.get('stock_quantity', 0),
                            'price': p.get('price', '0'),
                            'sku': p.get('sku', ''),
                            'updated_at': _now(),
                        }}, upsert=True)
                        wc_to_local += 1
                    if len(products) < 100:
                        break
                    page += 1
            except Exception:
                break

    local_products = await db.products.find({}, {'_id': 0}).to_list(5000)
    if headers:
        for lp in local_products:
            sku = lp.get('sku', '')
            if not sku:
                continue
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(f'{WC_URL}/wp-json/wc/v3/products', headers=headers,
                                           params={'sku': sku})
                    if resp.status_code == 200:
                        wc_products = resp.json()
                        if wc_products:
                            wc_pid = wc_products[0]['id']
                            new_stock = lp.get('stock', 0)
                            await client.put(f'{WC_URL}/wp-json/wc/v3/products/{wc_pid}', headers=headers, json={
                                'stock_quantity': new_stock,
                                'manage_stock': True,
                                'stock_status': 'instock' if new_stock > 0 else 'outofstock',
                            })
                            local_to_wc += 1
            except Exception:
                continue

    await db.woo_sync_logs.insert_one({
        'id': _uid(), 'action': 'inventory_sync', 'status': 'completed',
        'details': {'wc_to_local': wc_to_local, 'local_to_wc': local_to_wc},
        'timestamp': _now(),
    })
    return {'wc_to_local': wc_to_local, 'local_to_wc': local_to_wc}


@router.post('/inventory/{product_id}/adjust')
async def adjust_inventory(product_id: int, body: InventoryAdjustIn, _=Depends(get_current_admin)):
    headers = _auth()
    if not headers:
        raise HTTPException(400, 'WC not configured')
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.put(f'{WC_URL}/wp-json/wc/v3/products/{product_id}', headers=headers, json={
            'stock_quantity': body.stock_quantity,
            'manage_stock': True,
            'stock_status': body.stock_status or ('instock' if body.stock_quantity > 0 else 'outofstock'),
        })
        if resp.status_code != 200:
            raise HTTPException(502, f'WC returned {resp.status_code}')
        data = resp.json()
        await db.woo_inventory.update_one({'wc_id': product_id}, {'$set': {
            'stock': body.stock_quantity,
            'stock_status': body.stock_status or ('instock' if body.stock_quantity > 0 else 'outofstock'),
            'updated_at': _now(),
        }}, upsert=True)
        return {'product_id': product_id, 'stock_quantity': body.stock_quantity, 'updated': True}


# ── Customers ──

@router.get('/customers')
async def list_wc_customers(page: int = 1, per_page: int = 20, _=Depends(get_current_admin)):
    headers = _auth()
    if not headers:
        raise HTTPException(400, 'WC not configured')
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f'{WC_URL}/wp-json/wc/v3/customers', headers=headers,
                               params={'page': page, 'per_page': per_page})
        if resp.status_code != 200:
            raise HTTPException(502, f'WC returned {resp.status_code}')
        return {
            'customers': resp.json(),
            'total': int(resp.headers.get('X-WP-Total', 0)),
            'pages': int(resp.headers.get('X-WP-TotalPages', 0)),
        }


@router.post('/customers/sync')
async def sync_customers(_=Depends(get_current_admin)):
    synced = 0
    headers = _auth()
    if not headers:
        raise HTTPException(400, 'WC not configured')
    page = 1
    while True:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f'{WC_URL}/wp-json/wc/v3/customers', headers=headers,
                                   params={'page': page, 'per_page': 100})
            if resp.status_code != 200:
                break
            customers = resp.json()
            if not customers:
                break
            for c in customers:
                await db.woo_customers.update_one({'wc_id': c['id']}, {'$set': {
                    'wc_id': c['id'],
                    'email': c.get('email', ''),
                    'first_name': c.get('first_name', ''),
                    'last_name': c.get('last_name', ''),
                    'username': c.get('username', ''),
                    'role': c.get('role', ''),
                    'billing': c.get('billing', {}),
                    'shipping': c.get('shipping', {}),
                    'orders_count': c.get('orders_count', 0),
                    'total_spent': c.get('total_spent', '0'),
                    'avatar_url': c.get('avatar_url', ''),
                    'synced_at': _now(),
                }}, upsert=True)
                synced += 1
            if len(customers) < 100:
                break
            page += 1

    await db.woo_sync_logs.insert_one({
        'id': _uid(), 'action': 'customers_sync', 'status': 'completed',
        'details': {'synced': synced},
        'timestamp': _now(),
    })
    return {'synced': synced}


# ── Coupons ──

@router.get('/coupons')
async def list_wc_coupons(page: int = 1, per_page: int = 20, _=Depends(get_current_admin)):
    headers = _auth()
    if not headers:
        raise HTTPException(400, 'WC not configured')
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f'{WC_URL}/wp-json/wc/v3/coupons', headers=headers,
                               params={'page': page, 'per_page': per_page})
        if resp.status_code != 200:
            raise HTTPException(502, f'WC returned {resp.status_code}')
        return {
            'coupons': resp.json(),
            'total': int(resp.headers.get('X-WP-Total', 0)),
            'pages': int(resp.headers.get('X-WP-TotalPages', 0)),
        }


@router.post('/coupons/sync')
async def sync_coupons(_=Depends(get_current_admin)):
    synced = 0
    headers = _auth()
    if not headers:
        raise HTTPException(400, 'WC not configured')
    page = 1
    while True:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f'{WC_URL}/wp-json/wc/v3/coupons', headers=headers,
                                   params={'page': page, 'per_page': 100})
            if resp.status_code != 200:
                break
            coupons = resp.json()
            if not coupons:
                break
            for c in coupons:
                await db.woo_coupons.update_one({'wc_id': c['id']}, {'$set': {
                    'wc_id': c['id'],
                    'code': c.get('code', ''),
                    'discount_type': c.get('discount_type', ''),
                    'amount': c.get('amount', ''),
                    'individual_use': c.get('individual_use', False),
                    'usage_limit': c.get('usage_limit'),
                    'usage_limit_per_user': c.get('usage_limit_per_user'),
                    'minimum_amount': c.get('minimum_amount', ''),
                    'maximum_amount': c.get('maximum_amount', ''),
                    'date_expires': c.get('date_expires'),
                    'meta_data': c.get('meta_data', []),
                    'synced_at': _now(),
                }}, upsert=True)
                synced += 1
            if len(coupons) < 100:
                break
            page += 1

    await db.woo_sync_logs.insert_one({
        'id': _uid(), 'action': 'coupons_sync', 'status': 'completed',
        'details': {'synced': synced},
        'timestamp': _now(),
    })
    return {'synced': synced}


# ── Webhooks ──

@router.post('/webhooks')
async def register_webhook(body: WebhookRegisterIn, _=Depends(get_current_admin)):
    headers = _auth()
    if not headers:
        raise HTTPException(400, 'WC not configured')
    secret = body.secret or uuid.uuid4().hex
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f'{WC_URL}/wp-json/wc/v3/webhooks', headers=headers, json={
            'name': body.name,
            'topic': body.topic,
            'delivery_url': body.delivery_url,
            'secret': secret,
            'status': 'active',
        })
        if resp.status_code not in (200, 201):
            raise HTTPException(502, f'WC returned {resp.status_code}')
        data = resp.json()
        await db.woo_webhooks.insert_one({
            'wc_id': data['id'], 'name': body.name, 'topic': body.topic,
            'delivery_url': body.delivery_url, 'secret': secret,
            'status': data.get('status', ''), 'created_at': _now(),
        })
        return data


@router.get('/webhooks')
async def list_webhooks(_=Depends(get_current_admin)):
    headers = _auth()
    if not headers:
        raise HTTPException(400, 'WC not configured')
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f'{WC_URL}/wp-json/wc/v3/webhooks', headers=headers, params={'per_page': 100})
        if resp.status_code != 200:
            raise HTTPException(502, f'WC returned {resp.status_code}')
        return resp.json()


@router.delete('/webhooks/{webhook_id}')
async def delete_webhook(webhook_id: int, _=Depends(get_current_admin)):
    headers = _auth()
    if not headers:
        raise HTTPException(400, 'WC not configured')
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.delete(f'{WC_URL}/wp-json/wc/v3/webhooks/{webhook_id}', headers=headers)
        if resp.status_code not in (200, 204):
            raise HTTPException(502, f'WC returned {resp.status_code}')
        await db.woo_webhooks.delete_one({'wc_id': webhook_id})
        return {'deleted': True, 'webhook_id': webhook_id}


# ── Logs ──

@router.get('/logs')
async def sync_logs(_=Depends(get_current_admin)):
    logs = await db.woo_sync_logs.find({}, {'_id': 0}).sort('timestamp', -1).limit(100).to_list(100)
    return logs


# ── Full Sync ──

@router.post('/full-sync')
async def full_sync(_=Depends(get_current_admin)):
    stats = {'products': {}, 'orders': {}, 'inventory': {}, 'customers': {}, 'coupons': {}}
    errors = []

    try:
        page = 1
        created, updated = 0, 0
        while True:
            result = await get_products(page=page, per_page=100)
            if 'error' in result:
                errors.append(f'products: {result["error"]}')
                break
            products = result['products']
            if not products:
                break
            for p in products:
                existing = await db.woo_products.find_one({'wc_id': p['id']})
                await db.woo_products.update_one({'wc_id': p['id']}, {'$set': {
                    'wc_id': p['id'], 'name': p.get('name', ''), 'slug': p.get('slug', ''),
                    'status': p.get('status', ''), 'price': p.get('price', ''),
                    'regular_price': p.get('regular_price', ''), 'sale_price': p.get('sale_price', ''),
                    'description': p.get('description', ''), 'short_description': p.get('short_description', ''),
                    'stock_quantity': p.get('stock_quantity'), 'stock_status': p.get('stock_status', ''),
                    'categories': [c.get('name', '') for c in p.get('categories', [])],
                    'images': [i.get('src', '') for i in p.get('images', [])],
                    'sku': p.get('sku', ''), 'weight': p.get('weight', ''),
                    'dimensions': p.get('dimensions', {}), 'attributes': p.get('attributes', []),
                    'synced_at': _now(),
                }}, upsert=True)
                if existing:
                    updated += 1
                else:
                    created += 1
            if len(products) < 100:
                break
            page += 1
        stats['products'] = {'created': created, 'updated': updated}
    except Exception as e:
        errors.append(f'products: {str(e)}')

    try:
        total_orders = 0
        for order_status in ['pending', 'processing', 'on-hold', 'completed', 'cancelled', 'refunded', 'failed']:
            page = 1
            while True:
                result = await get_orders(status=order_status, page=page, per_page=100)
                if 'error' in result:
                    break
                orders = result['orders']
                if not orders:
                    break
                for o in orders:
                    await db.woo_orders.update_one({'wc_id': o['id']}, {'$set': {
                        'wc_id': o['id'], 'number': o.get('number', ''), 'status': o.get('status', ''),
                        'total': o.get('total', '0'), 'currency': o.get('currency', ''),
                        'customer_id': o.get('customer_id', 0), 'billing': o.get('billing', {}),
                        'shipping': o.get('shipping', {}), 'line_items': o.get('line_items', []),
                        'payment_method': o.get('payment_method', ''),
                        'date_created': o.get('date_created', ''), 'synced_at': _now(),
                    }}, upsert=True)
                    total_orders += 1
                if len(orders) < 100:
                    break
                page += 1
        stats['orders'] = {'synced': total_orders}
    except Exception as e:
        errors.append(f'orders: {str(e)}')

    try:
        inv = await get_inventory()
        if 'items' in inv:
            for item in inv['items']:
                await db.woo_inventory.update_one({'wc_id': item['id']}, {'$set': {
                    'wc_id': item['id'], 'name': item['name'],
                    'stock': item['stock'], 'price': item['price'], 'updated_at': _now(),
                }}, upsert=True)
            stats['inventory'] = {'synced': len(inv['items'])}
        else:
            stats['inventory'] = {'error': inv.get('error', 'unknown')}
    except Exception as e:
        errors.append(f'inventory: {str(e)}')

    try:
        synced = 0
        headers = _auth()
        if headers:
            page = 1
            while True:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(f'{WC_URL}/wp-json/wc/v3/customers', headers=headers,
                                           params={'page': page, 'per_page': 100})
                    if resp.status_code != 200:
                        break
                    customers = resp.json()
                    if not customers:
                        break
                    for c in customers:
                        await db.woo_customers.update_one({'wc_id': c['id']}, {'$set': {
                            'wc_id': c['id'], 'email': c.get('email', ''),
                            'first_name': c.get('first_name', ''), 'last_name': c.get('last_name', ''),
                            'username': c.get('username', ''), 'role': c.get('role', ''),
                            'billing': c.get('billing', {}), 'shipping': c.get('shipping', {}),
                            'orders_count': c.get('orders_count', 0), 'total_spent': c.get('total_spent', '0'),
                            'synced_at': _now(),
                        }}, upsert=True)
                        synced += 1
                    if len(customers) < 100:
                        break
                    page += 1
        stats['customers'] = {'synced': synced}
    except Exception as e:
        errors.append(f'customers: {str(e)}')

    try:
        synced = 0
        headers = _auth()
        if headers:
            page = 1
            while True:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(f'{WC_URL}/wp-json/wc/v3/coupons', headers=headers,
                                           params={'page': page, 'per_page': 100})
                    if resp.status_code != 200:
                        break
                    coupons = resp.json()
                    if not coupons:
                        break
                    for c in coupons:
                        await db.woo_coupons.update_one({'wc_id': c['id']}, {'$set': {
                            'wc_id': c['id'], 'code': c.get('code', ''),
                            'discount_type': c.get('discount_type', ''), 'amount': c.get('amount', ''),
                            'individual_use': c.get('individual_use', False),
                            'usage_limit': c.get('usage_limit'), 'date_expires': c.get('date_expires'),
                            'synced_at': _now(),
                        }}, upsert=True)
                        synced += 1
                    if len(coupons) < 100:
                        break
                    page += 1
        stats['coupons'] = {'synced': synced}
    except Exception as e:
        errors.append(f'coupons: {str(e)}')

    await db.woo_sync_logs.insert_one({
        'id': _uid(), 'action': 'full_sync', 'status': 'completed' if not errors else 'partial',
        'details': {'stats': stats, 'errors': errors},
        'timestamp': _now(),
    })
    return {'stats': stats, 'errors': errors, 'completed_at': _now()}
