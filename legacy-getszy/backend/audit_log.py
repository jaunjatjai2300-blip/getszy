"""Audit log — track all security-relevant actions."""
import uuid
from datetime import datetime, timezone
from db import db


async def log(action: str, user_id: str = '', details: dict = None, ip: str = '', status: str = 'success'):
    entry = {
        'id': str(uuid.uuid4()),
        'action': action,
        'user_id': user_id,
        'details': details or {},
        'ip': ip,
        'status': status,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    try:
        await db.audit_logs.insert_one(entry)
    except Exception:
        pass


async def get_logs(user_id: str = '', action: str = '', limit: int = 50):
    query = {}
    if user_id:
        query['user_id'] = user_id
    if action:
        query['action'] = action
    cur = db.audit_logs.find(query, {'_id': 0}).sort('timestamp', -1).limit(limit)
    return [log async for log in cur]


async def get_stats():
    pipeline = [
        {'$group': {'_id': '$action', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]
    stats = await db.audit_logs.aggregate(pipeline).to_list(50)
    total = await db.audit_logs.count_documents({})
    return {'total': total, 'by_action': stats}
