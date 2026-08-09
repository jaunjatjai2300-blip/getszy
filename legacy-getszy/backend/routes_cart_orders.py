from fastapi import APIRouter, HTTPException, Depends
from db import db
from models import CartItem, Order, OrderItem, CheckoutIn, OrderStatusUpdate
from auth import get_current_user, get_current_admin
from datetime import datetime, timezone
import uuid

router = APIRouter(tags=['cart-orders'])


async def _get_or_create_cart(user_id: str):
    cart = await db.carts.find_one({'user_id': user_id}, {'_id': 0})
    if not cart:
        cart = {'user_id': user_id, 'items': [], 'updated_at': datetime.now(timezone.utc).isoformat()}
        await db.carts.insert_one(cart.copy())
    return cart


@router.get('/cart')
async def get_cart(user=Depends(get_current_user)):
    cart = await _get_or_create_cart(user['id'])
    items = cart.get('items', [])
    if not items:
        return {'items': [], 'total': 0, 'count': 0}
    # Bulk fetch all products in one query (fixes N+1)
    product_ids = [it['product_id'] for it in items]
    products = await db.products.find({'id': {'$in': product_ids}}, {'_id': 0, 'cost_price': 0}).to_list(len(product_ids))
    product_map = {p['id']: p for p in products}
    enriched = []
    total = 0
    for item in items:
        p = product_map.get(item['product_id'])
        if p:
            line_total = p['price'] * item['quantity']
            total += line_total
            enriched.append({**item, 'product': p, 'line_total': line_total})
    return {'items': enriched, 'total': total, 'count': sum(i['quantity'] for i in items)}


@router.post('/cart/add')
async def add_to_cart(body: CartItem, user=Depends(get_current_user)):
    cart = await _get_or_create_cart(user['id'])
    items = cart.get('items', [])
    found = False
    for it in items:
        if it['product_id'] == body.product_id:
            it['quantity'] += body.quantity
            found = True
            break
    if not found:
        items.append(body.model_dump())
    await db.carts.update_one({'user_id': user['id']}, {'$set': {'items': items, 'updated_at': datetime.now(timezone.utc).isoformat()}})
    return {'ok': True}


@router.post('/cart/update')
async def update_cart(body: CartItem, user=Depends(get_current_user)):
    cart = await _get_or_create_cart(user['id'])
    items = cart.get('items', [])
    if body.quantity <= 0:
        items = [it for it in items if it['product_id'] != body.product_id]
    else:
        found = False
        for it in items:
            if it['product_id'] == body.product_id:
                it['quantity'] = body.quantity
                found = True
                break
        if not found:
            items.append(body.model_dump())
    await db.carts.update_one({'user_id': user['id']}, {'$set': {'items': items}})
    return {'ok': True}


@router.post('/cart/clear')
async def clear_cart(user=Depends(get_current_user)):
    await db.carts.update_one({'user_id': user['id']}, {'$set': {'items': []}})
    return {'ok': True}


async def _next_order_number():
    """Atomic order number generation using MongoDB findAndModify."""
    counter = await db.counters.find_one_and_update(
        {'_id': 'order_number'},
        {'$inc': {'seq': 1}},
        upsert=True,
        return_document=True,
    )
    return f'ORD{1000 + counter["seq"]}'


@router.post('/orders/checkout')
async def checkout(body: CheckoutIn, user=Depends(get_current_user)):
    cart = await _get_or_create_cart(user['id'])
    if not cart.get('items'):
        raise HTTPException(400, 'Cart is empty')
    # Bulk fetch all products in one query (fixes N+1)
    product_ids = [it['product_id'] for it in cart['items']]
    products = await db.products.find({'id': {'$in': product_ids}}, {'_id': 0}).to_list(len(product_ids))
    product_map = {p['id']: p for p in products}
    items_out = []
    subtotal = 0
    cost_total = 0
    for it in cart['items']:
        p = product_map.get(it['product_id'])
        if not p:
            continue
        line = p['price'] * it['quantity']
        cost = (p.get('cost_price', 0) or 0) * it['quantity']
        subtotal += line
        cost_total += cost
        items_out.append(OrderItem(
            product_id=p['id'],
            name=p['name'],
            image=(p.get('images') or [None])[0],
            price=p['price'],
            cost_price=p.get('cost_price', 0) or 0,
            quantity=it['quantity'],
            supplier=p.get('supplier'),
        ))
    if not items_out:
        raise HTTPException(400, 'No valid products in cart')
    shipping = 0.0 if subtotal >= 999 else 49.0
    total = subtotal + shipping
    order = Order(
        order_number=await _next_order_number(),
        user_id=user['id'],
        customer_name=user['name'],
        customer_email=user['email'],
        items=items_out,
        subtotal=subtotal,
        shipping_fee=shipping,
        total=total,
        cost_total=cost_total,
        profit=total - cost_total - shipping,
        address=body.address,
        notes=body.notes,
    )
    await db.orders.insert_one(order.model_dump())
    await db.carts.update_one({'user_id': user['id']}, {'$set': {'items': []}})
    return order.model_dump()


@router.get('/orders/mine')
async def my_orders(user=Depends(get_current_user)):
    return await db.orders.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).to_list(100)


@router.get('/admin/orders', dependencies=[Depends(get_current_admin)])
async def all_orders():
    return await db.orders.find({}, {'_id': 0}).sort('created_at', -1).to_list(500)


@router.put('/admin/orders/{order_id}/status', dependencies=[Depends(get_current_admin)])
async def update_status(order_id: str, body: OrderStatusUpdate):
    updates = {'status': body.status}
    if body.tracking_number:
        updates['tracking_number'] = body.tracking_number
    res = await db.orders.update_one({'$or': [{'id': order_id}, {'order_number': order_id}]}, {'$set': updates})
    if res.matched_count == 0:
        raise HTTPException(404, 'Order not found')
    return await db.orders.find_one({'$or': [{'id': order_id}, {'order_number': order_id}]}, {'_id': 0})
