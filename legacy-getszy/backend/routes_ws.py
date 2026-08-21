"""Authenticated WebSocket endpoints for real-time updates."""
import os

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from auth import is_token_revoked
from db import db
from websocket_manager import manager

router = APIRouter(tags=['websocket'])

JWT_SECRET = os.environ.get('JWT_SECRET', '')
JWT_ALG = 'HS256'


async def _verify_ws_user(token: str, *, require_admin: bool = False) -> dict | None:
    """Return the active database user represented by a non-revoked WS JWT."""
    if not token or not JWT_SECRET:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        return None

    user_id = payload.get('sub')
    if not user_id or await is_token_revoked(payload.get('jti', '')):
        return None

    user = await db.users.find_one({'id': user_id}, {'_id': 0, 'id': 1, 'role': 1})
    if not user or (require_admin and user.get('role') != 'admin'):
        return None
    return user


@router.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket, channel: str = 'general', token: str = Query(default='')):
    user = await _verify_ws_user(token)
    if not user:
        await websocket.close(code=4001, reason='Invalid or missing token')
        return
    user_id = user['id']
    await manager.connect(websocket, channel, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(channel, {'channel': channel, 'data': data, 'user_id': user_id})
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel, user_id)


@router.websocket('/ws/notifications/{user_id}')
async def notifications_ws(websocket: WebSocket, user_id: str, token: str = Query(default='')):
    user = await _verify_ws_user(token)
    if not user or user['id'] != user_id:
        await websocket.close(code=4001, reason='Unauthorized')
        return
    await manager.connect(websocket, f'notifications:{user_id}', user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, f'notifications:{user_id}', user_id)


@router.websocket('/ws/admin-live')
async def admin_live_ws(websocket: WebSocket, token: str = Query(default='')):
    """Live ops feed restricted to an active administrator account."""
    user = await _verify_ws_user(token, require_admin=True)
    if not user:
        await websocket.close(code=4001, reason='Unauthorized')
        return
    user_id = user['id']
    await manager.connect(websocket, 'admin-live', user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, 'admin-live', user_id)
