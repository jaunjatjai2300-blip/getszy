"""Live admin event broadcaster (Tier 2 #10).

Lets any backend mutation push a real-time event to connected admins over
the existing WebSocket manager (channel 'admin-live').
"""
from datetime import datetime, timezone

from websocket_manager import manager


def broadcast_admin_event(event_type: str, payload: dict):
    """Push a real-time event to all admins watching the live channel."""
    try:
        manager.broadcast('admin-live', {
            'type': event_type,
            'payload': payload,
            'ts': datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass
