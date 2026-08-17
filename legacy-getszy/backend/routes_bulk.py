"""Bulk operations API (Tier 2 #12).

Admin batch actions over orders and users — status changes, refunds,
role changes, ban/unban. Each action is audited.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_admin
from db import db

router = APIRouter(prefix='/admin/bulk', tags=['bulk'])

ALLOWED_ORDER_STATUS = {'pending', 'confirmed', 'shipped', 'delivered', 'cancelled', 'refunded'}
ALLOWED_ROLES = {'user', 'admin', 'moderator', 'support'}


class OrderStatusBulk(BaseModel):
    ids: List[str]
    status: str


class RefundBulk(BaseModel):
    ids: List[str]
    reason: str = "Bulk refund"


class UserRoleBulk(BaseModel):
    ids: List[str]
    role: str


class BanBulk(BaseModel):
    ids: List[str]
    banned: bool = True


def _now():
    return datetime.now(timezone.utc).isoformat()


@router.post('/orders/status')
async def bulk_order_status(body: OrderStatusBulk, _=Depends(get_current_admin)):
    if body.status not in ALLOWED_ORDER_STATUS:
        raise HTTPException(400, f"Invalid status '{body.status}'")
    res = await db.orders.update_many({'id': {'$in': body.ids}}, {'$set': {'status': body.status, 'updated_at': _now()}})
    await db.audit_logs.insert_one({
        'id': uuid.uuid4().hex, 'action': 'bulk_order_status', 'count': res.matched_count,
        'status': body.status, 'ts': _now(), 'source': 'bulk',
    })
    return {'ok': True, 'matched': res.matched_count}


@router.post('/orders/refund')
async def bulk_order_refund(body: RefundBulk, admin=Depends(get_current_admin)):
    refunded = 0
    for oid in body.ids:
        order = await db.orders.find_one({'id': oid}, {'_id': 0})
        if not order:
            continue
        await db.orders.update_one({'id': oid}, {'$set': {'status': 'refunded', 'updated_at': _now()}})
        refund = {
            'id': uuid.uuid4().hex, 'order_id': oid, 'order_number': order.get('order_number'),
            'amount': order.get('total', 0), 'reason': body.reason, 'method': 'bulk',
            'admin': admin.get('email'), 'created_at': _now(),
        }
        await db.refunds.insert_one(refund)
        refunded += 1
    await db.audit_logs.insert_one({
        'id': uuid.uuid4().hex, 'action': 'bulk_refund', 'count': refunded,
        'reason': body.reason, 'ts': _now(), 'source': 'bulk',
    })
    return {'ok': True, 'refunded': refunded}


@router.post('/users/role')
async def bulk_user_role(body: UserRoleBulk, _=Depends(get_current_admin)):
    if body.role not in ALLOWED_ROLES:
        raise HTTPException(400, f"Invalid role '{body.role}'")
    res = await db.users.update_many({'id': {'$in': body.ids}}, {'$set': {'role': body.role}})
    await db.audit_logs.insert_one({
        'id': uuid.uuid4().hex, 'action': 'bulk_user_role', 'count': res.matched_count,
        'role': body.role, 'ts': _now(), 'source': 'bulk',
    })
    return {'ok': True, 'matched': res.matched_count}


@router.post('/users/ban')
async def bulk_user_ban(body: BanBulk, _=Depends(get_current_admin)):
    res = await db.users.update_many({'id': {'$in': body.ids}}, {'$set': {'banned': body.banned}})
    await db.audit_logs.insert_one({
        'id': uuid.uuid4().hex, 'action': 'bulk_user_ban', 'count': res.matched_count,
        'banned': body.banned, 'ts': _now(), 'source': 'bulk',
    })
    return {'ok': True, 'matched': res.matched_count}
