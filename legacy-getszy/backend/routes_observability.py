"""Observability + SLA (Tier 2 #14).

Aggregates request logs into uptime / error-rate / latency SLIs so the
admin can see platform health at a glance.
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from auth import get_current_admin
from db import db

router = APIRouter(prefix='/admin/observability', tags=['observability'])


def _percentile(sorted_vals, pct):
    if not sorted_vals:
        return 0
    k = max(0, min(len(sorted_vals) - 1, int(round((pct / 100) * (len(sorted_vals) - 1)))))
    return sorted_vals[k]


async def compute_sla(hours: int = 24):
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    pipe = [
        {'$match': {'time': {'$gte': since}}},
        {'$group': {
            '_id': None,
            'total': {'$sum': 1},
            'errors': {'$sum': {'$cond': [{'$gte': ['$status', 500]}, 1, 0]}},
            'latencies': {'$push': '$duration_ms'},
        }},
    ]
    rows = [r async for r in db.request_logs.aggregate(pipe)]
    if not rows:
        return {'total': 0, 'errors': 0, 'error_rate': 0.0, 'p95_ms': 0, 'uptime_pct': 100.0, 'window': f'{hours}h'}
    agg = rows[0]
    total = agg.get('total', 0) or 0
    errors = agg.get('errors', 0) or 0
    lats = sorted([l for l in (agg.get('latencies') or []) if isinstance(l, (int, float))])
    p95 = _percentile(lats, 95)
    uptime = round((1 - errors / total) * 100, 2) if total else 100.0
    return {
        'total': total,
        'errors': errors,
        'error_rate': round(errors / total * 100, 2) if total else 0.0,
        'p95_ms': p95,
        'uptime_pct': uptime,
        'window': f'{hours}h',
    }


@router.get('/sla')
async def sla(hours: int = 24, _=Depends(get_current_admin)):
    return await compute_sla(hours)


@router.get('/summary')
async def summary(_=Depends(get_current_admin)):
    sla24 = await compute_sla(24)
    # quick counts across collections
    counts = {}
    for name in ('users', 'orders', 'products', 'gs_invoices', 'automations'):
        try:
            counts[name] = await db[name].count_documents({})
        except Exception:
            counts[name] = 0
    return {'sla': sla24, 'counts': counts}
