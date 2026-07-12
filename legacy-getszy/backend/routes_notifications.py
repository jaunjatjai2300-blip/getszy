"""Notification routes."""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from auth import get_current_user, get_current_admin
from db import db
from websocket_manager import manager

router = APIRouter(prefix='/notifications', tags=['notifications'])


@router.get('/')
async def list_notifications(user=Depends(get_current_user), limit: int = Query(20, ge=1, le=100)):
    cursor = db.notifications.find(
        {'user_id': user['id']}, {'_id': 0}
    ).sort('created_at', -1).limit(limit)
    return await cursor.to_list(limit)


@router.get('/unread-count')
async def unread_count(user=Depends(get_current_user)):
    count = await db.notifications.count_documents({'user_id': user['id'], 'read': False})
    return {'count': count}


@router.post('/mark-read')
async def mark_read(notification_id: str, user=Depends(get_current_user)):
    await db.notifications.update_one(
        {'id': notification_id, 'user_id': user['id']},
        {'$set': {'read': True}}
    )
    return {'ok': True}


@router.post('/mark-all-read')
async def mark_all_read(user=Depends(get_current_user)):
    await db.notifications.update_many(
        {'user_id': user['id'], 'read': False},
        {'$set': {'read': True}}
    )
    return {'ok': True}


@router.get('/online')
async def online_status():
    return {'online_count': manager.online_count, 'online_users': manager.online_users}
