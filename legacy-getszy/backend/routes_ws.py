"""WebSocket routes for realtime features."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from auth import decode_token
from websocket_manager import manager

router = APIRouter(tags=['websocket'])


@router.websocket('/ws')
async def websocket_endpoint(ws: WebSocket, token: str = Query(None)):
    """Main WebSocket endpoint. Connect: ws://host/api/ws?token=JWT_TOKEN"""
    user_id = None
    try:
        if token:
            payload = decode_token(token)
            user_id = payload.get('sub')
    except Exception:
        pass

    if not user_id:
        user_id = f'anon-{id(ws)}'

    await manager.connect(ws, user_id)
    try:
        while True:
            data = await ws.receive_json()
            event = data.get('event', '')

            if event == 'subscribe':
                channel = data.get('channel', 'global')
                manager.subscribe_channel(ws, channel)
                await ws.send_json({'event': 'subscribed', 'channel': channel})

            elif event == 'unsubscribe':
                channel = data.get('channel', 'global')
                manager.unsubscribe_channel(ws, channel)
                await ws.send_json({'event': 'unsubscribed', 'channel': channel})

            elif event == 'ping':
                await ws.send_json({'event': 'pong', 'online': manager.online_count})

            elif event == 'typing':
                # Forward typing indicator to channel
                channel = data.get('channel', 'global')
                from websocket_manager import manager as mgr
                import json
                msg = json.dumps({'event': 'typing', 'user_id': user_id})
                if channel in mgr._channels:
                    for conn in mgr._channels[channel]:
                        try:
                            await conn.send_text(msg)
                        except Exception:
                            pass

    except WebSocketDisconnect:
        manager.disconnect(ws, user_id)
    except Exception as e:
        manager.disconnect(ws, user_id)
