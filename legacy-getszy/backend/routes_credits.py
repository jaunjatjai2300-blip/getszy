"""Credit balance + admin manual-grant routes.

Manual grant exists so the founder can hand out credits to test users BEFORE
Razorpay/Stripe is wired up. Once payments go live, the payment webhook will
call `credits.add_credits()` the same way this endpoint does.
"""
from fastapi import APIRouter, Depends, HTTPException
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
