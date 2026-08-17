"""Neo Ops — AI-native assistant layer for the admin (Tier 1 #7/#8/#9).

- POST /admin/neo/insight  → plain-English insight + suggested actions from REAL data
- POST /admin/neo/draft    → inline AI copy (refund email, product copy, coupon message)
Both degrade gracefully (rule-based fallback) if the LLM is unavailable.
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import get_current_admin
from db import db
from llm_provider import chat_completion

router = APIRouter(prefix='/admin/neo', tags=['neo-ops'])


class InsightIn(BaseModel):
    context: str = 'orders'          # orders | revenue | users | refunds | security
    window: str = '24h'              # 24h | 7d | 30d


class DraftIn(BaseModel):
    type: str                        # refund_email | product_copy | coupon
    fields: dict = {}


async def _safe(coro, default=0):
    try:
        return await coro
    except Exception:
        return default


async def _ctx_data(context: str, window: str) -> dict:
    now = datetime.now(timezone.utc)
    days = {'24h': 1, '7d': 7, '30d': 30}.get(window, 1)
    since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if days > 1:
        since = since.replace(day=1) if days == 30 else since  # 30d ~ this month
    since_iso = since.isoformat()

    if context == 'revenue':
        rev = await _safe(db.orders.aggregate([
            {'$match': {'status': {'$in': ['paid', 'delivered', 'shipped']},
                        'created_at': {'$gte': since_iso}}},
            {'$group': {'_id': None, 'total': {'$sum': '$total'}}},
        ]).to_list(1))
        return {'revenue_window': round(rev[0]['total'] if rev else 0, 2)}

    if context == 'users':
        total = await _safe(db.users.count_documents({}))
        new = await _safe(db.users.count_documents({'created_at': {'$gte': since_iso}}))
        subs = await _safe(db.users.count_documents({'subscription_plan': {'$ne': 'free'}}))
        return {'total_users': total, 'new_users_window': new, 'paying_users': subs}

    if context == 'refunds':
        cnt = await _safe(db.refunds.count_documents({}))
        amt = await _safe(db.refunds.aggregate([
            {'$group': {'_id': None, 'total': {'$sum': '$refund_amount'}}},
        ]).to_list(1))
        return {'refund_count': cnt, 'refund_amount_total': round(amt[0]['total'] if amt else 0, 2)}

    if context == 'security':
        fails = await _safe(db.audit_logs.count_documents({
            'action': 'failed_login', 'created_at': {'$gte': since_iso}}))
        blocked = await _safe(db.blocked_ips.count_documents({}))
        return {'failed_logins_window': fails, 'blocked_ips': blocked}

    # default: orders
    total = await _safe(db.orders.count_documents({}))
    recent = await _safe(db.orders.count_documents({'created_at': {'$gte': since_iso}}))
    rev = await _safe(db.orders.aggregate([
        {'$match': {'status': {'$in': ['paid', 'delivered', 'shipped']},
                    'created_at': {'$gte': since_iso}}},
        {'$group': {'_id': None, 'total': {'$sum': '$total'}}},
    ]).to_list(1))
    return {
        'total_orders': total,
        'orders_window': recent,
        'revenue_window': round(rev[0]['total'] if rev else 0, 2),
    }


def _fallback_insight(context: str, data: dict) -> dict:
    parts = [f"{k.replace('_', ' ')}: {v}" for k, v in data.items()]
    summary = f"{context.title()} snapshot — " + "; ".join(parts) + "."
    suggestions = [
        "Review the latest entries for anomalies.",
        "Set an alert if these numbers move >20% vs yesterday.",
    ]
    if context == 'refunds':
        suggestions = ["Check repeat refund reasons for a product quality issue.",
                       "Consider tightening the return window if refunds spike."]
    elif context == 'security':
        suggestions = ["Block repeated offender IPs automatically.",
                       "Enforce 2FA for admin accounts."]
    elif context == 'revenue':
        suggestions = ["Launch a targeted remarketing campaign.",
                       "Bundle low-selling items to lift AOV."]
    return {'insight': summary, 'suggestions': suggestions, 'source': 'rule-based'}


@router.post('/insight')
async def insight(body: InsightIn, _=Depends(get_current_admin)):
    data = await _ctx_data(body.context, body.window)
    try:
        system = (
            "You are Neo, the founder's AI ops analyst for Getszy. Given a JSON "
            "snapshot of real platform data, reply with STRICT JSON: "
            "{\"insight\": \"one crisp plain-English sentence\", "
            "\"suggestions\": [\"action 1\", \"action 2\", \"action 3\"]}. "
            "No markdown, no commentary."
        )
        user = f"Context: {body.context} (window {body.window})\nData: {data}"
        raw = await chat_completion(system, user, temperature=0.3)
        parsed = _parse_json(raw)
        if parsed and 'insight' in parsed:
            return {
                'insight': parsed.get('insight'),
                'suggestions': parsed.get('suggestions', []),
                'source': 'llm',
                'data': data,
            }
    except Exception:
        pass
    return {**_fallback_insight(body.context, data), 'data': data}


@router.post('/draft')
async def draft(body: DraftIn, _=Depends(get_current_admin)):
    f = body.fields or {}
    if body.type == 'refund_email':
        prompt = (
            f"Write a short, polite refund confirmation email to customer "
            f"{f.get('name', 'valued customer')}. Order {f.get('order_id','')}, "
            f"amount ₹{f.get('amount','')}. Tone: warm, Hindi-English mix, 2 sentences."
        )
    elif body.type == 'product_copy':
        prompt = (
            f"Write a compelling 1-paragraph product description for "
            f"'{f.get('name','')}'. Category: {f.get('category','')}. Highlight 3 benefits."
        )
    elif body.type == 'coupon':
        prompt = (
            f"Write a punchy 1-line promo message for a {f.get('percent','10')}% off "
            f"coupon code {f.get('code','SAVE10')}. Friendly, urgent, <120 chars."
        )
    else:
        prompt = f"Write friendly marketing copy about: {f}"

    try:
        text = await chat_completion(
            "You are Neo, a senior copywriter for Getszy (Indian SMB commerce). "
            "Be concise and on-brand.", prompt, temperature=0.6)
        return {'text': text, 'source': 'llm'}
    except Exception:
        return {'text': f"[{body.type}] draft unavailable right now — please try later.",
                'source': 'fallback'}


def _parse_json(raw: str) -> Optional[dict]:
    if not raw:
        return None
    s = raw.strip()
    if s.startswith('```'):
        s = s.strip('`')
        s = s[s.find('{') if '{' in s else 0:]
    try:
        import json
        return json.loads(s)
    except Exception:
        return None
