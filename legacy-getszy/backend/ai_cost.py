"""AI cost tracking and benchmarking."""
import logging
from datetime import datetime, timezone, timedelta
from db import db
from models import _id, _now

logger = logging.getLogger('getszy.ai_cost')

# Approximate costs per 1M tokens (USD)
PROVIDER_COSTS = {
    'groq': {'input': 0.05, 'output': 0.10},
    'openrouter': {'input': 0.10, 'output': 0.30},
    'huggingface': {'input': 0.0, 'output': 0.0},
    'gemini': {'input': 0.075, 'output': 0.30},
    'ollama': {'input': 0.0, 'output': 0.0},
    'emergent': {'input': 2.50, 'output': 10.00},
}


async def log_ai_usage(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    user_id: str = None,
    agent: str = 'general',
    endpoint: str = '',
    latency_ms: int = 0,
):
    """Log AI API usage and cost."""
    costs = PROVIDER_COSTS.get(provider, {'input': 0, 'output': 0})
    cost_usd = (input_tokens * costs['input'] + output_tokens * costs['output']) / 1_000_000

    entry = {
        'id': _id(),
        'provider': provider,
        'model': model,
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'total_tokens': input_tokens + output_tokens,
        'cost_usd': cost_usd,
        'user_id': user_id,
        'agent': agent,
        'endpoint': endpoint,
        'latency_ms': latency_ms,
        'created_at': _now(),
    }
    await db.ai_usage.insert_one(entry)
    return entry


async def get_ai_usage_stats(days: int = 30) -> dict:
    """Get AI usage statistics."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    match = {'created_at': {'$gte': cutoff}}

    # Total usage
    pipeline = [
        {'$match': match},
        {'$group': {
            '_id': '$provider',
            'total_cost': {'$sum': '$cost_usd'},
            'total_tokens': {'$sum': '$total_tokens'},
            'requests': {'$sum': 1},
            'avg_latency': {'$avg': '$latency_ms'},
        }},
        {'$sort': {'total_cost': -1}},
    ]
    by_provider = []
    async for doc in db.ai_usage.aggregate(pipeline):
        by_provider.append({
            'provider': doc['_id'],
            'total_cost': round(doc['total_cost'], 4),
            'total_tokens': doc['total_tokens'],
            'requests': doc['requests'],
            'avg_latency': round(doc['avg_latency'], 0),
        })

    # By agent
    agent_pipeline = [
        {'$match': match},
        {'$group': {
            '_id': '$agent',
            'total_cost': {'$sum': '$cost_usd'},
            'requests': {'$sum': 1},
        }},
        {'$sort': {'total_cost': -1}},
    ]
    by_agent = []
    async for doc in db.ai_usage.aggregate(agent_pipeline):
        by_agent.append({
            'agent': doc['_id'],
            'total_cost': round(doc['total_cost'], 4),
            'requests': doc['requests'],
        })

    # Daily cost trend
    daily_pipeline = [
        {'$match': match},
        {'$group': {
            '_id': {'$substr': ['$created_at', 0, 10]},
            'cost': {'$sum': '$cost_usd'},
            'tokens': {'$sum': '$total_tokens'},
        }},
        {'$sort': {'_id': 1}},
    ]
    daily = []
    async for doc in db.ai_usage.aggregate(daily_pipeline):
        daily.append({'date': doc['_id'], 'cost': round(doc['cost'], 4), 'tokens': doc['tokens']})

    total_cost = sum(p['total_cost'] for p in by_provider)
    total_tokens = sum(p['total_tokens'] for p in by_provider)

    return {
        'total_cost_usd': round(total_cost, 4),
        'total_tokens': total_tokens,
        'by_provider': by_provider,
        'by_agent': by_agent,
        'daily_trend': daily,
        'period_days': days,
    }
