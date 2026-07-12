"""Advanced analytics — funnels, retention, churn, conversion."""
from datetime import datetime, timezone, timedelta
from db import db


async def funnel_analysis(steps: list, days: int = 30):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    results = []
    for i, step in enumerate(steps):
        count = await db.events.count_documents({'event': step, 'timestamp': {'$gte': since}})
        results.append({'step': step, 'count': count, 'order': i + 1})
    for i in range(1, len(results)):
        prev = results[i - 1]['count']
        results[i]['conversion_rate'] = round(results[i]['count'] / prev * 100, 1) if prev else 0
    return {'steps': results, 'days': days}


async def retention_cohort(days: int = 30):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    pipeline = [
        {'$match': {'created_at': {'$gte': since}}},
        {'$group': {
            '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': {'$toDate': '$created_at'}}},
            'new_users': {'$sum': 1}
        }},
        {'$sort': {'_id': 1}}
    ]
    cohorts = await db.users.aggregate(pipeline).to_list(days)
    return {'cohorts': [{'date': c['_id'], 'new_users': c['new_users']} for c in cohorts]}


async def churn_analysis(days: int = 30):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    active_users = await db.events.distinct('user_id', {'timestamp': {'$gte': since}})
    total_users = await db.users.count_documents({})
    churned = total_users - len(active_users)
    return {
        'total_users': total_users,
        'active_users': len(active_users),
        'churned_users': churned,
        'churn_rate': round(churned / total_users * 100, 1) if total_users else 0,
        'days': days
    }


async def conversion_metrics(days: int = 30):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    signups = await db.users.count_documents({'created_at': {'$gte': since}})
    orders = await db.orders.count_documents({'created_at': {'$gte': since}})
    credits_used = await db.credits_transactions.count_documents({'created_at': {'$gte': since}})
    return {
        'signups': signups,
        'orders': orders,
        'credits_used': credits_used,
        'signup_to_order': round(orders / signups * 100, 1) if signups else 0,
        'days': days
    }
