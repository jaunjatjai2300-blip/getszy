import os
import uuid
import asyncio
import subprocess
import psutil
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth import get_current_admin
from db import db, client

router = APIRouter(prefix='/admin/founder', tags=['founder'])


def _now():
    return datetime.now(timezone.utc).isoformat()


def _today_start():
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def _days_ago(n):
    return (datetime.now(timezone.utc) - timedelta(days=n)).replace(hour=0, minute=0, second=0, microsecond=0)


async def _check_redis():
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url('redis://localhost:6379', socket_connect_timeout=2)
        await r.ping()
        await r.close()
        return {'status': 'healthy'}
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}


async def _check_ollama():
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as hx:
            resp = await hx.get('http://host.docker.internal:11434/api/tags')
            data = resp.json()
            models = [m['name'] for m in data.get('models', [])]
            return {'status': 'healthy', 'models': models}
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}


@router.get('/health-summary')
async def health_summary(_=Depends(get_current_admin)):
    services = {}
    try:
        await client.admin.command('ping')
        services['mongodb'] = {'status': 'healthy'}
    except Exception as e:
        services['mongodb'] = {'status': 'unhealthy', 'error': str(e)}

    services['redis'] = await _check_redis()
    services['ollama'] = await _check_ollama()

    disk = psutil.disk_usage('/')
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.5)

    overall = 'healthy' if all(s['status'] == 'healthy' for s in services.values()) else 'degraded'

    return {
        'status': overall,
        'timestamp': _now(),
        'services': services,
        'system': {
            'cpu_percent': cpu,
            'ram_total_gb': round(mem.total / (1024**3), 2),
            'ram_used_gb': round(mem.used / (1024**3), 2),
            'ram_percent': mem.percent,
            'disk_total_gb': round(disk.total / (1024**3), 2),
            'disk_used_gb': round(disk.used / (1024**3), 2),
            'disk_percent': round(disk.used / disk.total * 100, 1),
        }
    }


