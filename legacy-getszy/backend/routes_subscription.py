import os

from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_user, get_current_admin
from subscription import (
    PRICING, effective_subscription, start_trial, grant_plan, cancel_subscription,
    PLAN_PRO, PLAN_ELITE, plan_features,
)
from db import db

router = APIRouter(tags=['subscription'])


@router.get('/pricing')
async def pricing():
    return {'plans': PRICING}


@router.get('/me/subscription')
async def my_subscription(user=Depends(get_current_user)):
    sub = await effective_subscription(user)
    feats = plan_features(sub['plan'])
    return {**sub, 'quota': feats}


@router.post('/me/subscription/start-trial')
async def trial(user=Depends(get_current_user)):
    try:
        sub = await start_trial(user)
        return sub
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post('/me/subscription/upgrade')
async def upgrade(body: dict, user=Depends(get_current_user)):
    """Initiate subscription upgrade via Razorpay.
    When Razorpay is configured, creates a checkout order.
    When unconfigured, grants plan directly (admin bypass mode)."""
    plan = body.get('plan')
    interval = body.get('interval', 'monthly')
    if plan not in (PLAN_PRO, PLAN_ELITE):
        raise HTTPException(400, 'Invalid plan')

    # Try Razorpay billing route if configured
    try:
        from routes_razorpay import _is_configured, _client, _plan_id_for
        if _is_configured():
            plan_id = _plan_id_for(plan)
            if plan_id:
                client = _client()
                sub = client.subscription.create({
                    'plan_id': plan_id,
                    'total_count': 120,
                    'customer_notify': 1,
                    'notes': {'user_id': user['id'], 'plan': plan},
                })
                from db import db
                import uuid
                from datetime import datetime, timezone
                await db.billing_subscriptions.insert_one({
                    'id': str(uuid.uuid4()),
                    'user_id': user['id'],
                    'plan': plan,
                    'razorpay_subscription_id': sub['id'],
                    'razorpay_plan_id': plan_id,
                    'status': sub.get('status', 'created'),
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                })
                return {
                    'status': 'checkout_ready',
                    'subscription_id': sub['id'],
                    'short_url': sub.get('short_url'),
                    'key_id': os.environ.get('RAZORPAY_KEY_ID', ''),
                    'plan': plan,
                    'interval': interval,
                }
    except Exception:
        pass

    # Fallback: direct grant (works without Razorpay)
    from subscription import grant_plan
    sub = await grant_plan(user['id'], plan, days=30)
    return {
        'status': 'activated',
        'message': f'{plan} plan activated for 30 days. Razorpay not configured — direct grant mode.',
        'plan': plan,
        'interval': interval,
        'subscription': sub,
    }


@router.post('/me/subscription/cancel')
async def cancel(user=Depends(get_current_user)):
    sub = await cancel_subscription(user)
    return sub


# Admin: manually grant plan (until Razorpay is live)
@router.post('/admin/subscriptions/grant', dependencies=[Depends(get_current_admin)])
async def admin_grant(body: dict):
    email = body.get('email')
    plan = body.get('plan')
    days = int(body.get('days', 30))
    if not email or not plan:
        raise HTTPException(400, 'email and plan required')
    user = await db.users.find_one({'email': email.lower()}, {'_id': 0})
    if not user:
        raise HTTPException(404, 'User not found')
    sub = await grant_plan(user['id'], plan, days)
    return {'user': user['email'], 'subscription': sub}


@router.get('/admin/subscriptions', dependencies=[Depends(get_current_admin)])
async def admin_list_subscriptions():
    users = await db.users.find({'role': 'customer'}, {'_id': 0, 'password_hash': 0}).to_list(1000)
    pro = sum(1 for u in users if (u.get('subscription') or {}).get('plan') == 'pro')
    elite = sum(1 for u in users if (u.get('subscription') or {}).get('plan') == 'elite')
    trial = sum(1 for u in users if (u.get('subscription') or {}).get('status') == 'trial')
    mrr = pro * 499 + elite * 1499
    return {
        'total_users': len(users),
        'pro_count': pro,
        'elite_count': elite,
        'trial_count': trial,
        'mrr': mrr,
        'users': users,
    }
