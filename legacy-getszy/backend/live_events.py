"""Live admin event broadcaster (Tier 2 #10).

Lets any backend mutation push a real-time event to connected admins over
the existing WebSocket manager (channel 'admin-live').
"""
import asyncio
from datetime import datetime, timezone

from websocket_manager import manager
from automation_engine import trigger_automations


def _deliver(msg):
    """Send to the WS manager. The real manager.broadcast is a coroutine, so we
    schedule it on the running loop; a synchronous manager (tests) just returns."""
    result = manager.broadcast('admin-live', msg)
    if asyncio.iscoroutine(result):
        _schedule(result)


def _schedule(coro):
    try:
        asyncio.get_running_loop().create_task(coro)
        return
    except RuntimeError:
        pass
    try:
        asyncio.run(coro)
    except Exception:
        pass


def broadcast_admin_event(event_type: str, payload: dict):
    """Push a real-time event to all admins watching the live channel."""
    try:
        _deliver({
            'type': event_type,
            'payload': payload,
            'ts': datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass
    # Fire automation rules (notify / webhook / tag / log) — fire-and-forget.
    try:
        trigger_automations(event_type, payload)
    except Exception:
        pass
