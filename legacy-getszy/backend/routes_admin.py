from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from db import db
from auth import get_current_admin
from models import AdminChatIn, AdminChatMessage
from ai_chat import parse_intent, execute_intent
from datetime import datetime, timezone, timedelta
import uuid, os, secrets

router = APIRouter(prefix='/admin', tags=['admin'])


async def compute_stats(range_: str = 'today'):
    now = datetime.now(timezone.utc)
    if range_ == 'today':
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif range_ == 'week':
        since = now - timedelta(days=7)
    elif range_ == 'month':
        since = now - timedelta(days=30)
    else:
        since = None
    q = {}
    if since:
        q['created_at'] = {'$gte': since.isoformat()}
    orders = await db.orders.find(q, {'_id': 0}).to_list(5000)
    revenue = sum(o.get('total', 0) for o in orders)
    profit = sum(o.get('profit', 0) for o in orders)
    orders_count = len(orders)
    customers_count = await db.users.count_documents({'role': 'customer'})
    products_count = await db.products.count_documents({'is_active': True})
    low_stock = await db.products.count_documents({'stock': {'$lte': 5}})

    # 7-day revenue series
    series = []
    for i in range(6, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_orders = [o for o in (await db.orders.find({'created_at': {'$gte': day_start.isoformat(), '$lt': day_end.isoformat()}}, {'_id': 0}).to_list(1000))]
        series.append({
            'date': day_start.strftime('%a'),
            'revenue': round(sum(o.get('total', 0) for o in day_orders), 2),
            'orders': len(day_orders),
        })

    return {
        'range': range_,
        'revenue': round(revenue, 2),
        'profit': round(profit, 2),
        'orders_count': orders_count,
        'customers_count': customers_count,
        'products_count': products_count,
        'low_stock_count': low_stock,
        'series_7d': series,
        'recent_orders': sorted(orders, key=lambda x: x.get('created_at', ''), reverse=True)[:5],
    }


@router.get('/stats', dependencies=[Depends(get_current_admin)])
async def stats(range: str = 'today'):
    return await compute_stats(range)


@router.get('/customers', dependencies=[Depends(get_current_admin)])
async def customers():
    users = await db.users.find({'role': 'customer'}, {'_id': 0, 'password_hash': 0}).to_list(500)
    for u in users:
        u['orders_count'] = await db.orders.count_documents({'user_id': u['id']})
        agg = await db.orders.find({'user_id': u['id']}, {'_id': 0, 'total': 1}).to_list(500)
        u['lifetime_value'] = round(sum(o.get('total', 0) for o in agg), 2)
        # credits field exists in user doc; fallback to 0 if missing
        if 'credits' not in u:
            u['credits'] = 0
        # plan / subscription label
        if 'plan' not in u:
            sub = await db.subscriptions.find_one({'user_id': u.get('id'), 'status': 'active'}, {'_id': 0, 'plan': 1})
            u['plan'] = sub.get('plan', 'free') if sub else 'free'
    return users


@router.post('/chat')
async def chat(body: AdminChatIn, user=Depends(get_current_admin)):
    session_id = body.session_id or str(uuid.uuid4())
    parsed = await parse_intent(body.message, session_id)
    result = await execute_intent(parsed)

    # Log user msg
    user_msg = AdminChatMessage(
        session_id=session_id, role='user', text=body.message,
    )
    await db.admin_chat.insert_one(user_msg.model_dump())

    # Log assistant msg
    asst_msg = AdminChatMessage(
        session_id=session_id,
        role='assistant',
        text=parsed.get('reply', ''),
        intent=parsed.get('intent'),
        params=parsed.get('params', {}),
        result=result,
    )
    await db.admin_chat.insert_one(asst_msg.model_dump())

    return {
        'session_id': session_id,
        'intent': parsed.get('intent'),
        'params': parsed.get('params', {}),
        'reply': parsed.get('reply', ''),
        'result': result,
    }


@router.get('/chat/history')
async def chat_history(session_id: str = None, user=Depends(get_current_admin)):
    q = {'session_id': session_id} if session_id else {}
    msgs = await db.admin_chat.find(q, {'_id': 0}).sort('created_at', 1).to_list(500)
    return msgs


@router.get('/founder-stats', dependencies=[Depends(get_current_admin)])
async def founder_stats():
    import os
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now - timedelta(days=30)

    total_users = await db.users.count_documents({'role': 'customer'})
    active_users = await db.users.count_documents({'role': 'customer', 'last_login': {'$gte': month_start.isoformat()}})
    subscribers = await db.subscriptions.count_documents({'status': 'active'}) if await db.list_collection_names() else 0
    try: subscribers = await db.subscriptions.count_documents({'status': 'active'})
    except: subscribers = 0

    # MRR/ARR from subscriptions
    try:
        subs = await db.subscriptions.find({'status': 'active'}, {'_id': 0, 'amount': 1}).to_list(1000)
        mrr = sum(s.get('amount', 999) for s in subs) if subs else subscribers * 999
    except:
        mrr = subscribers * 999
    arr = mrr * 12

    # AI Jobs
    ai_jobs_today = await db.video_jobs.count_documents({'created_at': {'$gte': today_start.isoformat()}})
    total_videos = await db.video_jobs.count_documents({'status': 'done'})
    total_images = await db.ai_jobs.count_documents({'type': 'image', 'status': 'done'})
    total_voice = await db.ai_jobs.count_documents({'type': 'voice_clone', 'status': 'done'})
    total_llm = 0

    # Credits
    try:
        tx_today = await db.credit_transactions.find({'created_at': {'$gte': today_start.isoformat()}, 'delta': {'$lt': 0}}, {'delta': 1, '_id': 0}).to_list(10000)
        credits_used_today = abs(sum(t.get('delta', 0) for t in tx_today))
        tx_month = await db.credit_transactions.find({'created_at': {'$gte': month_start.isoformat()}, 'delta': {'$lt': 0}}, {'delta': 1, '_id': 0}).to_list(10000)
        credits_used_month = abs(sum(t.get('delta', 0) for t in tx_month))
        tx_granted = await db.credit_transactions.find({'delta': {'$gt': 0}}, {'delta': 1, '_id': 0}).to_list(10000)
        credits_granted = sum(t.get('delta', 0) for t in tx_granted)
    except:
        credits_used_today = credits_used_month = credits_granted = 0

    import time
    uptime_seconds = None
    try:
        with open('/proc/uptime') as f:
            uptime_seconds = int(float(f.read().split()[0]))
    except Exception:
        pass

    env_health = {
        'MONGO_URL':          bool(os.getenv('MONGO_URL')),
        'JWT_SECRET':         bool(os.getenv('JWT_SECRET')),
        'SESSION_SECRET':     bool(os.getenv('SESSION_SECRET')),
        'GROQ_API_KEY':       bool(os.getenv('GROQ_API_KEY')),
        'HF_TOKEN':           bool(os.getenv('HF_TOKEN')),
        'OPENROUTER_API_KEY': bool(os.getenv('OPENROUTER_KEY') or os.getenv('OPENROUTER_API_KEY')),
        'RAZORPAY_KEY_ID':    bool(os.getenv('RAZORPAY_KEY_ID')),
    }

    return {
        'mrr': mrr,
        'arr': arr,
        'total_users': total_users,
        'active_users': active_users,
        'subscribers': subscribers,
        'ai_jobs_today': ai_jobs_today,
        'total_videos': total_videos,
        'total_images': total_images,
        'total_voice': total_voice,
        'total_llm': total_llm,
        'credits_used_today': credits_used_today,
        'credits_used_month': credits_used_month,
        'credits_granted': credits_granted,
        'uptime_seconds': uptime_seconds,
        'env_health': env_health,
        # legacy flat keys kept for backward compat
        'hf_token_set': env_health['HF_TOKEN'],
        'groq_set': env_health['GROQ_API_KEY'],
        'openrouter_set': env_health['OPENROUTER_API_KEY'],
    }


@router.get('/chat/sessions')
async def chat_sessions(user=Depends(get_current_admin)):
    pipeline = [
        {'$sort': {'created_at': -1}},
        {'$group': {'_id': '$session_id', 'last': {'$first': '$text'}, 'created_at': {'$first': '$created_at'}, 'count': {'$sum': 1}}},
        {'$sort': {'created_at': -1}},
        {'$limit': 30},
    ]
    sessions = await db.admin_chat.aggregate(pipeline).to_list(30)
    return [{'session_id': s['_id'], 'last': s['last'], 'created_at': s['created_at'], 'count': s['count']} for s in sessions]


# ── System Stats (real /proc data) ────────────────────────────────────────────

@router.get('/system-stats', dependencies=[Depends(get_current_admin)])
async def system_stats():
    """Real VPS health — RAM, CPU load, disk, uptime, MongoDB ping."""
    import os as _os

    # Uptime
    uptime_s = None
    try:
        with open('/proc/uptime') as f:
            uptime_s = int(float(f.read().split()[0]))
    except Exception:
        pass

    # CPU load (1m, 5m, 15m)
    cpu_load = None
    try:
        with open('/proc/loadavg') as f:
            parts = f.read().split()
            cpu_load = {'1m': float(parts[0]), '5m': float(parts[1]), '15m': float(parts[2])}
    except Exception:
        pass

    # RAM (MemTotal, MemAvailable in kB)
    ram = None
    try:
        mem = {}
        with open('/proc/meminfo') as f:
            for line in f:
                k, v = line.split(':')
                mem[k.strip()] = int(v.strip().split()[0])
        total_mb  = mem.get('MemTotal', 0) // 1024
        avail_mb  = mem.get('MemAvailable', 0) // 1024
        used_mb   = total_mb - avail_mb
        ram = {
            'total_mb': total_mb,
            'used_mb': used_mb,
            'avail_mb': avail_mb,
            'used_pct': round(used_mb / total_mb * 100, 1) if total_mb else 0,
        }
    except Exception:
        pass

    # Disk usage (root partition)
    disk = None
    try:
        st = _os.statvfs('/')
        total_gb = round(st.f_blocks * st.f_frsize / 1e9, 1)
        free_gb  = round(st.f_bfree  * st.f_frsize / 1e9, 1)
        used_gb  = round(total_gb - free_gb, 1)
        disk = {
            'total_gb': total_gb,
            'used_gb': used_gb,
            'free_gb': free_gb,
            'used_pct': round(used_gb / total_gb * 100, 1) if total_gb else 0,
        }
    except Exception:
        pass

    # MongoDB ping
    mongo_ok = False
    mongo_ms = None
    try:
        import time
        t0 = time.monotonic()
        await db.command('ping')
        mongo_ms = round((time.monotonic() - t0) * 1000, 1)
        mongo_ok = True
    except Exception:
        pass

    # GPU detection (nvidia-smi)
    gpu = None
    try:
        import subprocess
        r = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.free', '--format=csv,noheader'],
            capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            parts = r.stdout.strip().split(',')
            gpu = {'name': parts[0].strip(), 'vram_total': parts[1].strip(), 'vram_free': parts[2].strip() if len(parts) > 2 else None}
    except Exception:
        gpu = None

    return {
        'uptime_s': uptime_s,
        'cpu_load': cpu_load,
        'ram': ram,
        'disk': disk,
        'mongo': {'ok': mongo_ok, 'ping_ms': mongo_ms},
        'gpu': gpu,
        'gpu_available': gpu is not None,
    }


# ── Login Sessions ────────────────────────────────────────────────────────────

@router.get('/login-sessions', dependencies=[Depends(get_current_admin)])
async def login_sessions(limit: int = 30):
    """Return recent login events from login_logs collection (written by auth route on each login)."""
    try:
        logs = await db.login_logs.find({}, {'_id': 0}).sort('created_at', -1).to_list(limit)
    except Exception:
        logs = []
    if not logs:
        # fallback: pull last-login from users collection
        users = await db.users.find(
            {'last_login': {'$exists': True}},
            {'_id': 0, 'id': 1, 'email': 1, 'name': 1, 'last_login': 1}
        ).sort('last_login', -1).to_list(limit)
        logs = [
            {
                'id': str(u.get('id', '')),
                'email': u.get('email', ''),
                'name': u.get('name', ''),
                'ip': None,
                'user_agent': None,
                'created_at': u.get('last_login'),
                'active': True,
            }
            for u in users
        ]
    return {'items': logs}


# ── API Keys ─────────────────────────────────────────────────────────────────

class ApiKeyIn(BaseModel):
    name: str


@router.get('/api-keys', dependencies=[Depends(get_current_admin)])
async def list_api_keys():
    keys = await db.api_keys.find({}, {'_id': 0, 'key': 0}).sort('created_at', -1).to_list(100)
    return {'items': keys}


@router.post('/api-keys', dependencies=[Depends(get_current_admin)])
async def create_api_key(body: ApiKeyIn):
    raw_key = 'gs_' + secrets.token_urlsafe(32)
    doc = {
        'id': str(uuid.uuid4()),
        'name': body.name.strip(),
        'key': raw_key,
        'key_prefix': raw_key[:10],
        'created_at': datetime.now(timezone.utc).isoformat(),
        'last_used': None,
        'revoked': False,
    }
    await db.api_keys.insert_one(doc)
    return {'id': doc['id'], 'name': doc['name'], 'key': raw_key, 'key_prefix': doc['key_prefix']}


@router.delete('/api-keys/{key_id}', dependencies=[Depends(get_current_admin)])
async def revoke_api_key(key_id: str):
    result = await db.api_keys.delete_one({'id': key_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Key not found')
    return {'ok': True}


# ── All builder projects (admin view) ─────────────────────────────────────────

@router.get('/projects', dependencies=[Depends(get_current_admin)])
async def all_projects(limit: int = 100):
    """Admin view — shows builder projects across ALL users."""
    projects = await db.builder_projects.find({}, {'_id': 0}).sort('created_at', -1).to_list(limit)
    return {'items': projects, 'total': len(projects)}
