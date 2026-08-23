"""Notifications routes — DB-backed delivery and encrypted channel configuration."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, get_current_admin
from db import db
from notify_channels import dispatch, get_channels_config
from routes_integrations import _decrypt_credentials, _encrypt_credentials
from websocket_manager import manager

router = APIRouter(prefix='/notifications', tags=['notifications'])

_SECRET_FIELDS = {'smtp_pass', 'whatsapp_token'}


class NotificationIn(BaseModel):
    title: str
    message: str
    type: str = 'info'
    target_user: Optional[str] = None


@router.get('/')
async def list_notifications(limit: int = 20, user=Depends(get_current_user)):
    limit = min(max(limit, 1), 100)
    cur = db.notifications.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(limit)
    items = [n async for n in cur]
    unread = await db.notifications.count_documents({'user_id': user['id'], 'read': False})
    return {'notifications': items, 'unread_count': unread}


@router.post('/mark-read/{notification_id}')
async def mark_read(notification_id: str, user=Depends(get_current_user)):
    await db.notifications.update_one({'id': notification_id, 'user_id': user['id']}, {'$set': {'read': True}})
    return {'status': 'read'}


@router.post('/mark-all-read')
async def mark_all_read(user=Depends(get_current_user)):
    await db.notifications.update_many({'user_id': user['id'], 'read': False}, {'$set': {'read': True}})
    return {'status': 'all_read'}


@router.post('/send')
async def send_notification(payload: NotificationIn, admin=Depends(get_current_admin)):
    target = payload.target_user or admin['id']
    notif = {
        'id': str(uuid.uuid4()), 'user_id': target,
        'title': payload.title, 'message': payload.message,
        'type': payload.type, 'read': False,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.notifications.insert_one(notif)
    await manager.send_to_user(target, {'type': 'notification', 'title': payload.title, 'message': payload.message})
    notif.pop('_id', None)
    return notif


@router.get('/online')
async def online_users(_=Depends(get_current_user)):
    return {'online': manager.get_online_users(), 'count': len(manager.get_online_users())}


class ChannelConfig(BaseModel):
    email_enabled: bool = False
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = 465
    smtp_user: Optional[str] = None
    smtp_pass: Optional[str] = None
    smtp_from: Optional[str] = None
    whatsapp_enabled: bool = False
    whatsapp_api_url: Optional[str] = None
    whatsapp_token: Optional[str] = None


def _public_config(config: dict) -> dict:
    """Remove credential material while preserving useful configured-state metadata."""
    public = dict(config or {})
    for field in _SECRET_FIELDS:
        if field in public:
            public[f'{field}_configured'] = bool(public.pop(field))
        else:
            public[f'{field}_configured'] = bool(public.get(f'{field}_configured', False))
    public.pop('credentials_encrypted', None)
    return public


@router.get('/config', dependencies=[Depends(get_current_admin)])
async def notification_config():
    # get_channels_config defaults to a redacted result, but keep this defensive
    # boundary so future changes cannot re-expose delivery credentials.
    return _public_config(await get_channels_config())


@router.put('/config', dependencies=[Depends(get_current_admin)])
async def update_notification_config(body: ChannelConfig):
    """Apply a partial config update without replacing or disclosing credentials."""
    incoming = body.model_dump(exclude_unset=True)
    existing = await db.notification_config.find_one({}, {'_id': 0}) or {}
    encrypted = existing.get('credentials_encrypted')
    try:
        credentials = _decrypt_credentials(encrypted) if encrypted else {
            field: existing[field] for field in _SECRET_FIELDS if existing.get(field)
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail='notification credentials are unreadable; rotate the encryption key only after migration') from exc

    updates = {key: value for key, value in incoming.items() if key not in _SECRET_FIELDS}
    supplied_secret_fields = _SECRET_FIELDS.intersection(incoming)
    for field in supplied_secret_fields:
        value = incoming[field]
        if value:
            credentials[field] = value
        else:
            credentials.pop(field, None)

    unset = {field: '' for field in _SECRET_FIELDS if field in existing}
    if credentials:
        try:
            updates['credentials_encrypted'] = _encrypt_credentials(credentials)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail='INTEGRATION_ENCRYPTION_KEY is required before notification credentials can be stored') from exc
    elif 'credentials_encrypted' in existing:
        unset['credentials_encrypted'] = ''

    operation = {'$set': updates}
    if unset:
        operation['$unset'] = unset
    await db.notification_config.update_one({}, operation, upsert=True)
    return {'ok': True, 'config': _public_config(await get_channels_config())}


class BroadcastIn(BaseModel):
    title: str
    message: str
    emails: list[str] = []
    phones: list[str] = []


@router.post('/broadcast', dependencies=[Depends(get_current_admin)])
async def broadcast_channels(payload: BroadcastIn):
    results = await dispatch(payload.title, payload.message, payload.emails, payload.phones)
    return {'ok': True, 'results': results}
