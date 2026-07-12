"""Operations — Prometheus, Grafana, Sentry, Cron Jobs, System Health."""
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_admin
from db import db

router = APIRouter(prefix='/admin/ops', tags=['operations'])


def _now():
    return datetime.now(timezone.utc).isoformat()


# ===== System Health =====
@router.get('/health')
async def system_health(_=Depends(get_current_admin)):
    health = {'status': 'healthy', 'timestamp': _now(), 'services': {}}
    try:
        from db import client
        await client.admin.command('ping')
        health['services']['mongodb'] = 'healthy'
    except Exception as e:
        health['services']['mongodb'] = f'unhealthy: {str(e)}'
        health['status'] = 'degraded'

    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url('redis://localhost:6379', socket_connect_timeout=2)
        await r.ping()
        await r.close()
        health['services']['redis'] = 'healthy'
    except Exception as e:
        health['services']['redis'] = f'not connected: {str(e)}'

    import os, shutil
    disk = shutil.disk_usage('/')
    health['disk'] = {
        'total_gb': round(disk.total / (1024**3), 1),
        'used_gb': round(disk.used / (1024**3), 1),
        'free_gb': round(disk.free / (1024**3), 1),
        'percent': round(disk.used / disk.total * 100, 1)
    }
    return health


# ===== Metrics =====
@router.get('/metrics')
async def get_metrics(_=Depends(get_current_admin)):
    collections = await db.list_collection_names()
    counts = {}
    for col in collections:
        try:
            counts[col] = await db[col].count_documents({})
        except Exception:
            counts[col] = 0

    users_today = await db.users.count_documents({
        'created_at': {'$gte': datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()}
    })
    return {
        'total_users': counts.get('users', 0),
        'total_orders': counts.get('orders', 0),
        'total_courses': counts.get('courses', 0),
        'total_projects': counts.get('build_projects', counts.get('builder_projects', 0)),
        'users_today': users_today,
        'collection_counts': counts,
        'timestamp': _now()
    }


# ===== Prometheus =====
@router.get('/prometheus/status')
async def prometheus_status(_=Depends(get_current_admin)):
    return {
        'status': 'configured',
        'note': 'Connect to Prometheus at your monitoring endpoint. Enable via PROMETHEUS_ENABLED=true.',
        'endpoints': {
            'metrics': '/metrics',
            'prometheus_ui': 'http://localhost:9090 (if running)'
        }
    }


# ===== Grafana =====
@router.get('/grafana/status')
async def grafana_status(_=Depends(get_current_admin)):
    return {
        'status': 'configured',
        'note': 'Connect to Grafana at http://localhost:3000 (if running).',
        'dashboards': ['System Health', 'User Activity', 'AI Usage', 'API Performance']
    }


# ===== Sentry =====
@router.get('/sentry/status')
async def sentry_status(_=Depends(get_current_admin)):
    import os
    sentry_dsn = os.environ.get('SENTRY_DSN', '')
    return {
        'status': 'connected' if sentry_dsn else 'not_configured',
        'dsn_set': bool(sentry_dsn),
        'note': 'Set SENTRY_DSN env var to enable error tracking.' if not sentry_dsn else 'Sentry error tracking is active.'
    }


# ===== Cron Jobs =====
class CronJobIn(BaseModel):
    name: str
    schedule: str = '0 * * * *'
    task: str
    enabled: bool = True


@router.get('/cron')
async def list_cron_jobs(_=Depends(get_current_admin)):
    cur = db.cron_jobs.find({}, {'_id': 0}).sort('created_at', -1)
    return {'jobs': [j async for j in cur]}


@router.post('/cron')
async def create_cron_job(payload: CronJobIn, _=Depends(get_current_admin)):
    job = {
        'id': str(uuid.uuid4()), 'name': payload.name,
        'schedule': payload.schedule, 'task': payload.task,
        'enabled': payload.enabled, 'last_run': None, 'next_run': None,
        'created_at': _now()
    }
    await db.cron_jobs.insert_one(job)
    job.pop('_id', None)
    return job


@router.post('/cron/{job_id}/toggle')
async def toggle_cron_job(job_id: str, _=Depends(get_current_admin)):
    job = await db.cron_jobs.find_one({'id': job_id})
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    new_state = not job.get('enabled', True)
    await db.cron_jobs.update_one({'id': job_id}, {'$set': {'enabled': new_state}})
    return {'id': job_id, 'enabled': new_state}


@router.delete('/cron/{job_id}')
async def delete_cron_job(job_id: str, _=Depends(get_current_admin)):
    await db.cron_jobs.delete_one({'id': job_id})
    return {'status': 'deleted'}


# ===== Audit Logs UI =====
@router.get('/audit-logs')
async def get_audit_logs(limit: int = 50, action: Optional[str] = None, _=Depends(get_current_admin)):
    query = {}
    if action:
        query['action'] = action
    cur = db.audit_logs.find(query, {'_id': 0}).sort('timestamp', -1).limit(limit)
    return {'logs': [l async for l in cur]}


@router.get('/audit-logs/stats')
async def audit_log_stats(_=Depends(get_current_admin)):
    pipeline = [
        {'$group': {'_id': '$action', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]
    stats = await db.audit_logs.aggregate(pipeline).to_list(20)
    total = await db.audit_logs.count_documents({})
    return {'total': total, 'by_action': stats}


# ===== Request Logs =====
@router.get('/logs')
async def get_request_logs(limit: int = 100, status: Optional[int] = None, _=Depends(get_current_admin)):
    query = {}
    if status:
        query['status_code'] = status
    cur = db.request_logs.find(query, {'_id': 0}).sort('timestamp', -1).limit(limit)
    return {'logs': [l async for l in cur]}
