"""WebSocket endpoint for real-time updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import jwt
import os

from websocket_manager import manager

router = APIRouter(tags=['websocket'])

JWT_SECRET = os.environ.get('JWT_SECRET', '')
JWT_ALG = 'HS256'


def _verify_ws_token(token: str) -> str | None:
    """Return user_id from JWT or None if invalid."""
    if not token or not JWT_SECRET:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return payload.get('sub')
    except Exception:
        return None


@router.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket, channel: str = 'general', token: str = Query(default='')):
    user_id = _verify_ws_token(token)
    if not user_id:
        await websocket.close(code=4001, reason='Invalid or missing token')
        return
    await manager.connect(websocket, channel, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(channel, {'channel': channel, 'data': data, 'user_id': user_id})
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel, user_id)


@router.websocket('/ws/notifications/{user_id}')
async def notifications_ws(websocket: WebSocket, user_id: str, token: str = Query(default='')):
    verified_id = _verify_ws_token(token)
    if not verified_id or verified_id != user_id:
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
    """Live ops feed for admins: orders, refunds, signups, threats in real time."""
    user_id = _verify_ws_token(token)
    if not user_id:
        await websocket.close(code=4001, reason='Invalid or missing token')
        return
    await manager.connect(websocket, 'admin-live', user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, 'admin-live', user_id)
