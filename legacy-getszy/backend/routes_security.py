"""Security — MFA (TOTP), IP Whitelist, Session Manager."""
import uuid
import secrets
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from db import db

router = APIRouter(prefix='/security', tags=['security'])


def _now():
    return datetime.now(timezone.utc).isoformat()


# ===== MFA (TOTP) =====
@router.post('/mfa/enable')
async def enable_mfa(user=Depends(get_current_user)):
    secret = secrets.token_hex(20)
    await db.user_mfa.update_one(
        {'user_id': user['id']},
        {'$set': {'secret': secret, 'enabled': False, 'created_at': _now()}},
        upsert=True
    )
    return {'secret': secret, 'otpauth_url': f'otpauth://totp/Getszy:{user.get("email", user["id"])}?secret={secret}&issuer=Getszy'}


@router.post('/mfa/verify')
async def verify_mfa(code: str, user=Depends(get_current_user)):
    mfa = await db.user_mfa.find_one({'user_id': user['id']})
    if not mfa:
        raise HTTPException(status_code=400, detail='MFA not set up')
    import pyotp
    totp = pyotp.TOTP(mfa['secret'])
    if totp.verify(code, valid_window=1):
        await db.user_mfa.update_one({'user_id': user['id']}, {'$set': {'enabled': True, 'verified_at': _now()}})
        return {'status': 'verified', 'mfa_enabled': True}
    raise HTTPException(status_code=400, detail='Invalid MFA code')


@router.post('/mfa/disable')
async def disable_mfa(code: str, user=Depends(get_current_user)):
    mfa = await db.user_mfa.find_one({'user_id': user['id']})
    if mfa and mfa.get('enabled'):
        import pyotp
        totp = pyotp.TOTP(mfa['secret'])
        if not totp.verify(code, valid_window=1):
            raise HTTPException(status_code=400, detail='Invalid MFA code')
    await db.user_mfa.delete_one({'user_id': user['id']})
    return {'status': 'disabled'}


@router.get('/mfa/status')
async def mfa_status(user=Depends(get_current_user)):
    mfa = await db.user_mfa.find_one({'user_id': user['id']}, {'_id': 0, 'secret': 0})
    return {'enabled': mfa.get('enabled', False) if mfa else False}


# ===== IP Whitelist =====
class IPWhitelistIn(BaseModel):
    ip: str
    label: str = ''


@router.get('/ip-whitelist')
async def list_ip_whitelist(user=Depends(get_current_user)):
    cur = db.ip_whitelist.find({'user_id': user['id']}, {'_id': 0})
    return {'ips': [ip async for ip in cur]}


@router.post('/ip-whitelist')
async def add_ip_whitelist(payload: IPWhitelistIn, user=Depends(get_current_user)):
    entry = {
        'id': str(uuid.uuid4()), 'user_id': user['id'],
        'ip': payload.ip, 'label': payload.label,
        'created_at': _now()
    }
    await db.ip_whitelist.insert_one(entry)
    entry.pop('_id', None)
    return entry


@router.delete('/ip-whitelist/{entry_id}')
async def remove_ip_whitelist(entry_id: str, user=Depends(get_current_user)):
    await db.ip_whitelist.delete_one({'id': entry_id, 'user_id': user['id']})
    return {'status': 'removed'}


# ===== Session Manager =====
@router.get('/sessions')
async def list_sessions(user=Depends(get_current_user)):
    cur = db.active_sessions.find({'user_id': user['id']}, {'_id': 0})
    return {'sessions': [s async for s in cur]}


@router.delete('/sessions/{session_id}')
async def revoke_session(session_id: str, user=Depends(get_current_user)):
    await db.active_sessions.delete_one({'id': session_id, 'user_id': user['id']})
    return {'status': 'revoked'}


@router.delete('/sessions')
async def revoke_all_sessions(user=Depends(get_current_user)):
    result = await db.active_sessions.delete_many({'user_id': user['id']})
    return {'status': 'all_revoked', 'count': result.deleted_count}
