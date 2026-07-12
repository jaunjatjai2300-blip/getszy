"""AI usage cost tracking — per-provider, per-model, per-user."""
import uuid
from datetime import datetime, timezone
from db import db

COST_PER_1K_TOKENS = {
    'ollama': 0.0,
    'groq': 0.0002,
    'openrouter': 0.0003,
    'huggingface': 0.0001,
    'gemini': 0.0001,
    'openai': 0.006,
    'emergent': 0.001,
}


async def track_usage(provider: str, model: str, user_id: str, input_tokens: int = 0, output_tokens: int = 0):
    total_tokens = input_tokens + output_tokens
    rate = COST_PER_1K_TOKENS.get(provider, 0.001)
    cost = (total_tokens / 1000.0) * rate
    entry = {
        'id': str(uuid.uuid4()),
        'provider': provider, 'model': model,
        'user_id': user_id,
        'input_tokens': input_tokens, 'output_tokens': output_tokens,
        'total_tokens': total_tokens, 'cost_usd': round(cost, 8),
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    await db.ai_usage.insert_one(entry)
    return entry


async def get_user_usage(user_id: str, days: int = 30):
    since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    from datetime import timedelta
    since = since - timedelta(days=days)
    pipeline = [
        {'$match': {'user_id': user_id, 'timestamp': {'$gte': since.isoformat()}}},
        {'$group': {
            '_id': '$provider',
            'total_tokens': {'$sum': '$total_tokens'},
            'total_cost': {'$sum': '$cost_usd'},
            'requests': {'$sum': 1}
        }},
        {'$sort': {'total_cost': -1}}
    ]
    results = await db.ai_usage.aggregate(pipeline).to_list(20)
    total_pipeline = [
        {'$match': {'user_id': user_id, 'timestamp': {'$gte': since.isoformat()}}},
        {'$group': {'_id': None, 'total_cost': {'$sum': '$cost_usd'}, 'total_tokens': {'$sum': '$total_tokens'}}}
    ]
    totals = await db.ai_usage.aggregate(total_pipeline).to_list(1)
    total = totals[0] if totals else {'total_cost': 0, 'total_tokens': 0}
    return {
        'by_provider': results,
        'total_cost_usd': round(total.get('total_cost', 0), 6),
        'total_tokens': total.get('total_tokens', 0),
        'days': days
    }


async def get_global_usage(days: int = 7):
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    pipeline = [
        {'$match': {'timestamp': {'$gte': since}}},
        {'$group': {
            '_id': {'provider': '$provider', 'model': '$model'},
            'total_tokens': {'$sum': '$total_tokens'},
            'total_cost': {'$sum': '$cost_usd'},
            'requests': {'$sum': 1}
        }},
        {'$sort': {'total_cost': -1}}
    ]
    return await db.ai_usage.aggregate(pipeline).to_list(50)
