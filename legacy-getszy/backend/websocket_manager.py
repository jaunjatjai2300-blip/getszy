"""WebSocket connection manager for real-time updates."""
import json
from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = 'general', user_id: str = ''):
        await websocket.accept()
        if channel not in self.active:
            self.active[channel] = set()
        self.active[channel].add(websocket)
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str = 'general', user_id: str = ''):
        if channel in self.active:
            self.active[channel].discard(websocket)
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)

    async def broadcast(self, channel: str, message: dict):
        if channel not in self.active:
            return
        dead = []
        for ws in self.active[channel]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active[channel].discard(ws)

    async def send_to_user(self, user_id: str, message: dict):
        if user_id not in self.user_connections:
            return
        dead = []
        for ws in self.user_connections[user_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.user_connections[user_id].discard(ws)

    def get_online_users(self) -> list:
        return [uid for uid, conns in self.user_connections.items() if conns]

    def channel_count(self, channel: str) -> int:
        return len(self.active.get(channel, set()))


manager = ConnectionManager()
