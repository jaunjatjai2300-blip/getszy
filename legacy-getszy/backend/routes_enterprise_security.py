import uuid
import secrets
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_admin, get_current_user
from db import db

router = APIRouter(prefix='/admin/enterprise-security', tags=['enterprise-security'])


def _now():
    return datetime.now(timezone.utc).isoformat()


class DeviceRegister(BaseModel):
    user_agent: str
    ip: str
    label: str = ''
    platform: str = ''


class APIKeyCreate(BaseModel):
    name: str
    expires_in_days: int = 90


class GoogleSSOConfig(BaseModel):
    client_id: str
    client_secret: str


class EnvVarSet(BaseModel):
    key: str
    value: str
    project_id: str


class BulkEnvVars(BaseModel):
    project_id: str
    env_text: str


class DomainMap(BaseModel):
    domain: str
    project_id: str
    auto_ssl: bool = True


@router.get('/devices')
async def list_devices(user=Depends(get_current_user)):
    query = {} if user.get('role') in ('admin', 'founder') else {'user_id': user['id']}
    cur = db.user_devices.find(query, {'_id': 0}).sort('last_seen', -1)
    return {'devices': [d async for d in cur]}


@router.post('/devices')
async def register_device(payload: DeviceRegister, user=Depends(get_current_user)):
    device = {
        'id': uuid.uuid4().hex[:12],
        'user_id': user['id'],
        'user_agent': payload.user_agent,
        'ip': payload.ip,
        'label': payload.label,
        'platform': payload.platform,
        'registered_at': _now(),
        'last_seen': _now(),
    }
    await db.user_devices.insert_one(device)
    device.pop('_id', None)
    return device


@router.delete('/devices/{device_id}')
async def remove_device(device_id: str, user=Depends(get_current_user)):
    query = {'id': device_id}
    if user.get('role') not in ('admin', 'founder'):
        query['user_id'] = user['id']
    result = await db.user_devices.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Device not found')
    return {'status': 'removed'}


@router.get('/threat-detection')
async def threat_detection(_=Depends(get_current_admin)):
    threats = []
    now = datetime.now(timezone.utc)

    ip_counts = defaultdict(int)
    req_cursor = db.request_logs.find(
        {'timestamp': {'$gte': (now - timedelta(minutes=1)).isoformat()}},
        {'_id': 0, 'ip': 1}
    )
    async for log in req_cursor:
        ip_counts[log.get('ip', 'unknown')] += 1
    for ip, count in ip_counts.items():
        if count > 100:
            threats.append({'type': 'rate_limit', 'severity': 'high', 'ip': ip, 'requests_in_min': count, 'message': f'{count} requests/min from {ip}'})

    ten_min_ago = (now - timedelta(minutes=10)).isoformat()
    failed_login_pipeline = [
        {'$match': {'action': 'login_failed', 'timestamp': {'$gte': ten_min_ago}}},
        {'$group': {'_id': '$ip', 'count': {'$sum': 1}}}
    ]
    failed_logins = await db.audit_logs.aggregate(failed_login_pipeline).to_list(100)
    for entry in failed_logins:
        if entry['count'] > 5:
            threats.append({'type': 'brute_force', 'severity': 'critical', 'ip': entry['_id'], 'attempts': entry['count'], 'message': f'{entry["count"]} failed logins from {entry["_id"]} in 10min'})

    unusual_hour_start = now.replace(hour=2, minute=0, second=0, microsecond=0)
    unusual_hour_end = now.replace(hour=5, minute=0, second=0, microsecond=0)
    if now.hour < 5:
        unusual_cursor = db.request_logs.find(
            {'timestamp': {'$gte': unusual_hour_start.isoformat(), '$lt': unusual_hour_end.isoformat()}},
            {'_id': 0, 'ip': 1, 'user_id': 1}
        )
        unusual_ips = set()
        async for log in unusual_cursor:
            ip = log.get('ip', '')
            if ip not in unusual_ips:
                unusual_ips.add(ip)
                threats.append({'type': 'unusual_hour', 'severity': 'medium', 'ip': ip, 'user_id': log.get('user_id', ''), 'message': f'Access at unusual hour from {ip}'})

    failed_job_count = await db.queue.count_documents({'status': 'failed'})
    if failed_job_count > 10:
        threats.append({'type': 'job_failures', 'severity': 'warning', 'count': failed_job_count, 'message': f'{failed_job_count} failed jobs detected'})

    return {'threats': threats, 'count': len(threats), 'checked_at': _now()}


