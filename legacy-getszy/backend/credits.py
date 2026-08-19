"""Unified credit system — the single gate for every AI-cost-incurring action.

Design (per founder decision, July 2026):
- New users start with 0 credits. No free credits are granted automatically.
- Credits are only added via `add_credits()` — today that means an admin manual
  grant (for pre-Razorpay testing); once Razorpay/Stripe is wired, the payment
  webhook will call `add_credits()` after a successful purchase.
- 1 credit ≈ ₹20 of retail value (Lite ₹799/40cr, Pro ₹2,499/125cr, Ultra
  ₹5,999/300cr), sized so real provider cost stays under ~30% of credit price.
- Every deduction is atomic (single findAndUpdate with a `credits >= cost`
  filter) so concurrent requests can never push a balance negative, and every
  change (spend or grant) is written to `credit_transactions` for audit/support.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from db import db

logger = logging.getLogger('getszy.credits')

# ===== Credit costs per action =====
# Keep these centralized so pricing changes happen in exactly one place.
CREDIT_COSTS = {
    'image': 2,               # Media Studio — single image
    'logo': 3,                # Media Studio — 4 logo variants
    'tryon': 2,                # Media Studio — virtual try-on
    'voice_min': 1,             # Media Studio — per ~minute of narration
    'video_quick': 10,          # Media Studio — quick AI video clip
    'mirror': 2,                # Media Studio — face mirror/swap
    'script': 1,                # Creator OS — single script
    'repurpose_format': 1,       # Creator OS — per target format
    'faceless_video': 10,        # Faceless Video Studio — one full video job
    'video_factory_chain': 5,    # Video Factory v2 — enhance→research→script→hooks→storyboard chain
    'video_factory_assets': 15,  # Video Factory v2 — image+voice generation + final render
    'builder_website': 5,        # Talk-to-Build Studio — new site generation
    'builder_refine': 3,         # Talk-to-Build Studio — refine existing site
    # ── Creator / entertainment economy (high-volume, low-cost) ──
    'viral_hooks': 1,            # Creator OS — batch of viral hook openers
    'meme_mode': 1,              # Creator OS — story/source -> storyboard
    # ── Game-changing video features (Phase 1/2) ──
    'avatar_talking': 2,         # Photo + voice -> talking avatar (SadTalker)
    'voice_clone': 1,            # Clone a voice from reference audio (XTTS)
    'text_to_video': 4,          # Topic -> script + scenes + voiceover + music
    'video_translate': 5,        # Video -> translated lip-synced video
    'image_to_video': 3,         # Photo -> animated video clip
    'one_tap_repurposing': 6,    # Long video -> vertical shorts w/ captions
    'social_publish': 1,         # One-click publish to YouTube/Insta/FB
    'influencer_reply': 1,       # AI auto-reply to a social comment
}

# ===== Paid credit packs (Razorpay monthly subscriptions) =====
# Keep in sync with routes_razorpay.py — this is the single source of truth
# for what each recurring pack charges and how many credits it grants per cycle.
CREDIT_PACKS = {
    'lite':  {'name': 'Lite',  'price_inr': 799,  'credits': 40},
    'pro':   {'name': 'Pro',   'price_inr': 2499, 'credits': 125},
    'ultra': {'name': 'Ultra', 'price_inr': 5999, 'credits': 300},
}

# Subscription plan -> credits granted on activation (CTO decision, Aug 2026).
# A subscription is a credit *bucket*: it is granted once when the user
# subscribes, and the subscription ENDS the moment the balance hits 0 (the user
# drops to free and must resubscribe). Sizes are kept in lock-step with
# CREDIT_PACKS so pricing stays one coherent system.
PLAN_CREDIT_GRANT = {
    'pro': CREDIT_PACKS['pro']['credits'],    # 125
    'elite': CREDIT_PACKS['ultra']['credits'],  # 300
}

# ===== Creator / entertainment economy — high-volume, low-cost buckets =====
# Ultra-cheap tiers to win India's mobile-first creator market (YouTubers, Reel
# creators, influencers). Credits here are deliberately generous vs the
# commerce packs so a ₹299 pass covers ~100 short-form generations.
CREATOR_PACKS = {
    'creator_pass': {'name': 'Creator Pass', 'price_inr': 299,  'credits': 100,
                     'tagline': '100 HD short-form generations/mo'},
    'creator_topup': {'name': 'Creator Top-up', 'price_inr': 99, 'credits': 50,
                      'tagline': 'Pay-as-you-go for casual creators'},
}

# Plan alias used by the subscription layer for the creator bucket.
CREATOR_PLAN_GRANT = {
    'creator': CREATOR_PACKS['creator_pass']['credits'],  # 100
}

# ===== Free tier (viral growth engine) =====
# Free users get a small monthly allowance of watermarked generations so the
# product spreads organically ("Made with Getszy.com"). Paid users are exempt.
FREE_TIER_MONTHLY = 5
WATERMARK_TEXT = 'Made with Getszy.com'
# Actions that count against the free tier (video outputs only).
FREE_TIER_ACTIONS = {
    'avatar_talking', 'text_to_video', 'video_translate',
    'image_to_video', 'one_tap_repurposing',
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def cost_of(action: str, qty: int = 1) -> int:
    if action not in CREDIT_COSTS:
        raise ValueError(f'Unknown credit action: {action}')
    return CREDIT_COSTS[action] * max(1, qty)


async def get_balance(user_id: str) -> int:
    user = await db.users.find_one({'id': user_id}, {'_id': 0, 'credits': 1})
    return int((user or {}).get('credits', 0) or 0)


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m')


async def free_tier_used(user_id: str) -> int:
    rec = await db.free_tier_usage.find_one({'user_id': user_id, 'month': _month_key()}, {'_id': 0, 'count': 1})
    return int((rec or {}).get('count', 0) or 0)


async def free_tier_remaining(user_id: str) -> int:
    return max(0, FREE_TIER_MONTHLY - await free_tier_used(user_id))


async def free_tier_record(user_id: str, n: int = 1) -> None:
    await db.free_tier_usage.update_one(
        {'user_id': user_id, 'month': _month_key()},
        {'$inc': {'count': n}, '$setOnInsert': {'user_id': user_id, 'month': _month_key()}},
        upsert=True,
    )


async def has_enough(user: dict, action: str, qty: int = 1) -> bool:
    if user.get('role') in ('admin', 'founder'):
        return True
    cost = cost_of(action, qty)
    return int(user.get('credits', 0) or 0) >= cost


async def deduct(user_id: str, action: str, qty: int = 1, meta: Optional[dict] = None, user: Optional[dict] = None) -> tuple[bool, str, int]:
    """Atomically deduct credits. Returns (ok, message, balance_after).
    Admin and founder roles bypass credit checks entirely."""
    # Admin/founder bypass — they can use everything for free
    if not user:
        user = await db.users.find_one({'id': user_id}, {'_id': 0, 'role': 1, 'credits': 1})
    if user and user.get('role') in ('admin', 'founder'):
        return True, '', int(user.get('credits', 0) or 0)

    cost = cost_of(action, qty)
    updated = await db.users.find_one_and_update(
        {'id': user_id, 'credits': {'$gte': cost}},
        {'$inc': {'credits': -cost}},
        return_document=True,
        projection={'_id': 0, 'credits': 1},
    )
    if not updated:
        current = await get_balance(user_id)
        return False, (
            f'Not enough credits. This action needs {cost} credits, you have {current}. '
            'Please top up your credit balance to continue.'
        ), current
    balance_after = int(updated.get('credits', 0) or 0)
    await db.credit_transactions.insert_one({
        'user_id': user_id,
        'type': 'spend',
        'action': action,
        'qty': qty,
        'amount': -cost,
        'balance_after': balance_after,
        'meta': meta or {},
        'created_at': _now(),
    })
    # Subscription is a credit bucket: when it hits 0, end it so the user must
    # resubscribe to receive a fresh grant. User-only by construction — admins
    # never reach this branch (they return early above).
    if balance_after == 0:
        try:
            from subscription import end_subscription_if_no_credits
            ended = await end_subscription_if_no_credits(user_id)
            if ended:
                logger.info('subscription ended at zero credits for user %s', user_id)
        except Exception as e:  # never block the response on a side-effect
            logger.warning('end_subscription_if_no_credits failed for %s: %s', user_id, e)
    return True, '', balance_after


async def refund(user_id: str, action: str, qty: int = 1, reason: str = 'generation_failed') -> int:
    """Refund credits when a background job fails after credits were already spent."""
    amount = cost_of(action, qty)
    updated = await db.users.find_one_and_update(
        {'id': user_id},
        {'$inc': {'credits': amount}},
        return_document=True,
        projection={'_id': 0, 'credits': 1},
    )
    balance_after = int((updated or {}).get('credits', 0) or 0)
    await db.credit_transactions.insert_one({
        'user_id': user_id,
        'type': 'refund',
        'action': action,
        'qty': qty,
        'amount': amount,
        'balance_after': balance_after,
        'meta': {'reason': reason},
        'created_at': _now(),
    })
    return balance_after


async def add_credits(user_id: str, amount: int, reason: str, meta: Optional[dict] = None) -> int:
    """Grant credits — used today by the admin manual-grant endpoint, and later
    by the Razorpay/Stripe payment webhook after a successful purchase."""
    if amount <= 0:
        raise ValueError('amount must be positive')
    updated = await db.users.find_one_and_update(
        {'id': user_id},
        {'$inc': {'credits': amount}},
        return_document=True,
        projection={'_id': 0, 'credits': 1},
    )
    if updated is None:
        raise ValueError('user not found')
    balance_after = int(updated.get('credits', 0) or 0)
    await db.credit_transactions.insert_one({
        'user_id': user_id,
        'type': 'grant',
        'action': 'manual_grant',
        'qty': amount,
        'amount': amount,
        'balance_after': balance_after,
        'meta': {**(meta or {}), 'reason': reason},
        'created_at': _now(),
    })
    return balance_after
