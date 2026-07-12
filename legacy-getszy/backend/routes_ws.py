"""WebSocket endpoint for real-time updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from websocket_manager import manager

router = APIRouter(tags=['websocket'])


@router.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket, channel: str = 'general', user_id: str = ''):
    await manager.connect(websocket, channel, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(channel, {'channel': channel, 'data': data, 'user_id': user_id})
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel, user_id)


@router.websocket('/ws/notifications/{user_id}')
async def notifications_ws(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, f'notifications:{user_id}', user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, f'notifications:{user_id}', user_id)
