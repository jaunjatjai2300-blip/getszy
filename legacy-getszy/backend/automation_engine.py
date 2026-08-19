"""Automation engine (Tier 2 #11).

Admins define trigger -> condition -> action rules. When a live event fires
(see live_events.broadcast_admin_event), the engine evaluates every enabled
rule whose trigger matches and runs its actions.

Actions implemented:
  - notify   : insert a DB notification (+ push to admins)
  - webhook  : POST JSON {event_type, payload} to a URL
  - tag      : record a tag on the entity in db.automation_tags
  - log      : append to db.automation_logs (audit)
"""
import asyncio
import ipaddress
import socket
import urllib.parse
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from db import db


# Block webhook targets that point at internal/metadata/link-local resources
# (SSRF defense). Only public http/https destinations are allowed.
_BLOCKED_NETWORKS = (
    ipaddress.ip_network('0.0.0.0/8'),
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('100.64.0.0/10'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),        # cloud metadata
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.0.0.0/24'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('198.18.0.0/15'),
    ipaddress.ip_network('198.51.100.0/24'),
    ipaddress.ip_network('203.0.113.0/24'),
    ipaddress.ip_network('224.0.0.0/4'),
    ipaddress.ip_network('240.0.0.0/4'),
    ipaddress.ip_network('255.255.255.255/32'),
    ipaddress.ip_network('::/128'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
    ipaddress.ip_network('fe80::/10'),
    ipaddress.ip_network('ff00::/8'),
)


async def _is_safe_webhook_url(url: str) -> bool:
    """Return True only for URLs that are safe to fetch server-side (no SSRF)."""
    if not url or not isinstance(url, str):
        return False
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        return False
    if not parsed.hostname:
        return False
    # Reject raw IP literals that are private/reserved. For hostnames, resolve and
    # reject if ANY resolved address is blocked. Runs off-thread to avoid blocking the loop.
    def _blocked() -> bool:
        try:
            infos = socket.getaddrinfo(parsed.hostname, None)
        except socket.gaierror:
            return True  # cannot resolve -> refuse
        for info in infos:
            addr = info[4][0]
            # Strip IPv6 scope id if present
            addr = addr.split('%')[0]
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                return True
            if ip.version == 6 and ip.ipv4_mapped is not None:
                ip = ip.ipv4_mapped
            if any(ip in net for net in _BLOCKED_NETWORKS):
                return True
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return True
        return False
    return not await asyncio.to_thread(_blocked)


def _get_path(obj: dict, path: str) -> Any:
    cur = obj
    for part in path.split('.'):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


_OPS = {
    '>': lambda a, b: _num(a) > _num(b),
    'gt': lambda a, b: _num(a) > _num(b),
    '<': lambda a, b: _num(a) < _num(b),
    'lt': lambda a, b: _num(a) < _num(b),
    '>=': lambda a, b: _num(a) >= _num(b),
    'gte': lambda a, b: _num(a) >= _num(b),
    '<=': lambda a, b: _num(a) <= _num(b),
    'lte': lambda a, b: _num(a) <= _num(b),
    '==': lambda a, b: str(a) == str(b),
    '=': lambda a, b: str(a) == str(b),
    'eq': lambda a, b: str(a) == str(b),
    '!=': lambda a, b: str(a) != str(b),
    'ne': lambda a, b: str(a) != str(b),
    'contains': lambda a, b: str(b) in str(a),
    'in': lambda a, b: str(a) in str(b).split(','),
    'exists': lambda a, b: (a is not None) == (str(b).lower() != 'false'),
}


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def evaluate_condition(cond: dict, payload: dict) -> bool:
    field = cond.get('field')
    op = cond.get('op', '==')
    expected = cond.get('value')
    actual = _get_path(payload, field) if field else payload
    fn = _OPS.get(op, _OPS['=='])
    try:
        return bool(fn(actual, expected))
    except Exception:
        return False


def match_rule(rule: dict, event_type: str, payload: dict) -> bool:
    if not rule.get('enabled', True):
        return False
    if rule.get('trigger') != event_type:
        return False
    conditions = rule.get('conditions') or []
    if not conditions:
        return True
    mode = rule.get('match', 'all')
    results = [evaluate_condition(c, payload) for c in conditions]
    return all(results) if mode == 'all' else any(results)


async def _action_notify(rule: dict, action: dict, payload: dict, event_type: str):
    title = action.get('title') or f"Automation: {rule.get('name', 'rule')}"
    message = action.get('message') or f"{event_type} -> {payload}"
    target = action.get('target_user')
    ts = datetime.now(timezone.utc).isoformat()
    users = []
    if target:
        users = [target]
    else:
        cur = db.users.find({'role': 'admin'}, {'id': 1, '_id': 0})
        users = [u['id'] async for u in cur]
    if not users:
        return {'action': 'notify', 'delivered': 0}
    sent = 0
    from websocket_manager import manager
    for uid in users:
        notif = {
            'id': str(uuid.uuid4()),
            'user_id': uid,
            'title': title,
            'message': message,
            'type': action.get('type', 'info'),
            'read': False,
            'created_at': ts,
            'source': 'automation',
            'rule_id': rule.get('id'),
        }
        await db.notifications.insert_one(notif)
        try:
            manager.send_to_user(uid, {'type': 'notification', 'title': title, 'message': message})
        except Exception:
            pass
        sent += 1
    return {'action': 'notify', 'delivered': sent}


async def _action_webhook(rule: dict, action: dict, payload: dict, event_type: str):
    import json
    import urllib.request

    url = action.get('url')
    if not url:
        return {'action': 'webhook', 'ok': False, 'error': 'no url'}
    if not await _is_safe_webhook_url(url):
        return {'action': 'webhook', 'ok': False, 'error': 'url blocked: only public http(s) endpoints are allowed'}

    # Build an opener that does NOT follow redirects, so a 3xx cannot bounce us to
    # an internal/metadata address after the initial host passed validation.
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    data = json.dumps({'event_type': event_type, 'payload': payload, 'rule': rule.get('name')}).encode()
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(req, timeout=5) as resp:
            return {'action': 'webhook', 'ok': True, 'status': resp.status}
    except Exception as e:
        return {'action': 'webhook', 'ok': False, 'error': str(e)[:200]}


async def _action_tag(rule: dict, action: dict, payload: dict, event_type: str):
    ref = payload.get('order_number') or payload.get('email') or payload.get('id') or event_type
    tag = action.get('tag', rule.get('name', 'automated'))
    doc = {
        'id': str(uuid.uuid4()),
        'rule_id': rule.get('id'),
        'ref': str(ref),
        'tag': tag,
        'event_type': event_type,
        'ts': datetime.now(timezone.utc).isoformat(),
    }
    await db.automation_tags.insert_one(doc)
    return {'action': 'tag', 'tag': tag, 'ref': str(ref)}


async def _action_log(rule: dict, action: dict, payload: dict, event_type: str):
    await db.automation_logs.insert_one({
        'id': str(uuid.uuid4()),
        'rule_id': rule.get('id'),
        'event_type': event_type,
        'payload': payload,
        'note': action.get('note', ''),
        'ts': datetime.now(timezone.utc).isoformat(),
    })
    return {'action': 'log', 'ok': True}


_DISPATCH = {
    'notify': _action_notify,
    'webhook': _action_webhook,
    'tag': _action_tag,
    'log': _action_log,
}


async def run_automations(event_type: str, payload: dict):
    """Evaluate and execute all matching enabled automation rules."""
    results = []
    if not event_type or not isinstance(payload, dict):
        return results
    cur = db.automations.find({'enabled': True, 'trigger': event_type}, {'_id': 0})
    async for rule in cur:
        if not match_rule(rule, event_type, payload):
            continue
        rule_results = []
        for action in rule.get('actions') or []:
            fn = _DISPATCH.get(action.get('type'))
            if not fn:
                continue
            try:
                rule_results.append(await fn(rule, action, payload, event_type))
            except Exception as e:
                rule_results.append({'action': action.get('type'), 'ok': False, 'error': str(e)[:200]})
        await db.automation_logs.insert_one({
            'id': str(uuid.uuid4()),
            'rule_id': rule.get('id'),
            'rule_name': rule.get('name'),
            'event_type': event_type,
            'payload': payload,
            'results': rule_results,
            'ts': datetime.now(timezone.utc).isoformat(),
        })
        results.append({'rule_id': rule.get('id'), 'rule_name': rule.get('name'), 'results': rule_results})
    return results


def trigger_automations(event_type: str, payload: dict):
    """Fire-and-forget scheduler to be called from a sync broadcast helper."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(run_automations(event_type, payload))
    except Exception:
        pass