@router.get('/compliance')
async def compliance_check(_=Depends(get_current_admin)):
    total_users = await db.users.count_documents({})
    mfa_enabled = await db.user_mfa.count_documents({'enabled': True})
    mfa_pct = round(mfa_enabled / max(total_users, 1) * 100, 1)

    users_cursor = db.users.find({}, {'_id': 0, 'password': 1})
    weak_passwords = 0
    total_passwords = 0
    async for u in users_cursor:
        pwd = u.get('password', '')
        if pwd:
            total_passwords += 1
            if len(pwd) < 8 or pwd.isalnum():
                weak_passwords += 1
    password_score = round((1 - weak_passwords / max(total_passwords, 1)) * 100, 1)

    sessions = await db.active_sessions.count_documents({})
    old_sessions = await db.active_sessions.count_documents({
        'last_active': {'$lt': (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()}
    })
    session_score = round((1 - old_sessions / max(sessions, 1)) * 100, 1)

    whitelisted_users = await db.ip_whitelist.distinct('user_id')
    ip_whitelist_pct = round(len(whitelisted_users) / max(total_users, 1) * 100, 1)

    api_keys_count = await db.api_keys.count_documents({})
    expired_keys = await db.api_keys.count_documents({
        'expires_at': {'$lt': _now()}
    })
    api_key_score = round((1 - expired_keys / max(api_keys_count, 1)) * 100, 1)

    overall = round((mfa_pct + password_score + session_score + ip_whitelist_pct + api_key_score) / 5, 1)

    return {
        'overall_score': overall,
        'checks': {
            'mfa_enabled_pct': mfa_pct,
            'password_strength_pct': password_score,
            'session_health_pct': session_score,
            'ip_whitelist_coverage_pct': ip_whitelist_pct,
            'api_key_health_pct': api_key_score,
        },
        'details': {
            'total_users': total_users,
            'mfa_enabled': mfa_enabled,
            'weak_passwords': weak_passwords,
            'active_sessions': sessions,
            'old_sessions': old_sessions,
            'api_keys_total': api_keys_count,
            'api_keys_expired': expired_keys,
        },
        'timestamp': _now()
    }


@router.post('/api-keys')
async def create_api_key(payload: APIKeyCreate, user=Depends(get_current_user)):
    raw_key = secrets.token_hex(32)
    prefix = raw_key[:8]
    key_doc = {
        'id': uuid.uuid4().hex[:12],
        'user_id': user['id'],
        'name': payload.name,
        'key_hash': secrets.token_hex(32),
        'prefix': prefix,
        'created_at': _now(),
        'last_used': None,
        'expires_at': (datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)).isoformat(),
        'active': True,
    }
    await db.api_keys.insert_one(key_doc)
    key_doc.pop('_id', None)
    key_doc['key'] = f'gsk_{raw_key}'
    return key_doc


@router.get('/api-keys')
async def list_api_keys(user=Depends(get_current_user)):
    query = {} if user.get('role') in ('admin', 'founder') else {'user_id': user['id']}
    cur = db.api_keys.find(query, {'_id': 0, 'key_hash': 0})
    return {'keys': [k async for k in cur]}


@router.delete('/api-keys/{key_id}')
async def revoke_api_key(key_id: str, user=Depends(get_current_user)):
    query = {'id': key_id}
    if user.get('role') not in ('admin', 'founder'):
        query['user_id'] = user['id']
    result = await db.api_keys.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='API key not found')
    return {'status': 'revoked'}


@router.post('/api-keys/{key_id}/rotate')
async def rotate_api_key(key_id: str, user=Depends(get_current_user)):
    query = {'id': key_id}
    if user.get('role') not in ('admin', 'founder'):
        query['user_id'] = user['id']
    old_key = await db.api_keys.find_one(query)
    if not old_key:
        raise HTTPException(status_code=404, detail='API key not found')

    await db.api_keys.delete_one({'id': key_id})

    raw_key = secrets.token_hex(32)
    new_key_doc = {
        'id': uuid.uuid4().hex[:12],
        'user_id': old_key['user_id'],
        'name': old_key['name'],
        'key_hash': secrets.token_hex(32),
        'prefix': raw_key[:8],
        'created_at': _now(),
        'last_used': None,
        'expires_at': (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
        'active': True,
    }
    await db.api_keys.insert_one(new_key_doc)
    new_key_doc.pop('_id', None)
    new_key_doc['key'] = f'gsk_{raw_key}'
    return new_key_doc


@router.get('/sso/status')
async def sso_status(_=Depends(get_current_admin)):
    google_config = await db.sso_configs.find_one({'provider': 'google'}, {'_id': 0, 'client_secret': 0})
    github_config = await db.sso_configs.find_one({'provider': 'github'}, {'_id': 0, 'client_secret': 0})
    workspace_config = await db.sso_configs.find_one({'provider': 'workspace'}, {'_id': 0, 'client_secret': 0})

    return {
        'google': {'configured': bool(google_config), 'client_id': google_config.get('client_id', '') if google_config else ''},
        'github': {'configured': bool(github_config), 'client_id': github_config.get('client_id', '') if github_config else ''},
        'workspace': {'configured': bool(workspace_config), 'domain': workspace_config.get('domain', '') if workspace_config else ''},
        'timestamp': _now()
    }


@router.post('/sso/google/configure')
async def configure_google_sso(payload: GoogleSSOConfig, _=Depends(get_current_admin)):
    config = {
        'provider': 'google',
        'client_id': payload.client_id,
        'client_secret': payload.client_secret,
        'updated_at': _now(),
    }
    await db.sso_configs.update_one({'provider': 'google'}, {'$set': config}, upsert=True)
    return {'status': 'configured', 'provider': 'google'}


@router.get('/session-analytics')
async def session_analytics(_=Depends(get_current_admin)):
    cur = db.active_sessions.find({}, {'_id': 0})
    sessions = [s async for s in cur]

    by_device = defaultdict(int)
    by_location = defaultdict(int)
    by_hour = defaultdict(int)
    durations = []

    for s in sessions:
        by_device[s.get('platform', s.get('user_agent', 'unknown'))] += 1
        by_location[s.get('location', 'unknown')] += 1
        created = s.get('created_at', '')
        if created:
            try:
                hour = datetime.fromisoformat(created).hour
                by_hour[hour] += 1
            except (ValueError, TypeError):
                pass
        created_dt = s.get('created_at')
        last_active = s.get('last_active')
        if created_dt and last_active:
            try:
                start = datetime.fromisoformat(created_dt)
                end = datetime.fromisoformat(last_active)
                durations.append((end - start).total_seconds() / 60)
            except (ValueError, TypeError):
                pass

    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

    return {
        'total_sessions': len(sessions),
        'by_device': dict(by_device),
        'by_location': dict(by_location),
        'by_hour': dict(by_hour),
        'avg_duration_minutes': avg_duration,
        'timestamp': _now()
    }