@router.get('/kpi')
async def kpi(_=Depends(get_current_admin)):
    today_start = _today_start().isoformat()

    total_users = await db.users.count_documents({})
    active_subscriptions = await db.subscriptions.count_documents({'status': 'active'})
    mrr_cursor = db.subscriptions.aggregate([
        {'$match': {'status': 'active'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ])
    mrr_result = await mrr_cursor.to_list(1)
    mrr = mrr_result[0]['total'] if mrr_result else 0

    revenue_pipeline = db.orders.aggregate([
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ])
    revenue_result = await revenue_pipeline.to_list(1)
    total_revenue = revenue_result[0]['total'] if revenue_result else 0

    today_orders = db.orders.aggregate([
        {'$match': {'created_at': {'$gte': today_start}}},
        {'$group': {'_id': None, 'count': {'$sum': 1}, 'revenue': {'$sum': '$amount'}}}
    ])
    today_result = await today_orders.to_list(1)
    orders_today = today_result[0]['count'] if today_result else 0
    revenue_today = today_result[0]['revenue'] if today_result else 0

    ai_jobs_today = await db.video_jobs.count_documents({'created_at': {'$gte': today_start}})
    credits_today = db.users.aggregate([
        {'$match': {'created_at': {'$gte': today_start}}},
        {'$group': {'_id': None, 'total': {'$sum': '$credits_used'}}}
    ])
    credits_result = await credits_today.to_list(1)
    credits_used_today = credits_result[0]['total'] if credits_result else 0

    total_projects = await db.build_projects.count_documents({})
    if total_projects == 0:
        total_projects = await db.builder_projects.count_documents({})

    active_deployments = await db.deployments.count_documents({'status': {'$in': ['live', 'building', 'deploying']}})
    failed_jobs = await db.queue.count_documents({'status': 'failed'})
    low_stock = await db.products.count_documents({'stock': {'$lte': 5, '$gte': 0}})

    return {
        'total_users': total_users,
        'active_subscribers': active_subscriptions,
        'mrr': mrr,
        'total_revenue': total_revenue,
        'revenue_today': revenue_today,
        'orders_today': orders_today,
        'ai_jobs_today': ai_jobs_today,
        'credits_used_today': credits_used_today,
        'total_projects': total_projects,
        'active_deployments': active_deployments,
        'failed_jobs': failed_jobs,
        'low_stock_count': low_stock,
        'timestamp': _now()
    }


@router.get('/activity-feed')
async def activity_feed(_=Depends(get_current_admin)):
    feed = []

    orders = await db.orders.find({}, {'_id': 0}).sort('created_at', -1).to_list(5)
    for o in orders:
        feed.append({'type': 'order', 'message': f"Order #{o.get('id', '')[:8]} - ${o.get('amount', 0)}", 'timestamp': o.get('created_at', '')})

    users = await db.users.find({}, {'_id': 0}).sort('created_at', -1).to_list(5)
    for u in users:
        feed.append({'type': 'signup', 'message': f"New user: {u.get('email', u.get('id', ''))}", 'timestamp': u.get('created_at', '')})

    jobs = await db.video_jobs.find({}, {'_id': 0}).sort('created_at', -1).to_list(5)
    for j in jobs:
        feed.append({'type': 'ai_job', 'message': f"AI job: {j.get('type', 'video')} - {j.get('status', 'unknown')}", 'timestamp': j.get('created_at', '')})

    deploys = await db.deployments.find({}, {'_id': 0}).sort('created_at', -1).to_list(5)
    for d in deploys:
        feed.append({'type': 'deploy', 'message': f"Deploy {d.get('id', '')[:8]} - {d.get('status', 'unknown')}", 'timestamp': d.get('created_at', '')})

    feed.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return {'feed': feed[:20], 'timestamp': _now()}


@router.get('/system-health')
async def system_health(_=Depends(get_current_admin)):
    health = {'timestamp': _now(), 'services': {}, 'system': {}}

    try:
        await client.admin.command('ping')
        health['services']['mongodb'] = 'healthy'
    except Exception as e:
        health['services']['mongodb'] = f'unhealthy: {e}'

    health['services']['redis'] = (await _check_redis())['status']
    health['services']['ollama'] = (await _check_ollama())['status']

    disk = psutil.disk_usage('/')
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.5)
    health['system'] = {
        'cpu_percent': cpu,
        'ram_total_gb': round(mem.total / (1024**3), 2),
        'ram_used_gb': round(mem.used / (1024**3), 2),
        'ram_percent': mem.percent,
        'disk_total_gb': round(disk.total / (1024**3), 2),
        'disk_used_gb': round(disk.used / (1024**3), 2),
        'disk_percent': round(disk.used / disk.total * 100, 1),
    }

    try:
        result = subprocess.run(['docker', 'ps', '--format', '{{.Names}}\t{{.Status}}'], capture_output=True, text=True, timeout=5)
        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                containers.append({'name': parts[0], 'status': parts[1] if len(parts) > 1 else 'unknown'})
        health['services']['docker'] = {'status': 'healthy', 'containers': containers}
    except Exception as e:
        health['services']['docker'] = {'status': 'unavailable', 'error': str(e)}

    try:
        import ssl
        import socket
        hostname = 'getszy.com'
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=hostname) as s:
            s.settimeout(5)
            s.connect((hostname, 443))
            cert = s.getpeercert()
            expires = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
            days_left = (expires - datetime.now(timezone.utc)).days
            health['ssl'] = {'status': 'valid' if days_left > 30 else 'expiring_soon', 'expires_in_days': days_left}
    except Exception as e:
        health['ssl'] = {'status': 'unavailable', 'error': str(e)}

    return health


