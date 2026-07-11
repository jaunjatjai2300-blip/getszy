"""Commerce Extra — Coupons, Invoices, Refunds, GST, Affiliates, Reviews, Memberships."""
import uuid, io
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import get_current_admin, get_current_user
from db import db

router = APIRouter(tags=['commerce-extra'])

def _iso():
    return datetime.now(timezone.utc).isoformat()
def _id():
    return str(uuid.uuid4())[:12]

# ══════════════════════════ COUPONS ══════════════════════════

class CouponIn(BaseModel):
    code: str
    discount_type: str = "percent"  # percent / fixed
    value: float
    min_order: float = 0
    max_uses: int = 0  # 0 = unlimited
    expires_at: Optional[str] = None
    description: str = ""

@router.get('/admin/coupons', dependencies=[Depends(get_current_admin)])
async def list_coupons():
    items = [c async for c in db.gs_coupons.find({}, {'_id': 0}).sort('created_at', -1)]
    return {'items': items}

@router.post('/admin/coupons', dependencies=[Depends(get_current_admin)])
async def create_coupon(body: CouponIn):
    existing = await db.gs_coupons.find_one({'code': body.code.upper()})
    if existing:
        raise HTTPException(400, f'Coupon code "{body.code}" pehle se exist karta hai')
    doc = {'id': _id(), 'code': body.code.upper(), 'discount_type': body.discount_type,
           'value': body.value, 'min_order': body.min_order, 'max_uses': body.max_uses,
           'uses': 0, 'expires_at': body.expires_at, 'description': body.description,
           'active': True, 'created_at': _iso()}
    await db.gs_coupons.insert_one(doc)
    return doc

@router.put('/admin/coupons/{cid}', dependencies=[Depends(get_current_admin)])
async def update_coupon(cid: str, body: dict):
    await db.gs_coupons.update_one({'id': cid}, {'$set': body})
    return {'ok': True}

@router.delete('/admin/coupons/{cid}', dependencies=[Depends(get_current_admin)])
async def delete_coupon(cid: str):
    await db.gs_coupons.delete_one({'id': cid})
    return {'ok': True}

@router.post('/coupons/validate')
async def validate_coupon(body: dict, user=Depends(get_current_user)):
    code = (body.get('code') or '').upper()
    order_total = body.get('order_total', 0)
    c = await db.gs_coupons.find_one({'code': code, 'active': True}, {'_id': 0})
    if not c:
        raise HTTPException(404, 'Coupon nahi mila ya inactive hai')
    if c.get('expires_at') and c['expires_at'] < _iso():
        raise HTTPException(400, 'Coupon expire ho gaya')
    if c.get('max_uses') and c.get('uses', 0) >= c['max_uses']:
        raise HTTPException(400, 'Coupon ki limit khatam ho gayi')
    if order_total < c.get('min_order', 0):
        raise HTTPException(400, f'Minimum order ₹{c["min_order"]} chahiye')
    discount = (order_total * c['value'] / 100) if c['discount_type'] == 'percent' else c['value']
    discount = min(discount, order_total)
    return {'valid': True, 'discount': round(discount, 2), 'coupon': c}

# ══════════════════════════ INVOICES ══════════════════════════

@router.get('/admin/invoices', dependencies=[Depends(get_current_admin)])
async def list_invoices(page: int = 1, limit: int = 20):
    skip = (page - 1) * limit
    items = [i async for i in db.gs_invoices.find({}, {'_id': 0}).sort('created_at', -1).skip(skip).limit(limit)]
    total = await db.gs_invoices.count_documents({})
    return {'items': items, 'total': total, 'page': page}

@router.post('/admin/invoices/generate', dependencies=[Depends(get_current_admin)])
async def generate_invoice(body: dict):
    order_id = body.get('order_id')
    order = await db.orders.find_one({'id': order_id}, {'_id': 0}) if order_id else None
    inv_number = f"GST-{datetime.now().strftime('%Y%m')}-{_id().upper()}"
    subtotal = body.get('subtotal', order.get('total', 0) if order else 0)
    gst_rate = body.get('gst_rate', 18)
    gst_amount = round(subtotal * gst_rate / 100, 2)
    total = subtotal + gst_amount
    doc = {
        'id': _id(), 'invoice_number': inv_number, 'order_id': order_id,
        'customer_name': body.get('customer_name', order.get('customer_name', '') if order else ''),
        'customer_email': body.get('customer_email', ''),
        'customer_gstin': body.get('customer_gstin', ''),
        'items': body.get('items', order.get('items', []) if order else []),
        'subtotal': subtotal, 'gst_rate': gst_rate, 'gst_amount': gst_amount,
        'total': total, 'status': 'issued', 'created_at': _iso(),
        'due_date': body.get('due_date', ''), 'notes': body.get('notes', ''),
    }
    await db.gs_invoices.insert_one(doc)
    return doc

