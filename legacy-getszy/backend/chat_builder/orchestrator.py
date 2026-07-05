"""Orchestrator: processes a chat turn end-to-end.

Flow:
  1. Persist the user message.
  2. Classify intent via `intents.classify`.
  3. Persist the assistant "thinking" reply + emit progress events.
  4. Dispatch to the resolved capability.
  5. Persist the capability output as an asset attached to the project.
  6. Persist the final assistant message with the asset reference.

Events are streamed via the `chat_events` collection which the frontend polls
(polling keeps infra simple; can be swapped for SSE without touching call-sites).
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Callable, Awaitable

from db import db
from chat_builder.intents import classify
from chat_builder.capabilities import CAPABILITIES


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mk_emit(project_id: str) -> Callable[[str, Dict[str, Any]], Awaitable[None]]:
    async def emit(kind: str, payload: Dict[str, Any]):
        await db.chat_events.insert_one({
            'id': str(uuid.uuid4()), 'project_id': project_id,
            'kind': kind, 'payload': payload, 'created_at': _iso(),
        })
    return emit


async def _load_history(project_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    cur = db.chat_messages.find({'project_id': project_id}, {'_id': 0}).sort('created_at', 1).limit(limit)
    return [doc async for doc in cur]


async def process_message(project_id: str, user: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    emit = _mk_emit(project_id)
    # 1. Persist the user message
    user_msg = {'id': str(uuid.uuid4()), 'project_id': project_id, 'user_id': user['id'],
                'role': 'user', 'content': user_text, 'created_at': _iso()}
    await db.chat_messages.insert_one(user_msg)
    user_msg.pop('_id', None)
    await emit('user_message', {'id': user_msg['id'], 'content': user_text})

    # 2. Fast Lane detection (rules-only, no LLM) \u2014 short-circuits classifier for simple requests
    from chat_builder.fast_lane import detect as fast_lane_detect
    from auth import role_level, ROLE_LEVEL
    caller_level = role_level(user)
    fast = fast_lane_detect(user_text, history_len=await db.chat_messages.count_documents({'project_id': project_id}))
    if fast is not None:
        intent, params, human_reply = fast
        # Verify role permission even for fast lane
        if intent in CAPABILITIES:
            needed = CAPABILITIES[intent].get('min_role', 'customer')
            if caller_level < ROLE_LEVEL.get(needed, 1):
                fast = None  # fall through to classifier / general_chat
    if fast is None:
        history = await _load_history(project_id, limit=12)
        await emit('status', {'phase': 'thinking', 'msg': 'Neo is thinking\u2026'})
        decision = await classify(user_text, history=history, min_level=caller_level)
        intent = decision['intent']
        params = decision['params']
        human_reply = decision['human_reply']
        # Server-side authorization: even if the LLM routed to a higher-privilege capability
        # by mistake, refuse if the caller lacks the required role.
        if intent in CAPABILITIES:
            needed = CAPABILITIES[intent].get('min_role', 'customer')
            if caller_level < ROLE_LEVEL.get(needed, 1):
                human_reply = f'Sorry bhai, is capability ke liye {needed} role chahiye.'
                intent = 'general_chat'
    else:
        await emit('status', {'phase': 'fast_lane', 'msg': human_reply})
    await emit('intent', {'intent': intent, 'params': params, 'reply': human_reply, 'fast_lane': fast is not None})

    # 3. Persist "acknowledging" assistant reply so the UI can render immediately
    ack = {'id': str(uuid.uuid4()), 'project_id': project_id, 'user_id': user['id'],
           'role': 'assistant', 'content': human_reply, 'intent': intent, 'meta': {'phase': 'ack'},
           'created_at': _iso()}
    await db.chat_messages.insert_one(ack)
    ack.pop('_id', None)

    result_asset = None
    if intent == 'general_chat':
        # Nothing to dispatch — the ack IS the final assistant message.
        await emit('done', {'msg': 'ok'})
        await _update_project(project_id, intent, None)
        return {'user_message': user_msg, 'assistant_message': ack, 'asset': None}

    # 4. Dispatch
    cap = CAPABILITIES[intent]
    try:
        result = await cap['run'](user, params, emit)
    except Exception as e:
        result = {'kind': 'error', 'title': f'{intent} failed', 'data': {'error': str(e)[:400]}}
        await emit('error', {'intent': intent, 'error': str(e)[:400]})

    # 5. Persist asset
    if result and result.get('kind') != 'error':
        result_asset = {
            'id': str(uuid.uuid4()), 'project_id': project_id, 'user_id': user['id'],
            'kind': result.get('kind') or cap.get('result_kind') or intent,
            'title': result.get('title', ''),
            'data': result.get('data', {}),
            'source_intent': intent, 'source_params': params,
            'created_at': _iso(),
        }
        await db.chat_assets.insert_one(result_asset)
        result_asset.pop('_id', None)
        await emit('asset', {'id': result_asset['id'], 'kind': result_asset['kind'],
                              'title': result_asset['title'], 'data': result_asset['data']})
    else:
        # Persist error asset for visibility
        result_asset = {
            'id': str(uuid.uuid4()), 'project_id': project_id, 'user_id': user['id'],
            'kind': 'error', 'title': result.get('title', 'Something failed'),
            'data': result.get('data', {}), 'source_intent': intent, 'source_params': params,
            'created_at': _iso(),
        }
        await db.chat_assets.insert_one(result_asset)
        result_asset.pop('_id', None)

    # 6. Persist final assistant message summarising the outcome
    summary = _summarize(intent, result)
    final = {'id': str(uuid.uuid4()), 'project_id': project_id, 'user_id': user['id'],
             'role': 'assistant', 'content': summary, 'intent': intent,
             'asset_id': result_asset['id'] if result_asset else None,
             'meta': {'phase': 'result'}, 'created_at': _iso()}
    await db.chat_messages.insert_one(final)
    final.pop('_id', None)
    await emit('done', {'asset_id': result_asset['id'] if result_asset else None})
    await _update_project(project_id, intent, result_asset)
    return {'user_message': user_msg, 'assistant_message': final, 'asset': result_asset}


def _summarize(intent: str, result: Dict[str, Any]) -> str:
    if not result or result.get('kind') == 'error':
        return f"Bhai, {intent} run karte waqt error aa gaya: {(result or {}).get('data', {}).get('error', 'unknown')[:200]}"
    kind = result.get('kind', intent)
    title = result.get('title', '')
    summaries = {
        'script': f'Script ready ✅ — "{title}". Right pane mein details dekh sakte ho.',
        'hook_score': f'{title} ✅',
        'viral_score': f'{title} — drivers/risks right pane mein.',
        'trends': f'{title} — open right pane to see all trending topics.',
        'competitor_gap': f'{title} — 5 content gaps identified.',
        'video_job': f'Faceless video queued ✅. 60–120 sec mein banega. Right pane mein live status track karo.',
        'channel_plan': f'Channel "{title}" plan ready ✅. Right pane mein full 30-day calendar dekh sakte ho.',
        'webapp': f'Web app "{title}" ready ✅. Right pane mein live preview iframe hai.',
        'starter_mobileapp': f'Mobile app starter zip ready ✅. Right pane se download karo.',
        'starter_fullstack': f'Full-stack starter zip ready ✅. Right pane se download karo.',
        'starter_blog': f'Blog starter zip ready ✅. Right pane se download karo.',
        'workforce_run': f'Agent output ready ✅. Right pane mein full JSON.',
        'sourcing_scan': f'{title} ✅. Right pane mein products list.',
    }
    return summaries.get(kind, f'Done ✅ — {title}')


async def _update_project(project_id: str, intent: str, asset: Dict[str, Any] | None):
    upd = {'$set': {'updated_at': _iso(), 'last_intent': intent}}
    if asset:
        upd['$addToSet'] = {'capabilities_used': intent, 'asset_kinds_used': asset.get('kind', '')}
    await db.chat_projects.update_one({'id': project_id}, upd)
