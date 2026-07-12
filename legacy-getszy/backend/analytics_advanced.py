"""Advanced analytics — funnels, retention, churn, conversion."""
import logging
from datetime import datetime, timezone, timedelta
from db import db

logger = logging.getLogger('getszy.analytics')


async def get_funnel_analytics(days: int = 30) -> dict:
    """Conversion funnel: Visit → Signup → First Purchase → Repeat Purchase."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    total_users = await db.users.count_documents({'created_at': {'$gte': cutoff}})
    total_orders = await db.orders.count_documents({'created_at': {'$gte': cutoff}})
    repeat_orders = 0
    pipeline = [
        {'$match': {'created_at': {'$gte': cutoff}}},
        {'$group': {'_id': '$user_id', 'count': {'$sum': 1}}},
        {'$match': {'count': {'$gt': 1}}},
    ]
    async for doc in db.orders.aggregate(pipeline):
        repeat_orders += 1

    visitors = total_users * 5  # rough estimate
    return {
        'period_days': days,
        'visitors': visitors,
        'signups': total_users,
        'first_purchase': total_orders,
        'repeat_purchase': repeat_orders,
        'visitor_to_signup': round(total_users / max(visitors, 1) * 100, 1),
        'signup_to_purchase': round(total_orders / max(total_users, 1) * 100, 1),
        'purchase_to_repeat': round(repeat_orders / max(total_orders, 1) * 100, 1),
    }


async def get_retention_analysis(days: int = 30) -> dict:
    """User retention analysis."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    weekly = []
    for i in range(4):
        week_start = (datetime.now(timezone.utc) - timedelta(weeks=i+1)).isoformat()
        week_end = (datetime.now(timezone.utc) - timedelta(weeks=i)).isoformat()

        new_users = await db.users.count_documents({
            'created_at': {'$gte': week_start, '$lt': week_end}
        })
        active_users = await db.orders.count_documents({
            'created_at': {'$gte': week_start, '$lt': week_end}
        })

        weekly.append({
            'week': f'Week -{i+1}',
            'new_users': new_users,
            'active_users': active_users,
            'retention_rate': round(active_users / max(new_users, 1) * 100, 1),
        })

    return {'retention_weekly': list(reversed(weekly))}


async def get_churn_analysis(days: int = 30) -> dict:
    """Churn analysis — users who haven't been active."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    inactive_cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    total = await db.users.count_documents({})
    active_recent = await db.users.count_documents({'created_at': {'$gte': inactive_cutoff}})
    churned = total - active_recent

    return {
        'total_users': total,
        'active_last_30d': active_recent,
        'churned': churned,
        'churn_rate': round(churned / max(total, 1) * 100, 1),
    }


async def get_conversion_metrics(days: int = 30) -> dict:
    """Conversion metrics."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    total_orders = await db.orders.count_documents({'created_at': {'$gte': cutoff}})
    total_revenue = 0
    pipeline = [
        {'$match': {'created_at': {'$gte': cutoff}}},
        {'$group': {'_id': None, 'total': {'$sum': '$total'}}},
    ]
    async for doc in db.orders.aggregate(pipeline):
        total_revenue = doc.get('total', 0)

    users_with_orders = 0
    user_pipeline = [
        {'$match': {'created_at': {'$gte': cutoff}}},
        {'$group': {'_id': '$user_id'}},
    ]
    async for doc in db.orders.aggregate(user_pipeline):
        users_with_orders += 1

    total_users = await db.users.count_documents({})

    return {
        'total_orders': total_orders,
        'total_revenue': round(total_revenue, 2),
        'avg_order_value': round(total_revenue / max(total_orders, 1), 2),
        'conversion_rate': round(users_with_orders / max(total_users, 1) * 100, 1),
        'period_days': days,
    }
