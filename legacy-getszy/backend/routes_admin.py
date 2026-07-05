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
