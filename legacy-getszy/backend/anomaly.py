"""Anomaly detection + auto-block (Tier 2 #13).

Detects brute-force / abuse patterns from audit + request logs and
auto-blocks offending IPs. Exposes an aggregation endpoint for the
security dashboard.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from db import db

FAILED_LOGIN_WINDOW = timedelta(minutes=15)
FAILED_LOGIN_THRESHOLD = 5


def _now():
    return datetime.now(timezone.utc).isoformat()


async def _recent_failed(ip: str, since: datetime):
    cur = db.audit_logs.find({
        'action': 'failed_login',
        'ip': ip,
        'ts': {'$gte': since.isoformat()},
    }, {'_id': 0})
    return [a async for a in cur]


async def record_login_failure(ip: str, email: str, threshold: int = FAILED_LOGIN_THRESHOLD) -> bool:
    """After a failed login, auto-block the IP if it looks like brute force."""
    since = datetime.now(timezone.utc) - FAILED_LOGIN_WINDOW
    count = len(await _recent_failed(ip, since))
    if count < threshold:
        return False
    existing = await db.blocked_ips.find_one({'ip': ip})
    if existing:
        return True
    await db.blocked_ips.insert_one({
        'id': uuid.uuid4().hex,
        'ip': ip,
        'reason': f'Auto-blocked by anomaly engine: {count} failed logins in 15m',
        'source': 'anomaly',
        'created_at': _now(),
    })
    # notify admins
    try:
        from websocket_manager import manager
        cur = db.users.find({'role': 'admin'}, {'id': 1, '_id': 0})
        async for u in cur:
            notif = {
                'id': uuid.uuid4().hex, 'user_id': u['id'],
                'title': 'IP auto-blocked', 'type': 'error', 'read': False,
                'message': f'{ip} blocked after {count} failed logins (brute force)',
                'created_at': _now(), 'source': 'anomaly',
            }
            await db.notifications.insert_one(notif)
            try:
                manager.send_to_user(u['id'], {'type': 'notification', 'title': notif['title'], 'message': notif['message']})
            except Exception:
                pass
    except Exception:
        pass
    # live feed
    try:
        from live_events import broadcast_admin_event
        broadcast_admin_event('ip_blocked', {'ip': ip, 'reason': 'brute force', 'count': count})
    except Exception:
        pass
    return True


async def get_anomalies(hours: int = 24):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    since_iso = since.isoformat()
    ip_pipe = [
        {'$match': {'action': 'failed_login', 'ts': {'$gte': since_iso}}},
        {'$group': {'_id': '$ip', 'count': {'$sum': 1}, 'emails': {'$addToSet': '$email'}}},
        {'$sort': {'count': -1}},
        {'$limit': 20},
    ]
    ip_risk = [a async for a in db.audit_logs.aggregate(ip_pipe)]
    err_pipe = [
        {'$match': {'level': 'error', 'time': {'$gte': since_iso}}},
        {'$group': {'_id': '$ip', 'errors': {'$sum': 1}}},
        {'$sort': {'errors': -1}},
        {'$limit': 10},
    ]
    request_errors = [e async for e in db.request_logs.aggregate(err_pipe)]
    blocked = [b async for b in db.blocked_ips.find({}, {'_id': 0}).sort('created_at', -1).limit(20)]
    return {'ip_risk': ip_risk, 'request_errors': request_errors, 'blocked_ips': blocked, 'window': f'{hours}h'}
