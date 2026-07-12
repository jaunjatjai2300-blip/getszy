"""Notifications routes — DB-backed with unread count."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from auth import get_current_user
from db import db
from websocket_manager import manager

router = APIRouter(prefix='/notifications', tags=['notifications'])


class NotificationIn(BaseModel):
    title: str
    message: str
    type: str = 'info'
    target_user: Optional[str] = None


@router.get('/')
async def list_notifications(limit: int = 20, user=Depends(get_current_user)):
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
async def send_notification(payload: NotificationIn, _=Depends(get_current_user)):
    target = payload.target_user or _['id']
    notif = {
        'id': str(uuid.uuid4()), 'user_id': target,
        'title': payload.title, 'message': payload.message,
        'type': payload.type, 'read': False,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notif)
    await manager.send_to_user(target, {'type': 'notification', 'title': payload.title, 'message': payload.message})
    notif.pop('_id', None)
    return notif


@router.get('/online')
async def online_users(_=Depends(get_current_user)):
    return {'online': manager.get_online_users(), 'count': len(manager.get_online_users())}
