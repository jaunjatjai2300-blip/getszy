"""Per-user, per-day media generation quota.

We persist a tiny doc per user keyed by UTC date string. Counts are incremented
by tool kind (images, videos, voice_min, mirror, logo).

Free plan: 5 images, 0 videos, 0 voice, 0 mirror, 2 logos / day
Pro:       100 images, 5 videos, 30 voice_min, 20 mirror, 20 logos / day
Elite:     unlimited (large quota numbers)
"""
from datetime import datetime, timezone
from db import db
from subscription import effective_subscription, PLAN_FREE, PLAN_PRO, PLAN_ELITE

MEDIA_QUOTAS = {
    PLAN_FREE:  {'images': 5,    'videos': 0,  'voice_min': 0,   'mirror': 0,  'logos': 2},
    PLAN_PRO:   {'images': 100,  'videos': 5,  'voice_min': 30,  'mirror': 20, 'logos': 20},
    PLAN_ELITE: {'images': 9999, 'videos': 50, 'voice_min': 300, 'mirror': 200,'logos': 200},
}


def _today() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


async def get_usage(user_id: str) -> dict:
    doc = await db.media_usage.find_one({'user_id': user_id, 'date': _today()}, {'_id': 0})
    if not doc:
        return {'images': 0, 'videos': 0, 'voice_min': 0, 'mirror': 0, 'logos': 0}
    return {k: doc.get(k, 0) for k in ('images', 'videos', 'voice_min', 'mirror', 'logos')}


async def get_quota(user: dict) -> dict:
    sub = await effective_subscription(user)
    quota = MEDIA_QUOTAS.get(sub.get('plan', PLAN_FREE), MEDIA_QUOTAS[PLAN_FREE])
    used = await get_usage(user['id'])
    remaining = {k: max(0, quota[k] - used.get(k, 0)) for k in quota}
    return {'plan': sub.get('plan'), 'quota': quota, 'used': used, 'remaining': remaining, 'date': _today()}


async def check_and_consume(user: dict, kind: str, amount: int = 1) -> tuple[bool, str]:
    if kind not in MEDIA_QUOTAS[PLAN_FREE]:
        return False, f'Unknown tool: {kind}'
    sub = await effective_subscription(user)
    plan = sub.get('plan', PLAN_FREE)
    quota = MEDIA_QUOTAS.get(plan, MEDIA_QUOTAS[PLAN_FREE])[kind]
    if quota <= 0:
        return False, f'Your {plan.title()} plan does not include {kind.replace("_", " ")} generation. Upgrade to unlock.'
    used = await get_usage(user['id'])
    if used.get(kind, 0) + amount > quota:
        return False, f'Daily limit reached ({used.get(kind, 0)}/{quota}) for {kind}. Resets at midnight UTC.'
    await db.media_usage.update_one(
        {'user_id': user['id'], 'date': _today()},
        {'$inc': {kind: amount}, '$set': {'updated_at': datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return True, ''
