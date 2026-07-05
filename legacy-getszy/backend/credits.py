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
from datetime import datetime, timezone
from typing import Optional
from db import db

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


async def has_enough(user: dict, action: str, qty: int = 1) -> bool:
    cost = cost_of(action, qty)
    return int(user.get('credits', 0) or 0) >= cost


async def deduct(user_id: str, action: str, qty: int = 1, meta: Optional[dict] = None) -> tuple[bool, str, int]:
    """Atomically deduct credits. Returns (ok, message, balance_after)."""
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