@router.get('/alerts')
async def alerts(_=Depends(get_current_admin)):
    alert_list = []

    low_stock = await db.products.count_documents({'stock': {'$lte': 5, '$gte': 0}})
    if low_stock > 0:
        alert_list.append({'type': 'low_stock', 'severity': 'warning', 'message': f'{low_stock} products with low stock', 'count': low_stock})

    total_users = await db.users.count_documents({})
    mrr_cursor = db.subscriptions.aggregate([
        {'$match': {'status': 'active'}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ])
    mrr_result = await mrr_cursor.to_list(1)
    mrr = mrr_result[0]['total'] if mrr_result else 0
    if mrr == 0 and total_users > 10:
        alert_list.append({'type': 'zero_mrr', 'severity': 'critical', 'message': 'Zero MRR despite active users', 'user_count': total_users})

    disk = psutil.disk_usage('/')
    disk_pct = round(disk.used / disk.total * 100, 1)
    if disk_pct > 80:
        alert_list.append({'type': 'disk_high', 'severity': 'critical', 'message': f'Disk usage at {disk_pct}%', 'percent': disk_pct})

    failed_jobs = await db.queue.count_documents({'status': 'failed'})
    if failed_jobs > 0:
        alert_list.append({'type': 'failed_jobs', 'severity': 'warning', 'message': f'{failed_jobs} failed jobs in queue', 'count': failed_jobs})

    api_keys_set = os.environ.get('OPENAI_API_KEY', '')
    if not api_keys_set:
        alert_list.append({'type': 'no_api_keys', 'severity': 'warning', 'message': 'No OpenAI API key configured'})

    error_pipeline = [
        {'$match': {'status_code': {'$gte': 500}}},
        {'$group': {'_id': None, 'count': {'$sum': 1}}}
    ]
    error_result = await db.request_logs.aggregate(error_pipeline).to_list(1)
    total_errors = error_result[0]['count'] if error_result else 0
    total_requests = await db.request_logs.count_documents({})
    if total_requests > 100 and total_errors / max(total_requests, 1) > 0.05:
        alert_list.append({'type': 'high_error_rate', 'severity': 'warning', 'message': f'Error rate: {round(total_errors/total_requests*100, 1)}%', 'errors': total_errors, 'total': total_requests})

    return {'alerts': alert_list, 'count': len(alert_list), 'timestamp': _now()}


@router.get('/revenue-chart')
async def revenue_chart(range: str = Query('7d', regex=r'^\d+d$'), _=Depends(get_current_admin)):
    days = int(range[:-1])
    results = []
    for i in range(days - 1, -1, -1):
        day = _days_ago(i)
        next_day = day + timedelta(days=1)
        pipeline = db.orders.aggregate([
            {'$match': {'created_at': {'$gte': day.isoformat(), '$lt': next_day.isoformat()}}},
            {'$group': {'_id': None, 'revenue': {'$sum': '$amount'}, 'orders': {'$sum': 1}}}
        ])
        data = await pipeline.to_list(1)
        results.append({
            'date': day.strftime('%Y-%m-%d'),
            'revenue': data[0]['revenue'] if data else 0,
            'orders': data[0]['orders'] if data else 0
        })
    return {'range': range, 'data': results, 'timestamp': _now()}


@router.get('/growth-metrics')
async def growth_metrics(_=Depends(get_current_admin)):
    user_growth = []
    revenue_growth = []
    subscriber_growth = []
    ai_growth = []

    for i in range(29, -1, -1):
        day = _days_ago(i)
        next_day = day + timedelta(days=1)
        label = day.strftime('%Y-%m-%d')

        signups = await db.users.count_documents({'created_at': {'$gte': day.isoformat(), '$lt': next_day.isoformat()}})
        user_growth.append({'date': label, 'count': signups})

        rev_pipeline = db.orders.aggregate([
            {'$match': {'created_at': {'$gte': day.isoformat(), '$lt': next_day.isoformat()}}},
            {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
        ])
        rev_data = await rev_pipeline.to_list(1)
        revenue_growth.append({'date': label, 'revenue': rev_data[0]['total'] if rev_data else 0})

        new_subs = await db.subscriptions.count_documents({'created_at': {'$gte': day.isoformat(), '$lt': next_day.isoformat()}})
        subscriber_growth.append({'date': label, 'count': new_subs})

        ai_jobs = await db.video_jobs.count_documents({'created_at': {'$gte': day.isoformat(), '$lt': next_day.isoformat()}})
        ai_growth.append({'date': label, 'count': ai_jobs})

    return {
        'user_growth': user_growth,
        'revenue_growth': revenue_growth,
        'subscriber_growth': subscriber_growth,
        'ai_usage_growth': ai_growth,
        'timestamp': _now()
    }
