"""Razorpay integration — Subscriptions only (monthly).

Design:
- Works in UNCONFIGURED mode when RAZORPAY_KEY_ID / SECRET / WEBHOOK_SECRET are missing.
  All endpoints return `{ configured: False, ... }` so frontend can render a graceful
  "Coming soon" state. When keys are added and backend restarted, endpoints activate.

- Uses Razorpay Subscriptions API (monthly interval).
- Plans (Razorpay plan_ids) can be created either via the Razorpay dashboard
  and set via env `RAZORPAY_PLAN_PRO` / `RAZORPAY_PLAN_ELITE`, OR auto-created via
  `POST /billing/admin/create-plans` (admin-only) once the user decides the ₹price.

Env vars:
  RAZORPAY_KEY_ID
  RAZORPAY_KEY_SECRET
  RAZORPAY_WEBHOOK_SECRET
  RAZORPAY_PLAN_PRO         (optional, "plan_..." id from Razorpay)
  RAZORPAY_PLAN_ELITE       (optional)
"""
import os
import uuid
import hmac
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from auth import get_current_user, get_current_admin
from db import db
from subscription import PLAN_FREE, PLAN_PRO, PLAN_ELITE, PRICING, grant_plan, cancel_subscription, effective_subscription

logger = logging.getLogger('getszy.billing')
router = APIRouter(prefix='/billing', tags=['billing'])

KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '').strip()
KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '').strip()
WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '').strip()
PLAN_PRO_ID = os.environ.get('RAZORPAY_PLAN_PRO', '').strip()
PLAN_ELITE_ID = os.environ.get('RAZORPAY_PLAN_ELITE', '').strip()


def _is_configured() -> bool:
    return bool(KEY_ID and KEY_SECRET)


def _client():
    if not _is_configured():
        return None
    import razorpay  # lazy import so unconfigured mode doesn't require import
    return razorpay.Client(auth=(KEY_ID, KEY_SECRET))


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _plan_id_for(plan: str) -> Optional[str]:
    if plan == PLAN_PRO:
        return PLAN_PRO_ID or None
    if plan == PLAN_ELITE:
        return PLAN_ELITE_ID or None
    return None


# ---------- Status ----------
@router.get('/status')
async def status(user=Depends(get_current_user)):
    sub = await effective_subscription(user)
    return {
        'configured': _is_configured(),
        'webhook_configured': bool(WEBHOOK_SECRET),
        'plans_configured': {
            'pro': bool(PLAN_PRO_ID),
            'elite': bool(PLAN_ELITE_ID),
        },
        'key_id_preview': (KEY_ID[:8] + '…') if KEY_ID else '',
        'current': sub,
        'pricing': PRICING,
    }


# ---------- Public pricing (no auth) ----------
@router.get('/pricing')
async def pricing_public():
    return {'plans': PRICING, 'currency': 'INR', 'interval': 'monthly'}


# ---------- Create Subscription ----------
class SubscribeIn(BaseModel):
    plan: str  # 'pro' | 'elite'


@router.post('/subscribe')
async def subscribe(body: SubscribeIn, user=Depends(get_current_user)):
    if body.plan not in (PLAN_PRO, PLAN_ELITE):
        raise HTTPException(400, 'Invalid plan')
    if not _is_configured():
        return {
            'configured': False,
            'message': 'Razorpay not configured. Payments will activate once RAZORPAY_KEY_ID / SECRET are set.',
            'plan': body.plan,
        }
    plan_id = _plan_id_for(body.plan)
    if not plan_id:
        raise HTTPException(400, f'Razorpay plan for {body.plan} not configured. Admin must run POST /api/billing/admin/create-plans first.')

    client = _client()
    try:
        sub = client.subscription.create({
            'plan_id': plan_id,
            'total_count': 120,  # 10 years worth of monthly billings (subscriber can cancel any time)
            'customer_notify': 1,
            'notes': {'user_id': user['id'], 'plan': body.plan},
        })
    except Exception as e:
        logger.exception('razorpay subscription.create failed')
        raise HTTPException(500, f'Razorpay error: {str(e)[:180]}')

    # Persist a pending record; we'll flip to active on webhook
    await db.billing_subscriptions.insert_one({
        'id': str(uuid.uuid4()),
        'user_id': user['id'],
        'plan': body.plan,
        'razorpay_subscription_id': sub['id'],
        'razorpay_plan_id': plan_id,
        'status': sub.get('status', 'created'),
        'created_at': _iso(),
        'updated_at': _iso(),
    })
    return {
        'configured': True,
        'subscription_id': sub['id'],
        'short_url': sub.get('short_url'),
        'status': sub.get('status'),
        'key_id': KEY_ID,  # safe: publishable
    }


# ---------- Verify checkout signature (frontend hits this after Razorpay modal) ----------
class VerifyIn(BaseModel):
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str


