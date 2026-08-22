"""Credit balance + admin manual-grant routes.

Manual grant exists so the founder can hand out credits to test users BEFORE
Razorpay/Stripe is wired up. Once payments go live, the payment webhook will
call `credits.add_credits()` the same way this endpoint does.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth import get_current_user, get_current_admin
from db import db
from credits import CREDIT_COSTS, get_balance, add_credits

router = APIRouter(prefix='/credits', tags=['credits'])


@router.get('/me')
async def my_credits(user=Depends(get_current_user)):
    balance = await get_balance(user['id'])
    return {'credits': balance, 'costs': CREDIT_COSTS}


@router.get('/costs')
async def costs(_=Depends(get_current_user)):
    return {'costs': CREDIT_COSTS}


@router.get('/me/transactions')
async def my_credit_transactions(
    limit: int = Query(default=20, ge=1, le=100),
    user=Depends(get_current_user),
):
    """Return only the current customer's audited credit activity, newest first."""
    cursor = db.credit_transactions.find(
        {'user_id': user['id']},
        {'_id': 0, 'user_id': 0},
    ).sort('created_at', -1).limit(limit)
    items = []
    async for item in cursor:
        meta = item.get('meta') if isinstance(item.get('meta'), dict) else {}
        items.append({
            'id': item.get('id') or item.get('ref_id') or f"{item.get('created_at', '')}:{item.get('action', '')}",
            'type': item.get('type'),
            'action': item.get('action'),
            'qty': item.get('qty'),
            'amount': item.get('amount'),
            'balance_after': item.get('balance_after'),
            'reason': meta.get('reason'),
            'created_at': item.get('created_at'),
        })
    return {'items': items}


class AdminGrantIn(BaseModel):
    email: str
    amount: int = Field(..., gt=0)
    reason: str = 'manual_grant'


@router.post('/admin/grant')
async def admin_grant(body: AdminGrantIn, admin=Depends(get_current_admin)):
    target = await db.users.find_one({'email': body.email.lower()}, {'_id': 0})
    if not target:
        raise HTTPException(404, 'User not found')
    balance = await add_credits(target['id'], body.amount, body.reason, meta={'granted_by': admin['id']})
    return {'ok': True, 'user_id': target['id'], 'email': target['email'], 'credits': balance}


@router.get('/admin/transactions/{user_email}')
async def admin_transactions(user_email: str, limit: int = 50, admin=Depends(get_current_admin)):
    target = await db.users.find_one({'email': user_email.lower()}, {'_id': 0})
    if not target:
        raise HTTPException(404, 'User not found')
    cur = db.credit_transactions.find({'user_id': target['id']}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'items': [doc async for doc in cur]}


@router.get('/admin/transactions')
async def admin_transactions_all(limit: int = 100, admin=Depends(get_current_admin)):
    """All credit transactions across users (newest first)."""
    cur = db.credit_transactions.find({}, {'_id': 0}).sort('created_at', -1).limit(limit)
    items = []
    async for d in cur:
        meta = d.get('meta') or {}
        items.append({
            'id': d.get('id') or str(d.get('_id')),
            'user_id': d.get('user_id'),
            'created_at': d.get('created_at'),
            'delta': d.get('amount'),
            'value': d.get('amount'),
            'reason': meta.get('reason') if isinstance(meta, dict) else d.get('reason'),
            'success': d.get('success', True),
            'error': d.get('error'),
        })
    return {'items': items}
