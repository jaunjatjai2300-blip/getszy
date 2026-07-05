"""AI Operations Dashboard — consolidated metrics across all agents (Builder, Admin Chat, Tutor)."""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
from db import db
from auth import get_current_admin
from llm_provider import provider_info

router = APIRouter(prefix='/admin/ai-ops', tags=['ai-ops'])


def _today_start():
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def _week_start():
    return (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()


@router.get('/stats', dependencies=[Depends(get_current_admin)])
async def stats():
    today = _today_start()
    week = _week_start()

    # Builder
    builder_total = await db.builder_projects.count_documents({})
    builder_today = await db.builder_projects.count_documents({'created_at': {'$gte': today}})
    builder_week = await db.builder_projects.count_documents({'created_at': {'$gte': week}})

    # Admin Chat
    chat_total = await db.admin_chat.count_documents({'role': 'user'})
    chat_today = await db.admin_chat.count_documents({'role': 'user', 'created_at': {'$gte': today}})
    chat_intents_cursor = db.admin_chat.aggregate([
        {'$match': {'role': 'assistant', 'intent': {'$ne': None}}},
        {'$group': {'_id': '$intent', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 10},
    ])
    chat_intents = [{'intent': d['_id'], 'count': d['count']} async for d in chat_intents_cursor]

    # Tutor
    tutor_total = await db.tutor_messages.count_documents({})
    tutor_today = await db.tutor_messages.count_documents({'created_at': {'$gte': today}})

    # Latest activity feed (mix of all agents)
    builder_acts = await db.builder_projects.find({}, {'_id': 0, 'id': 1, 'name': 1, 'user_id': 1, 'created_at': 1}).sort('created_at', -1).limit(8).to_list(8)
    chat_acts = await db.admin_chat.find({'role': 'user'}, {'_id': 0, 'text': 1, 'created_at': 1, 'session_id': 1}).sort('created_at', -1).limit(8).to_list(8)
    tutor_acts = await db.tutor_messages.find({}, {'_id': 0, 'user_msg': 1, 'course_slug': 1, 'created_at': 1}).sort('created_at', -1).limit(8).to_list(8)

    feed = []
    for b in builder_acts:
        feed.append({'agent': 'Builder', 'icon': 'wand', 'label': f"Built: {b.get('name', '')}", 'at': b['created_at']})
    for c in chat_acts:
        feed.append({'agent': 'Admin Chat', 'icon': 'bot', 'label': (c.get('text', '') or '')[:60], 'at': c['created_at']})
    for t in tutor_acts:
        feed.append({'agent': 'AI Tutor', 'icon': 'graduation', 'label': f"[{t.get('course_slug', '')}] {(t.get('user_msg', '') or '')[:50]}", 'at': t['created_at']})
    feed.sort(key=lambda x: x['at'], reverse=True)
    feed = feed[:20]

    # Builds by day (last 7)
    series = []
    now = datetime.now(timezone.utc)
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        nxt = day + timedelta(days=1)
        n = await db.builder_projects.count_documents({'created_at': {'$gte': day.isoformat(), '$lt': nxt.isoformat()}})
        c = await db.admin_chat.count_documents({'role': 'user', 'created_at': {'$gte': day.isoformat(), '$lt': nxt.isoformat()}})
        t = await db.tutor_messages.count_documents({'created_at': {'$gte': day.isoformat(), '$lt': nxt.isoformat()}})
        series.append({'date': day.strftime('%a'), 'builds': n, 'chats': c, 'tutor': t})

    return {
        'engine': provider_info(),
        'agents': [
            {'name': 'Builder', 'description': 'Talk-to-Build site generator', 'status': 'online', 'total': builder_total, 'today': builder_today, 'week': builder_week},
            {'name': 'Admin Chat', 'description': 'Natural-language store ops', 'status': 'online', 'total': chat_total, 'today': chat_today, 'week': None},
            {'name': 'AI Tutor', 'description': 'Course-aware tutor', 'status': 'online', 'total': tutor_total, 'today': tutor_today, 'week': None},
        ],
        'intents': chat_intents,
        'feed': feed,
        'series_7d': series,
    }