@router.get('/admin/invoices/{iid}', dependencies=[Depends(get_current_admin)])
async def get_invoice(iid: str):
    inv = await db.gs_invoices.find_one({'id': iid}, {'_id': 0})
    if not inv:
        raise HTTPException(404, 'Invoice nahi mila')
    return inv

@router.put('/admin/invoices/{iid}', dependencies=[Depends(get_current_admin)])
async def update_invoice(iid: str, body: dict):
    await db.gs_invoices.update_one({'id': iid}, {'$set': body})
    return {'ok': True}

# ══════════════════════════ REFUNDS ══════════════════════════

class RefundIn(BaseModel):
    order_id: str
    amount: float
    reason: str
    refund_method: str = "original"  # original / wallet / bank

@router.get('/admin/refunds', dependencies=[Depends(get_current_admin)])
async def list_refunds():
    items = [r async for r in db.gs_refunds.find({}, {'_id': 0}).sort('created_at', -1)]
    return {'items': items}

@router.post('/admin/refunds', dependencies=[Depends(get_current_admin)])
async def create_refund(body: RefundIn):
    order = await db.orders.find_one({'id': body.order_id}, {'_id': 0})
    doc = {
        'id': _id(), 'order_id': body.order_id, 'amount': body.amount,
        'reason': body.reason, 'refund_method': body.refund_method,
        'status': 'pending', 'created_at': _iso(),
        'customer_name': order.get('customer_name', '') if order else '',
        'order_total': order.get('total', 0) if order else 0,
    }
    await db.gs_refunds.insert_one(doc)
    return doc

@router.put('/admin/refunds/{rid}', dependencies=[Depends(get_current_admin)])
async def update_refund(rid: str, body: dict):
    r = await db.gs_refunds.find_one({'id': rid})
    if not r:
        raise HTTPException(404, 'Refund nahi mila')
    body['updated_at'] = _iso()
    if body.get('status') == 'approved' and r.get('order_id'):
        await db.orders.update_one({'id': r['order_id']}, {'$set': {'status': 'refunded'}})
    await db.gs_refunds.update_one({'id': rid}, {'$set': body})
    return {'ok': True}

# ══════════════════════════ GST CONFIG ══════════════════════════

@router.get('/admin/gst-config', dependencies=[Depends(get_current_admin)])
async def get_gst_config():
    cfg = await db.gs_gst_config.find_one({}, {'_id': 0})
    if not cfg:
        cfg = {'gst_enabled': True, 'default_rate': 18, 'included_in_price': False,
               'cgst_rate': 9, 'sgst_rate': 9, 'igst_rate': 18,
               'company_gstin': '', 'company_name': 'Getszy', 'company_address': '',
               'hsn_code_digital': '998431', 'hsn_code_physical': ''}
    return cfg

@router.put('/admin/gst-config', dependencies=[Depends(get_current_admin)])
async def update_gst_config(body: dict):
    body['updated_at'] = _iso()
    await db.gs_gst_config.replace_one({}, body, upsert=True)
    return {'ok': True}

# ══════════════════════════ AFFILIATES ══════════════════════════

class AffiliateIn(BaseModel):
    name: str
    email: str
    commission_rate: float = 10.0  # percent

@router.get('/admin/affiliates', dependencies=[Depends(get_current_admin)])
async def list_affiliates():
    items = [a async for a in db.gs_affiliates.find({}, {'_id': 0}).sort('created_at', -1)]
    return {'items': items}

@router.post('/admin/affiliates', dependencies=[Depends(get_current_admin)])
async def create_affiliate(body: AffiliateIn):
    code = f"REF{body.name[:3].upper()}{_id()[:4].upper()}"
    doc = {
        'id': _id(), 'name': body.name, 'email': body.email,
        'code': code, 'commission_rate': body.commission_rate,
        'clicks': 0, 'conversions': 0, 'earnings': 0.0,
        'status': 'active', 'created_at': _iso(),
    }
    await db.gs_affiliates.insert_one(doc)
    return doc

@router.put('/admin/affiliates/{aid}', dependencies=[Depends(get_current_admin)])
async def update_affiliate(aid: str, body: dict):
    await db.gs_affiliates.update_one({'id': aid}, {'$set': body})
    return {'ok': True}

@router.delete('/admin/affiliates/{aid}', dependencies=[Depends(get_current_admin)])
async def delete_affiliate(aid: str):
    await db.gs_affiliates.delete_one({'id': aid})
    return {'ok': True}

