"""WebSocket manager for realtime features — live feeds, notifications, activity."""
import json
import logging
import asyncio
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from redis_cache import get_redis, pubsub_publish

logger = logging.getLogger('getszy.ws')


class ConnectionManager:
    """Manages WebSocket connections per user and broadcast channels."""

    def __init__(self):
        self._active: Dict[str, Set[WebSocket]] = {}
        self._channels: Dict[str, Set[WebSocket]] = {}

    async def connect(self, ws: WebSocket, user_id: str):
        await ws.accept()
        if user_id not in self._active:
            self._active[user_id] = set()
        self._active[user_id].add(ws)
        logger.info(f'WS connected: {user_id}')

    def disconnect(self, ws: WebSocket, user_id: str):
        if user_id in self._active:
            self._active[user_id].discard(ws)
            if not self._active[user_id]:
                del self._active[user_id]
        for ch_set in self._channels.values():
            ch_set.discard(ws)
        logger.info(f'WS disconnected: {user_id}')

    async def send_to_user(self, user_id: str, event: str, data: dict):
        msg = json.dumps({'event': event, 'data': data}, default=str)
        if user_id in self._active:
            dead = set()
            for ws in self._active[user_id]:
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.add(ws)
            self._active[user_id] -= dead

    async def broadcast(self, event: str, data: dict, channel: str = 'global'):
        msg = json.dumps({'event': event, 'data': data}, default=str)
        if channel in self._channels:
            dead = set()
            for ws in self._channels[channel]:
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.add(ws)
            self._channels[channel] -= dead

    async def broadcast_all(self, event: str, data: dict):
        msg = json.dumps({'event': event, 'data': data}, default=str)
        dead_users = []
        for user_id, connections in self._active.items():
            dead = set()
            for ws in connections:
                try:
                    await ws.send_text(msg)
                except Exception:
                    dead.add(ws)
            connections -= dead
            if not connections:
                dead_users.append(user_id)
        for uid in dead_users:
            del self._active[uid]

    def subscribe_channel(self, ws: WebSocket, channel: str):
        if channel not in self._channels:
            self._channels[channel] = set()
        self._channels[channel].add(ws)

    def unsubscribe_channel(self, ws: WebSocket, channel: str):
        if channel in self._channels:
            self._channels[channel].discard(ws)

    @property
    def online_count(self) -> int:
        return len(self._active)

    @property
    def online_users(self) -> list:
        return list(self._active.keys())


manager = ConnectionManager()


# ── Helper functions ─────────────────────────────────────────────────────────

async def notify_user(user_id: str, title: str, body: str, **extra):
    """Send notification to specific user (WebSocket + DB)."""
    event_data = {'title': title, 'body': body, **extra}
    await manager.send_to_user(user_id, 'notification', event_data)

    # Also store in DB for history
    try:
        from db import db
        from models import _id, _now
        await db.notifications.insert_one({
            'id': _id(),
            'user_id': user_id,
            'title': title,
            'body': body,
            'read': False,
            'created_at': _now(),
            **{k: v for k, v in extra.items() if k in ('type', 'link', 'icon')},
        })
    except Exception as e:
        logger.warning(f'Failed to store notification: {e}')


async def broadcast_activity(agent: str, icon: str, label: str, user_id: str = None):
    """Broadcast activity to admin feed."""
    data = {'agent': agent, 'icon': icon, 'label': label, 'user_id': user_id}
    await manager.broadcast('activity', data, channel='admin-feed')
    await pubsub_publish('activity', data)


async def broadcast_order_update(order_id: str, status: str, user_id: str):
    """Notify user about order status change."""
    await notify_user(user_id, 'Order Update', f'Order {order_id} is now: {status}',
                       type='order', link=f'/account?order={order_id}')


async def broadcast_ai_usage(agent: str, provider: str, tokens: int, cost: float):
    """Broadcast AI usage stats to admin."""
    data = {'agent': agent, 'provider': provider, 'tokens': tokens, 'cost': cost}
    await manager.broadcast('ai_usage', data, channel='admin-feed')
