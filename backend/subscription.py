"""Subscription helpers and gating logic."""
from datetime import datetime, timezone, timedelta
from db import db

PLAN_FREE = 'free'
PLAN_PRO = 'pro'
PLAN_ELITE = 'elite'

STATUS_ACTIVE = 'active'
STATUS_TRIAL = 'trial'
STATUS_EXPIRED = 'expired'
STATUS_CANCELLED = 'cancelled'

QUOTAS = {
    PLAN_FREE: {'studio_builds': 0, 'advanced_courses': False, 'ai_tutor': True},
    PLAN_PRO: {'studio_builds': 10, 'advanced_courses': True, 'ai_tutor': True},
    PLAN_ELITE: {'studio_builds': 9999, 'advanced_courses': True, 'ai_tutor': True},
}

PRICING = [
    {
        'id': 'free', 'name': 'Free', 'tagline': 'Discover & learn the basics',
        'price_monthly': 0, 'price_yearly': 0, 'cta': 'Current Plan',
        'features': [
            'Browse the entire storefront',
            'Beginner + Intermediate Academy courses',
            'AI Tutor for free courses',
            'View Studio (no builds)',
        ],
    },
    {
        'id': 'pro', 'name': 'Pro', 'tagline': 'Go beyond the basics', 'highlight': True,
        'price_monthly': 499, 'price_yearly': 4999, 'cta': 'Start 7-day free trial',
        'features': [
            'Everything in Free',
            'All Advanced courses unlocked',
            'AI Studio — build websites by chatting',
            '10 Studio builds / month',
            'Premium AI Tutor (priority)',
        ],
    },
    {
        'id': 'elite', 'name': 'Elite', 'tagline': 'For power users & creators',
        'price_monthly': 1499, 'price_yearly': 14999, 'cta': 'Upgrade to Elite',
        'features': [
            'Everything in Pro',
            'Unlimited Studio builds',
            'Priority AI queue',
            'Early access to AI Image/Video Studio',
            'Direct support',
        ],
    },
]


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat()


def _next_month_start(dt):
    if dt.month == 12:
        return dt.replace(year=dt.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return dt.replace(month=dt.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


async def ensure_subscription(user: dict) -> dict:
    """Make sure user has a subscription dict; create default free."""
    sub = user.get('subscription')
    if not sub:
        now = _now()
        sub = {
            'plan': PLAN_FREE,
            'status': STATUS_ACTIVE,
            'trial_started_at': None,
            'trial_ends_at': None,
            'current_period_end': None,
            'cancelled_at': None,
            'studio_builds_used': 0,
            'studio_builds_reset_at': _iso(_next_month_start(now)),
        }
        await db.users.update_one({'id': user['id']}, {'$set': {'subscription': sub}})
        user['subscription'] = sub
    return sub


async def effective_subscription(user: dict) -> dict:
    """Resolve plan considering trial expiry + monthly quota reset."""
    sub = await ensure_subscription(user)
    now = _now()
    changed = False

    # Trial expiry
    if sub.get('status') == STATUS_TRIAL and sub.get('trial_ends_at'):
        try:
            ends = datetime.fromisoformat(sub['trial_ends_at'].replace('Z', '+00:00'))
            if now > ends:
                sub['status'] = STATUS_EXPIRED
                sub['plan'] = PLAN_FREE
                changed = True
        except Exception:
            pass

    # Paid expiry
    if sub.get('status') == STATUS_ACTIVE and sub.get('plan') in (PLAN_PRO, PLAN_ELITE) and sub.get('current_period_end'):
        try:
            ends = datetime.fromisoformat(sub['current_period_end'].replace('Z', '+00:00'))
            if now > ends:
                sub['status'] = STATUS_EXPIRED
                sub['plan'] = PLAN_FREE
                changed = True
        except Exception:
            pass

    # Monthly quota reset
    if sub.get('studio_builds_reset_at'):
        try:
            reset_at = datetime.fromisoformat(sub['studio_builds_reset_at'].replace('Z', '+00:00'))
            if now >= reset_at:
                sub['studio_builds_used'] = 0
                sub['studio_builds_reset_at'] = _iso(_next_month_start(now))
                changed = True
        except Exception:
            pass

    if changed:
        await db.users.update_one({'id': user['id']}, {'$set': {'subscription': sub}})
        user['subscription'] = sub
    return sub


def plan_features(plan: str) -> dict:
    return QUOTAS.get(plan, QUOTAS[PLAN_FREE])


async def can_access_advanced(user: dict) -> bool:
    sub = await effective_subscription(user)
    return plan_features(sub['plan'])['advanced_courses']


async def can_use_studio(user: dict) -> tuple[bool, str, dict]:
    sub = await effective_subscription(user)
    feats = plan_features(sub['plan'])
    quota = feats['studio_builds']
    used = sub.get('studio_builds_used', 0)
    if quota <= 0:
        return False, 'Upgrade to Pro to use AI Studio', sub
    if used >= quota:
        return False, f'Monthly limit reached ({used}/{quota}). Upgrade to Elite for unlimited.', sub
    return True, '', sub


async def increment_studio_builds(user_id: str):
    await db.users.update_one({'id': user_id}, {'$inc': {'subscription.studio_builds_used': 1}})


async def start_trial(user: dict) -> dict:
    sub = await ensure_subscription(user)
    # Disallow second trial
    if sub.get('trial_started_at'):
        raise ValueError('Trial already used')
    now = _now()
    ends = now + timedelta(days=7)
    sub.update({
        'plan': PLAN_PRO,
        'status': STATUS_TRIAL,
        'trial_started_at': _iso(now),
        'trial_ends_at': _iso(ends),
        'current_period_end': _iso(ends),
    })
    await db.users.update_one({'id': user['id']}, {'$set': {'subscription': sub}})
    return sub


async def grant_plan(user_id: str, plan: str, days: int = 30) -> dict:
    if plan not in (PLAN_PRO, PLAN_ELITE):
        raise ValueError('Invalid plan')
    now = _now()
    ends = now + timedelta(days=days)
    update = {
        'subscription.plan': plan,
        'subscription.status': STATUS_ACTIVE,
        'subscription.current_period_end': _iso(ends),
    }
    await db.users.update_one({'id': user_id}, {'$set': update})
    user = await db.users.find_one({'id': user_id}, {'_id': 0})
    return user.get('subscription', {})


async def cancel_subscription(user: dict) -> dict:
    sub = await ensure_subscription(user)
    sub['status'] = STATUS_CANCELLED
    sub['cancelled_at'] = _iso(_now())
    await db.users.update_one({'id': user['id']}, {'$set': {'subscription': sub}})
    return sub