@router.post('/affiliates/track')
async def track_affiliate(body: dict):
    code = body.get('code', '')
    event = body.get('event', 'click')
    field = 'clicks' if event == 'click' else 'conversions'
    await db.gs_affiliates.update_one({'code': code}, {'$inc': {field: 1}})
    return {'ok': True}

# ══════════════════════════ REVIEWS ══════════════════════════

class ReviewIn(BaseModel):
    product_id: str
    rating: int  # 1-5
    comment: str = ""
    title: str = ""

@router.get('/admin/reviews', dependencies=[Depends(get_current_admin)])
async def list_reviews(status: str = "all"):
    q = {} if status == "all" else {'status': status}
    items = [r async for r in db.gs_reviews.find(q, {'_id': 0}).sort('created_at', -1)]
    return {'items': items}

@router.post('/reviews')
async def submit_review(body: ReviewIn, user=Depends(get_current_user)):
    existing = await db.gs_reviews.find_one({'product_id': body.product_id, 'user_id': user['id']})
    if existing:
        raise HTTPException(400, 'Aapne is product ka review pehle se diya hai')
    if not 1 <= body.rating <= 5:
        raise HTTPException(400, 'Rating 1-5 ke beech honi chahiye')
    doc = {
        'id': _id(), 'product_id': body.product_id, 'user_id': user['id'],
        'user_name': user.get('name', 'Customer'), 'rating': body.rating,
        'comment': body.comment, 'title': body.title,
        'status': 'pending', 'created_at': _iso(),
    }
    await db.gs_reviews.insert_one(doc)
    return {'ok': True, 'message': 'Review submit ho gaya, approval pending hai'}

@router.get('/reviews/product/{product_id}')
async def product_reviews(product_id: str):
    items = [r async for r in db.gs_reviews.find({'product_id': product_id, 'status': 'approved'}, {'_id': 0})]
    avg = sum(r['rating'] for r in items) / len(items) if items else 0
    return {'items': items, 'average_rating': round(avg, 1), 'count': len(items)}

@router.put('/admin/reviews/{rid}', dependencies=[Depends(get_current_admin)])
async def moderate_review(rid: str, body: dict):
    await db.gs_reviews.update_one({'id': rid}, {'$set': {**body, 'moderated_at': _iso()}})
    if body.get('status') == 'approved':
        r = await db.gs_reviews.find_one({'id': rid})
        if r:
            all_reviews = [x async for x in db.gs_reviews.find({'product_id': r['product_id'], 'status': 'approved'})]
            if all_reviews:
                avg = sum(x['rating'] for x in all_reviews) / len(all_reviews)
                await db.products.update_one({'id': r['product_id']}, {'$set': {'avg_rating': round(avg, 1), 'review_count': len(all_reviews)}})
    return {'ok': True}

@router.delete('/admin/reviews/{rid}', dependencies=[Depends(get_current_admin)])
async def delete_review(rid: str):
    await db.gs_reviews.delete_one({'id': rid})
    return {'ok': True}

# ══════════════════════════ MEMBERSHIPS ══════════════════════════

class MembershipIn(BaseModel):
    name: str
    price_monthly: float
    price_yearly: float = 0
    description: str = ""
    features: list = []
    color: str = "#6366f1"
    badge: str = ""

@router.get('/admin/memberships', dependencies=[Depends(get_current_admin)])
async def list_memberships():
    items = [m async for m in db.gs_memberships.find({}, {'_id': 0}).sort('price_monthly', 1)]
    return {'items': items}

@router.post('/admin/memberships', dependencies=[Depends(get_current_admin)])
async def create_membership(body: MembershipIn):
    doc = {
        'id': _id(), 'name': body.name, 'price_monthly': body.price_monthly,
        'price_yearly': body.price_yearly or body.price_monthly * 10,
        'description': body.description, 'features': body.features,
        'color': body.color, 'badge': body.badge,
        'active': True, 'member_count': 0, 'created_at': _iso(),
    }
    await db.gs_memberships.insert_one(doc)
    return doc

@router.put('/admin/memberships/{mid}', dependencies=[Depends(get_current_admin)])
async def update_membership(mid: str, body: dict):
    await db.gs_memberships.update_one({'id': mid}, {'$set': body})
    return {'ok': True}

@router.delete('/admin/memberships/{mid}', dependencies=[Depends(get_current_admin)])
async def delete_membership(mid: str):
    await db.gs_memberships.delete_one({'id': mid})
    return {'ok': True}

@router.get('/memberships')
async def public_memberships():
    items = [m async for m in db.gs_memberships.find({'active': True}, {'_id': 0}).sort('price_monthly', 1)]
    return {'items': items}
