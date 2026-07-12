"""Audit logging system — tracks all important actions for security compliance."""
import logging
from datetime import datetime, timezone
from db import db
from models import _id, _now

logger = logging.getLogger('getszy.audit')

# Actions to track
ACTION_SIGNUP = 'user.signup'
ACTION_LOGIN = 'user.login'
ACTION_LOGOUT = 'user.logout'
ACTION_PASSWORD_CHANGE = 'user.password_change'
ACTION_ROLE_CHANGE = 'user.role_change'
ACTION_PRODUCT_CREATE = 'product.create'
ACTION_PRODUCT_UPDATE = 'product.update'
ACTION_PRODUCT_DELETE = 'product.delete'
ACTION_ORDER_CREATE = 'order.create'
ACTION_ORDER_UPDATE = 'order.update'
ACTION_ORDER_CANCEL = 'order.cancel'
ACTION_PAYMENT = 'payment.processed'
ACTION_REFUND = 'payment.refunded'
ACTION_AI_REQUEST = 'ai.request'
ACTION_DEPLOY = 'deploy.triggered'
ACTION_SETTINGS_CHANGE = 'settings.changed'
ACTION_API_KEY_CREATE = 'api_key.created'
ACTION_API_KEY_DELETE = 'api_key.deleted'
ACTION_BULK_ACTION = 'bulk.action'
ACTION_EXPORT = 'data.export'
ACTION_IMPORT = 'data.import'


async def log_action(
    action: str,
    user_id: str = None,
    user_email: str = None,
    details: dict = None,
    ip_address: str = None,
    user_agent: str = None,
    status: str = 'success',
    resource_type: str = None,
    resource_id: str = None,
):
    """Log an audit event."""
    entry = {
        'id': _id(),
        'action': action,
        'user_id': user_id,
        'user_email': user_email,
        'details': details or {},
        'ip_address': ip_address,
        'user_agent': user_agent,
        'status': status,
        'resource_type': resource_type,
        'resource_id': resource_id,
        'created_at': _now(),
    }

    try:
        await db.audit_logs.insert_one(entry)
    except Exception as e:
        logger.error(f'Failed to write audit log: {e}')

    # Also log to stdout for monitoring
    logger.info(f'AUDIT: {action} user={user_email or user_id} status={status}')


async def get_audit_logs(
    user_id: str = None,
    action: str = None,
    resource_type: str = None,
    limit: int = 50,
    offset: int = 0,
) -> list:
    """Query audit logs with filters."""
    query = {}
    if user_id:
        query['user_id'] = user_id
    if action:
        query['action'] = {'$regex': action, '$options': 'i'}
    if resource_type:
        query['resource_type'] = resource_type

    cursor = db.audit_logs.find(query, {'_id': 0}).sort('created_at', -1).skip(offset).limit(limit)
    return await cursor.to_list(limit)


async def get_audit_stats(days: int = 30) -> dict:
    """Get audit statistics."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    total = await db.audit_logs.count_documents({'created_at': {'$gte': cutoff}})

    # Actions breakdown
    actions_cursor = db.audit_logs.aggregate([
        {'$match': {'created_at': {'$gte': cutoff}}},
        {'$group': {'_id': '$action', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 20},
    ])
    actions = [{'action': d['_id'], 'count': d['count']} async for d in actions_cursor]

    # Failed actions
    failed = await db.audit_logs.count_documents({
        'created_at': {'$gte': cutoff},
        'status': 'failed',
    })

    # Unique users
    users_cursor = db.audit_logs.aggregate([
        {'$match': {'created_at': {'$gte': cutoff}}},
        {'$group': {'_id': '$user_id'}},
    ])
    users = [d async for d in users_cursor]

    return {
        'total_events': total,
        'failed_events': failed,
        'unique_users': len(users),
        'top_actions': actions,
        'period_days': days,
    }
