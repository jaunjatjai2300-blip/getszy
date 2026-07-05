"""Founder + Admin capabilities appended to the main registry.

Kept in a separate file to avoid escaping issues from bulk-writes; imported at
module-load time by `capabilities.py` so the registry stays a single source of truth.
"""
from datetime import datetime, timezone
from typing import Dict, Any

from db import db


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Founder Labs ----------
async def _cap_labs_experiment(user, params, emit) -> Dict[str, Any]:
    """Free-form LLM experiment for founders. Not surfaced to customers."""
    from llm_provider import chat_completion
    system = (params.get('system') or 'You are an experimental research assistant for Getszy founders.')[:2000]
    prompt = (params.get('prompt') or '').strip()
    if len(prompt) < 4:
        return {'kind': 'error', 'title': 'Prompt required', 'data': {'error': 'prompt too short'}}
    await emit('progress', {'msg': 'Running founder experiment…', 'percent': 40})
    raw = await chat_completion(system=system, user=prompt,
                                temperature=float(params.get('temperature', 0.7)))
    return {'kind': 'labs_experiment', 'title': prompt[:60],
            'data': {'raw': (raw or '')[:6000], 'system': system, 'prompt': prompt}}


# ---------- Admin — Platform Operations ----------
async def _cap_admin_analytics(user, params, emit) -> Dict[str, Any]:
    await emit('progress', {'msg': 'Aggregating KPIs…', 'percent': 50})
    users = await db.users.count_documents({})
    products = await db.products.count_documents({})
    orders = await db.orders.count_documents({})
    videos = await db.video_jobs.count_documents({'status': 'done'})
    chats = await db.chat_projects.count_documents({})
    webapps = await db.builder_projects.count_documents({})
    pipe = [{'$match': {'status': {'$in': ['paid', 'delivered', 'shipped']}}},
            {'$group': {'_id': None, 'total': {'$sum': '$total'}}}]
    rev = await db.orders.aggregate(pipe).to_list(1)
    revenue = rev[0]['total'] if rev else 0
    roles = await db.users.aggregate([{'$group': {'_id': '$role', 'count': {'$sum': 1}}}]).to_list(10)
    return {'kind': 'admin_analytics', 'title': 'Platform KPIs',
            'data': {'users': users, 'products': products, 'orders': orders,
                     'revenue': revenue, 'videos_done': videos,
                     'chat_projects': chats, 'webapps_built': webapps,
                     'roles': {r['_id']: r['count'] for r in roles if r['_id']}}}


async def _cap_admin_list_users(user, params, emit) -> Dict[str, Any]:
    q = (params.get('query') or '').strip()
    filt: Dict[str, Any] = {}
    if q:
        filt = {'$or': [{'email': {'$regex': q, '$options': 'i'}},
                        {'name': {'$regex': q, '$options': 'i'}}]}
    if params.get('role'):
        filt['role'] = params['role']
    limit = max(1, min(int(params.get('limit', 20)), 100))
    await emit('progress', {'msg': 'Searching users…', 'percent': 40})
    docs = await db.users.find(filt, {'_id': 0, 'password_hash': 0}).sort('created_at', -1).limit(limit).to_list(limit)
    return {'kind': 'admin_user_list', 'title': f'{len(docs)} users',
            'data': {'users': docs, 'query': q, 'role_filter': params.get('role')}}


async def _cap_admin_set_role(user, params, emit) -> Dict[str, Any]:
    email = (params.get('email') or '').strip().lower()
    role = (params.get('role') or '').strip().lower()
    if not email or role not in ('visitor', 'customer', 'founder', 'admin'):
        return {'kind': 'error', 'title': 'Invalid role/email', 'data': {'error': 'email + valid role required'}}
    r = await db.users.update_one({'email': email}, {'$set': {'role': role}})
    return {'kind': 'admin_role_change', 'title': f'{email} → {role}',
            'data': {'matched': r.matched_count, 'modified': r.modified_count,
                     'email': email, 'role': role}}


async def _cap_admin_publish_course(user, params, emit) -> Dict[str, Any]:
    slug = (params.get('slug') or '').strip()
    if not slug:
        return {'kind': 'error', 'title': 'slug required', 'data': {}}
    r = await db.courses.update_one({'slug': slug}, {'$set': {'is_published': True, 'published_at': _iso()}})
    return {'kind': 'admin_course_publish', 'title': f'Published {slug}',
            'data': {'matched': r.matched_count, 'modified': r.modified_count}}


async def _cap_admin_homepage(user, params, emit) -> Dict[str, Any]:
    headline = params.get('headline')
    subheadline = params.get('subheadline')
    upd: Dict[str, Any] = {}
    if headline: upd['hero.headline'] = headline
    if subheadline: upd['hero.subheadline'] = subheadline
    if not upd:
        return {'kind': 'error', 'title': 'Nothing to update', 'data': {'hint': 'Provide headline or subheadline'}}
    upd['updated_at'] = _iso()
    await db.site_content.update_one({'key': 'homepage'}, {'$set': upd}, upsert=True)
    return {'kind': 'admin_cms_update', 'title': 'Homepage updated', 'data': upd}


EXTENDED_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    'labs_experiment': {
        'desc': 'Founder Labs — free-form LLM experiment with a custom system prompt (INTERNAL, not for customers)',
        'params': {'prompt': 'string (required)', 'system': 'optional custom system prompt', 'temperature': 'float 0-1'},
        'run': _cap_labs_experiment, 'result_kind': 'labs_experiment', 'min_role': 'founder',
    },
    'admin_analytics': {
        'desc': 'ADMIN — Platform KPIs snapshot (users, revenue, orders, chats, videos)',
        'params': {},
        'run': _cap_admin_analytics, 'result_kind': 'admin_analytics', 'min_role': 'admin',
    },
    'admin_list_users': {
        'desc': 'ADMIN — Search and list platform users by email/name/role',
        'params': {'query': 'string', 'role': 'visitor|customer|founder|admin', 'limit': 'int'},
        'run': _cap_admin_list_users, 'result_kind': 'admin_user_list', 'min_role': 'admin',
    },
    'admin_set_role': {
        'desc': "ADMIN — Change a user's role (visitor|customer|founder|admin)",
        'params': {'email': 'string (required)', 'role': 'visitor|customer|founder|admin'},
        'run': _cap_admin_set_role, 'result_kind': 'admin_role_change', 'min_role': 'admin',
    },
    'admin_publish_course': {
        'desc': 'ADMIN — Publish a course by slug',
        'params': {'slug': 'string (required)'},
        'run': _cap_admin_publish_course, 'result_kind': 'admin_course_publish', 'min_role': 'admin',
    },
    'admin_homepage': {
        'desc': 'ADMIN — Update homepage hero copy (headline / subheadline)',
        'params': {'headline': 'string', 'subheadline': 'string'},
        'run': _cap_admin_homepage, 'result_kind': 'admin_cms_update', 'min_role': 'admin',
    },
}
