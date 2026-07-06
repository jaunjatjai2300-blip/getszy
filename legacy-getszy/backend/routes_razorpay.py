"""Razorpay integration — Credit pack subscriptions only (monthly).

Design (per founder decision, July 2026 — credit system is the product's
single gate for AI actions; see credits.py):
- Works in UNCONFIGURED mode when RAZORPAY_KEY_ID / SECRET / WEBHOOK_SECRET are missing.
  All endpoints return `{ configured: False, ... }` so frontend can render a graceful
  "Coming soon" state. When keys are added and backend restarted, endpoints activate.

- Uses Razorpay Subscriptions API (monthly interval). Each successful charge
  (initial + every renewal) grants that pack's credit amount via
  `credits.add_credits()` — credits do NOT roll over automatically into a
  "plan"; they just top up the user's balance every billing cycle.
- Packs are defined in `credits.CREDIT_PACKS` (lite/pro/ultra). Razorpay
  plan_ids can be created either via the Razorpay dashboard and set via env
  `RAZORPAY_PLAN_LITE` / `RAZORPAY_PLAN_PRO` / `RAZORPAY_PLAN_ULTRA`, OR
  auto-created via `POST /billing/admin/create-plans` (admin-only).

Env vars:
  RAZORPAY_KEY_ID
  RAZORPAY_KEY_SECRET
  RAZORPAY_WEBHOOK_SECRET
  RAZORPAY_PLAN_LITE        (optional, "plan_..." id from Razorpay)
  RAZORPAY_PLAN_PRO         (optional)
  RAZORPAY_PLAN_ULTRA       (optional)
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
from credits import CREDIT_PACKS, add_credits

logger = logging.getLogger('getszy.billing')
router = APIRouter(prefix='/billing', tags=['billing'])

KEY_ID = os.environ.get('RAZORPAY_KEY_ID', '').strip()
KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '').strip()
WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '').strip()
PLAN_ENV_KEYS = {'lite': 'RAZORPAY_PLAN_LITE', 'pro': 'RAZORPAY_PLAN_PRO', 'ultra': 'RAZORPAY_PLAN_ULTRA'}
PLAN_IDS = {pack: os.environ.get(env_key, '').strip() for pack, env_key in PLAN_ENV_KEYS.items()}


def _is_configured() -> bool:
    return bool(KEY_ID and KEY_SECRET)


def _client():
    if not _is_configured():
        return None
    import razorpay  # lazy import so unconfigured mode doesn't require import
    return razorpay.Client(auth=(KEY_ID, KEY_SECRET))


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _plan_id_for(pack: str) -> Optional[str]:
    return PLAN_IDS.get(pack) or None


# ---------- Status ----------
@router.get('/status')
async def status(user=Depends(get_current_user)):
    return {
        'configured': _is_configured(),
        'webhook_configured': bool(WEBHOOK_SECRET),
        'plans_configured': {pack: bool(pid) for pack, pid in PLAN_IDS.items()},
        'key_id_preview': (KEY_ID[:8] + '…') if KEY_ID else '',
    }


# ---------- Public pricing (no auth) ----------
@router.get('/pricing')
async def pricing_public():
    plans = [
        {
            'id': pack,
            'name': info['name'],
            'price_monthly': info['price_inr'],
            'credits': info['credits'],
        }
        for pack, info in CREDIT_PACKS.items()
    ]
    return {'plans': plans, 'currency': 'INR', 'interval': 'monthly'}


# ---------- Create Subscription ----------
class SubscribeIn(BaseModel):
    plan: str  # 'lite' | 'pro' | 'ultra'


@router.post('/subscribe')
async def subscribe(body: SubscribeIn, user=Depends(get_current_user)):
    if body.plan not in CREDIT_PACKS:
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


async def _grant_pack_credits_once(user_id: str, pack: str, payment_id: str, source: str) -> Optional[int]:
    """Grant a pack's credits for a given Razorpay payment_id, but only once.
    Guards against Razorpay webhook retries and double-firing (verify + webhook
    both reporting the same charge) double-crediting the user."""
    if pack not in CREDIT_PACKS:
        logger.warning('Unknown credit pack %s for payment %s', pack, payment_id)
        return None
    try:
        await db.billing_processed_payments.insert_one({
            'payment_id': payment_id,
            'user_id': user_id,
            'pack': pack,
            'source': source,
            'created_at': _iso(),
        })
    except Exception:
        # Duplicate key (unique index on payment_id) => already processed, skip.
        return None
    amount = CREDIT_PACKS[pack]['credits']
    return await add_credits(user_id, amount, reason='razorpay_subscription_charge', meta={'pack': pack, 'payment_id': payment_id, 'source': source})


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

    balance = await _grant_pack_credits_once(user['id'], rec['plan'], body.razorpay_payment_id, source='verify')
    await db.billing_subscriptions.update_one(
        {'razorpay_subscription_id': body.razorpay_subscription_id},
        {'$set': {'status': 'active', 'last_payment_id': body.razorpay_payment_id, 'updated_at': _iso()}}
    )
    return {'ok': True, 'plan': rec['plan'], 'credits_granted': CREDIT_PACKS[rec['plan']]['credits'] if balance is not None else 0, 'balance': balance}


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
        payment_entity = (payload.get('payload') or {}).get('payment', {}).get('entity', {})
        payment_id = payment_entity.get('id') or f'{sub_id}:{event}:{entity.get("current_end", "")}'
        if rec:
            await _grant_pack_credits_once(user_id, rec['plan'], payment_id, source='webhook')
        await db.billing_subscriptions.update_one({'razorpay_subscription_id': sub_id}, {'$set': {'status': 'active', 'updated_at': _iso()}})
    elif event in ('subscription.paused', 'subscription.cancelled', 'subscription.completed'):
        await db.billing_subscriptions.update_one({'razorpay_subscription_id': sub_id}, {'$set': {'status': event.split('.')[-1], 'updated_at': _iso()}})

    return {'ok': True, 'event': event}


# ---------- My billing / history ----------
@router.get('/history')
async def history(user=Depends(get_current_user)):
    items = [x async for x in db.billing_subscriptions.find({'user_id': user['id']}, {'_id': 0, 'razorpay_plan_id': 0}).sort('created_at', -1).limit(20)]
    return {'items': items}


@router.post('/cancel')
async def cancel(user=Depends(get_current_user)):
    """Cancel latest active Razorpay subscription (best-effort). Credits already
    granted are NOT clawed back — cancelling just stops future monthly charges."""
    rec = await db.billing_subscriptions.find_one({'user_id': user['id'], 'status': 'active'}, {'_id': 0})
    if not rec:
        return {'ok': True, 'cancelled': False}
    if _is_configured() and rec.get('razorpay_subscription_id'):
        try:
            _client().subscription.cancel(rec['razorpay_subscription_id'])
        except Exception as e:
            logger.warning('Razorpay cancel failed: %s', e)
    await db.billing_subscriptions.update_one({'razorpay_subscription_id': rec['razorpay_subscription_id']}, {'$set': {'status': 'cancelled', 'updated_at': _iso()}})
    return {'ok': True, 'cancelled': True}


# ---------- Admin: create Razorpay plans (one-time bootstrap when prices are decided) ----------
@router.post('/admin/create-plans')
async def admin_create_plans(admin=Depends(get_current_admin)):
    if not _is_configured():
        raise HTTPException(400, 'Razorpay not configured — set RAZORPAY_KEY_ID / SECRET first')
    client = _client()
    created = {}
    try:
        for pack, info in CREDIT_PACKS.items():
            plan = client.plan.create({
                'period': 'monthly', 'interval': 1,
                'item': {
                    'name': f'Getszy {info["name"]} (Monthly, {info["credits"]} credits)',
                    'amount': info['price_inr'] * 100,
                    'currency': 'INR',
                },
            })
            created[pack] = plan['id']
    except Exception as e:
        raise HTTPException(500, f'Razorpay plan.create failed: {e}')
    return {
        'ok': True,
        'plan_ids': created,
        'next_step': 'Set ' + ', '.join(PLAN_ENV_KEYS[p] for p in created) + ' in backend .env, then restart backend.',
    }
