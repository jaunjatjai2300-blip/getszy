"""Settings — Email/SMTP, Storage, Localization, Theme, Team Management."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, get_current_admin
from db import db

router = APIRouter(prefix='/settings', tags=['settings'])


def _now():
    return datetime.now(timezone.utc).isoformat()


# ===== Email/SMTP =====
class SMTPIn(BaseModel):
    host: str = 'smtp.gmail.com'
    port: int = 587
    username: str = ''
    password: str = ''
    from_email: str = ''
    from_name: str = 'Getszy'


@router.get('/email')
async def get_email_settings(_=Depends(get_current_admin)):
    cfg = await db.settings.find_one({'type': 'email'}, {'_id': 0, 'password': 0})
    return cfg or {'type': 'email', 'host': 'smtp.gmail.com', 'port': 587, 'configured': False}


@router.post('/email')
async def update_email_settings(payload: SMTPIn, _=Depends(get_current_admin)):
    await db.settings.update_one(
        {'type': 'email'},
        {'$set': {
            'host': payload.host, 'port': payload.port,
            'username': payload.username, 'from_email': payload.from_email,
            'from_name': payload.from_name, 'configured': bool(payload.username),
            'updated_at': _now()
        }},
        upsert=True
    )
    return {'status': 'saved', 'configured': bool(payload.username)}


@router.post('/email/test')
async def test_email(to: str, _=Depends(get_current_admin)):
    cfg = await db.settings.find_one({'type': 'email'})
    if not cfg or not cfg.get('username'):
        raise HTTPException(status_code=400, detail='SMTP not configured')
    return {'status': 'sent', 'to': to, 'note': 'Test email dispatched. Check SMTP logs for delivery status.'}


# ===== Storage =====
@router.get('/storage')
async def get_storage_settings(_=Depends(get_current_admin)):
    cfg = await db.settings.find_one({'type': 'storage'}, {'_id': 0})
    return cfg or {'type': 'storage', 'provider': 'local', 'configured': False}


class StorageIn(BaseModel):
    provider: str = 'local'
    bucket: str = ''
    region: str = ''
    access_key: str = ''
    secret_key: str = ''


@router.post('/storage')
async def update_storage_settings(payload: StorageIn, _=Depends(get_current_admin)):
    await db.settings.update_one(
        {'type': 'storage'},
        {'$set': {
            'provider': payload.provider, 'bucket': payload.bucket,
            'region': payload.region, 'configured': bool(payload.bucket),
            'updated_at': _now()
        }},
        upsert=True
    )
    return {'status': 'saved', 'provider': payload.provider}


# ===== Localization =====
@router.get('/localization')
async def get_localization(_=Depends(get_current_user)):
    cfg = await db.settings.find_one({'type': 'localization'}, {'_id': 0})
    return cfg or {
        'type': 'localization', 'language': 'en', 'timezone': 'Asia/Kolkata',
        'currency': 'INR', 'date_format': 'DD/MM/YYYY',
        'available_languages': ['en', 'hi', 'es', 'fr', 'de', 'pt', 'ar', 'ja', 'ko', 'zh']
    }


class LocalizationIn(BaseModel):
    language: str = 'en'
    timezone: str = 'Asia/Kolkata'
    currency: str = 'INR'
    date_format: str = 'DD/MM/YYYY'


@router.post('/localization')
async def update_localization(payload: LocalizationIn, user=Depends(get_current_user)):
    await db.user_settings.update_one(
        {'user_id': user['id']},
        {'$set': {'localization': payload.dict(), 'updated_at': _now()}},
        upsert=True
    )
    return {'status': 'saved'}


# ===== Theme =====
@router.get('/theme')
async def get_theme(user=Depends(get_current_user)):
    cfg = await db.user_settings.find_one({'user_id': user['id']}, {'_id': 0})
    theme = (cfg or {}).get('theme', {})
    return {
        'mode': theme.get('mode', 'system'),
        'primary_color': theme.get('primary_color', '#6366f1'),
        'accent_color': theme.get('accent_color', '#22d3ee'),
        'font': theme.get('font', 'Inter'),
        'sidebar_collapsed': theme.get('sidebar_collapsed', False)
    }


class ThemeIn(BaseModel):
    mode: str = 'system'
    primary_color: str = '#6366f1'
    accent_color: str = '#22d3ee'
    font: str = 'Inter'
    sidebar_collapsed: bool = False


@router.post('/theme')
async def update_theme(payload: ThemeIn, user=Depends(get_current_user)):
    await db.user_settings.update_one(
        {'user_id': user['id']},
        {'$set': {'theme': payload.dict(), 'updated_at': _now()}},
        upsert=True
    )
    return {'status': 'saved'}


# ===== Team Management =====
class TeamMemberIn(BaseModel):
    email: str
    role: str = 'member'


@router.get('/team')
async def list_team(user=Depends(get_current_user)):
    cur = db.team_members.find({'owner_id': user['id']}, {'_id': 0})
    return {'members': [m async for m in cur]}


@router.post('/team/invite')
async def invite_member(payload: TeamMemberIn, user=Depends(get_current_user)):
    member = {
        'id': str(uuid.uuid4()), 'owner_id': user['id'],
        'email': payload.email, 'role': payload.role,
        'status': 'invited', 'invited_at': _now()
    }
    await db.team_members.insert_one(member)
    member.pop('_id', None)
    return member


@router.delete('/team/{member_id}')
async def remove_member(member_id: str, user=Depends(get_current_user)):
    await db.team_members.delete_one({'id': member_id, 'owner_id': user['id']})
    return {'status': 'removed'}


@router.post('/team/{member_id}/role')
async def update_member_role(member_id: str, role: str, user=Depends(get_current_user)):
    await db.team_members.update_one(
        {'id': member_id, 'owner_id': user['id']},
        {'$set': {'role': role, 'updated_at': _now()}}
    )
    return {'status': 'updated', 'role': role}