@router.post('/verify')
async def verify(body: VerifyIn, user=Depends(get_current_user)):
    if not _is_configured():
        raise HTTPException(400, 'Razorpay not configured')
    # For subscriptions, signature is HMAC-SHA256 of `payment_id|subscription_id`
    msg = f'{body.razorpay_payment_id}|{body.razorpay_subscription_id}'.encode()
    expected = hmac.new(KEY_SECRET.encode(), msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, body.razorpay_signature):
        raise HTTPException(400, 'Invalid signature')

    # Look up the subscription record we created earlier
    rec = await db.billing_subscriptions.find_one({'razorpay_subscription_id': body.razorpay_subscription_id, 'user_id': user['id']}, {'_id': 0})
    if not rec:
        raise HTTPException(404, 'Subscription record not found')

    # Grant plan
    await grant_plan(user, rec['plan'], interval='monthly')
    await db.billing_subscriptions.update_one(
        {'razorpay_subscription_id': body.razorpay_subscription_id},
        {'$set': {'status': 'active', 'last_payment_id': body.razorpay_payment_id, 'updated_at': _iso()}}
    )
    return {'ok': True, 'plan': rec['plan']}


# ---------- Webhook (server-to-server truth) ----------
@router.post('/webhook')
async def webhook(request: Request):
    body_bytes = await request.body()
    if not WEBHOOK_SECRET:
        # Silently accept in unconfigured mode to allow Razorpay's ping-tests
        return {'ok': True, 'unconfigured': True}
    sig = request.headers.get('X-Razorpay-Signature', '')
    expected = hmac.new(WEBHOOK_SECRET.encode(), body_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(400, 'Invalid webhook signature')

    import json as _json
    try:
        payload = _json.loads(body_bytes.decode('utf-8'))
    except Exception:
        raise HTTPException(400, 'Invalid JSON')

    event = payload.get('event') or ''
    entity = (payload.get('payload') or {}).get('subscription', {}).get('entity', {})
    sub_id = entity.get('id')
    notes = entity.get('notes') or {}
    user_id = notes.get('user_id')

    await db.billing_events.insert_one({
        'id': str(uuid.uuid4()),
        'event': event,
        'subscription_id': sub_id,
        'user_id': user_id,
        'received_at': _iso(),
        'raw': payload,
    })

    # Handle key events
    if event in ('subscription.charged', 'subscription.activated', 'subscription.resumed') and user_id and sub_id:
        rec = await db.billing_subscriptions.find_one({'razorpay_subscription_id': sub_id})
        if rec:
            user = await db.users.find_one({'id': user_id})
            if user:
                await grant_plan(user, rec['plan'], interval='monthly')
        await db.billing_subscriptions.update_one({'razorpay_subscription_id': sub_id}, {'$set': {'status': 'active', 'updated_at': _iso()}})
    elif event in ('subscription.paused', 'subscription.cancelled', 'subscription.completed'):
        if user_id:
            user = await db.users.find_one({'id': user_id})
            if user:
                await cancel_subscription(user)
        await db.billing_subscriptions.update_one({'razorpay_subscription_id': sub_id}, {'$set': {'status': event.split('.')[-1], 'updated_at': _iso()}})

    return {'ok': True, 'event': event}


# ---------- My billing / history ----------
@router.get('/history')
async def history(user=Depends(get_current_user)):
    items = [x async for x in db.billing_subscriptions.find({'user_id': user['id']}, {'_id': 0, 'razorpay_plan_id': 0}).sort('created_at', -1).limit(20)]
    return {'items': items}


@router.post('/cancel')
async def cancel(user=Depends(get_current_user)):
    """Cancel latest active Razorpay subscription (best-effort) + downgrade user."""
    rec = await db.billing_subscriptions.find_one({'user_id': user['id'], 'status': 'active'}, {'_id': 0})
    if _is_configured() and rec and rec.get('razorpay_subscription_id'):
        try:
            _client().subscription.cancel(rec['razorpay_subscription_id'])
        except Exception as e:
            logger.warning('Razorpay cancel failed: %s', e)
    sub = await cancel_subscription(user)
    if rec:
        await db.billing_subscriptions.update_one({'razorpay_subscription_id': rec['razorpay_subscription_id']}, {'$set': {'status': 'cancelled', 'updated_at': _iso()}})
    return {'ok': True, 'subscription': sub}


# ---------- Admin: create Razorpay plans (one-time bootstrap when prices are decided) ----------
class CreatePlansIn(BaseModel):
    pro_amount_inr: int   # e.g. 499
    elite_amount_inr: int  # e.g. 1999


@router.post('/admin/create-plans')
async def admin_create_plans(body: CreatePlansIn, admin=Depends(get_current_admin)):
    if not _is_configured():
        raise HTTPException(400, 'Razorpay not configured — set RAZORPAY_KEY_ID / SECRET first')
    client = _client()
    try:
        pro = client.plan.create({
            'period': 'monthly', 'interval': 1,
            'item': {'name': 'Getszy Pro (Monthly)', 'amount': body.pro_amount_inr * 100, 'currency': 'INR'},
        })
        elite = client.plan.create({
            'period': 'monthly', 'interval': 1,
            'item': {'name': 'Getszy Elite (Monthly)', 'amount': body.elite_amount_inr * 100, 'currency': 'INR'},
        })
    except Exception as e:
        raise HTTPException(500, f'Razorpay plan.create failed: {e}')
    return {
        'ok': True,
        'pro_plan_id': pro['id'],
        'elite_plan_id': elite['id'],
        'next_step': 'Set RAZORPAY_PLAN_PRO and RAZORPAY_PLAN_ELITE in backend .env, then restart backend.',
    }
