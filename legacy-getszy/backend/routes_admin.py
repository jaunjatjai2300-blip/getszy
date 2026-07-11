from fastapi import APIRouter, Depends
from db import db
from auth import get_current_admin
from models import AdminChatIn, AdminChatMessage
from ai_chat import parse_intent, execute_intent
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter(prefix='/admin', tags=['admin'])


async def compute_stats(range_: str = 'today'):
    now = datetime.now(timezone.utc)
    if range_ == 'today':
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif range_ == 'week':
        since = now - timedelta(days=7)
    elif range_ == 'month':
        since = now - timedelta(days=30)
    else:
        since = None
    q = {}
    if since:
        q['created_at'] = {'$gte': since.isoformat()}
    orders = await db.orders.find(q, {'_id': 0}).to_list(5000)
    revenue = sum(o.get('total', 0) for o in orders)
    profit = sum(o.get('profit', 0) for o in orders)
    orders_count = len(orders)
    customers_count = await db.users.count_documents({'role': 'customer'})
    products_count = await db.products.count_documents({'is_active': True})
    low_stock = await db.products.count_documents({'stock': {'$lte': 5}})

    # 7-day revenue series
    series = []
    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_orders = [o for o in (await db.orders.find({'created_at': {'$gte': day_start.isoformat(), '$lt': day_end.isoformat()}}, {'_id': 0}).to_list(1000))]
        series.append({
            'date': day_start.strftime('%a'),
            'revenue': round(sum(o.get('total', 0) for o in day_orders), 2),
            'orders': len(day_orders),
        })

    return {
        'range': range_,
        'revenue': round(revenue, 2),
        'profit': round(profit, 2),
        'orders_count': orders_count,
        'customers_count': customers_count,
        'products_count': products_count,
        'low_stock_count': low_stock,
        'series_7d': series,
        'recent_orders': sorted(orders, key=lambda x: x.get('created_at', ''), reverse=True)[:5],
    }


@router.get('/stats', dependencies=[Depends(get_current_admin)])
async def stats(range: str = 'today'):
    return await compute_stats(range)


@router.get('/customers', dependencies=[Depends(get_current_admin)])
async def customers():
    users = await db.users.find({'role': 'customer'}, {'_id': 0, 'password_hash': 0}).to_list(500)
    for u in users:
        u['orders_count'] = await db.orders.count_documents({'user_id': u['id']})
        agg = await db.orders.find({'user_id': u['id']}, {'_id': 0, 'total': 1}).to_list(500)
        u['lifetime_value'] = round(sum(o.get('total', 0) for o in agg), 2)
    return users


@router.post('/chat')
async def chat(body: AdminChatIn, user=Depends(get_current_admin)):
    session_id = body.session_id or str(uuid.uuid4())
    parsed = await parse_intent(body.message, session_id)
    result = await execute_intent(parsed)

    # Log user msg
    user_msg = AdminChatMessage(
        session_id=session_id, role='user', text=body.message,
    )
    await db.admin_chat.insert_one(user_msg.model_dump())

    # Log assistant msg
    asst_msg = AdminChatMessage(
        session_id=session_id,
        role='assistant',
        text=parsed.get('reply', ''),
        intent=parsed.get('intent'),
        params=parsed.get('params', {}),
        result=result,
    )
    await db.admin_chat.insert_one(asst_msg.model_dump())

    return {
        'session_id': session_id,
        'intent': parsed.get('intent'),
        'params': parsed.get('params', {}),
        'reply': parsed.get('reply', ''),
        'result': result,
    }


@router.get('/chat/history')
async def chat_history(session_id: str = None, user=Depends(get_current_admin)):
    q = {'session_id': session_id} if session_id else {}
    msgs = await db.admin_chat.find(q, {'_id': 0}).sort('created_at', 1).to_list(500)
    return msgs


@router.get('/founder-stats', dependencies=[Depends(get_current_admin)])
async def founder_stats():
    import os
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now - timedelta(days=30)

    total_users = await db.users.count_documents({'role': 'customer'})
    active_users = await db.users.count_documents({'role': 'customer', 'last_login': {'$gte': month_start.isoformat()}})
    subscribers = await db.subscriptions.count_documents({'status': 'active'}) if await db.list_collection_names() else 0
    try: subscribers = await db.subscriptions.count_documents({'status': 'active'})
    except: subscribers = 0

    # MRR/ARR from subscriptions
    try:
        subs = await db.subscriptions.find({'status': 'active'}, {'_id': 0, 'amount': 1}).to_list(1000)
        mrr = sum(s.get('amount', 999) for s in subs) if subs else subscribers * 999
    except:
        mrr = subscribers * 999
    arr = mrr * 12

    # AI Jobs
    ai_jobs_today = await db.video_jobs.count_documents({'created_at': {'$gte': today_start.isoformat()}})
    total_videos = await db.video_jobs.count_documents({'status': 'done'})
    total_images = await db.ai_jobs.count_documents({'type': 'image', 'status': 'done'})
    total_voice = await db.ai_jobs.count_documents({'type': 'voice_clone', 'status': 'done'})
    total_llm = 0

    # Credits
    try:
        tx_today = await db.credit_transactions.find({'created_at': {'$gte': today_start.isoformat()}, 'delta': {'$lt': 0}}, {'delta': 1, '_id': 0}).to_list(10000)
        credits_used_today = abs(sum(t.get('delta', 0) for t in tx_today))
        tx_month = await db.credit_transactions.find({'created_at': {'$gte': month_start.isoformat()}, 'delta': {'$lt': 0}}, {'delta': 1, '_id': 0}).to_list(10000)
        credits_used_month = abs(sum(t.get('delta', 0) for t in tx_month))
        tx_granted = await db.credit_transactions.find({'delta': {'$gt': 0}}, {'delta': 1, '_id': 0}).to_list(10000)
        credits_granted = sum(t.get('delta', 0) for t in tx_granted)
    except:
        credits_used_today = credits_used_month = credits_granted = 0

    return {
        'mrr': mrr,
        'arr': arr,
        'total_users': total_users,
        'active_users': active_users,
        'subscribers': subscribers,
        'ai_jobs_today': ai_jobs_today,
        'total_videos': total_videos,
        'total_images': total_images,
        'total_voice': total_voice,
        'total_llm': total_llm,
        'credits_used_today': credits_used_today,
        'credits_used_month': credits_used_month,
        'credits_granted': credits_granted,
        'hf_token_set': bool(os.getenv('HF_TOKEN')),
        'groq_set': bool(os.getenv('GROQ_API_KEY')),
        'openrouter_set': bool(os.getenv('OPENROUTER_KEY')),
    }


@router.get('/chat/sessions')
async def chat_sessions(user=Depends(get_current_admin)):
    pipeline = [
        {'$sort': {'created_at': -1}},
        {'$group': {'_id': '$session_id', 'last': {'$first': '$text'}, 'created_at': {'$first': '$created_at'}, 'count': {'$sum': 1}}},
        {'$sort': {'created_at': -1}},
        {'$limit': 30},
    ]
    sessions = await db.admin_chat.aggregate(pipeline).to_list(30)
    return [{'session_id': s['_id'], 'last': s['last'], 'created_at': s['created_at'], 'count': s['count']} for s in sessions]
