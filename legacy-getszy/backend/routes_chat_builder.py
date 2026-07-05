"""Universal AI Chat Builder — REST routes.

All endpoints under /api/chat/*, auth required.
Every user message goes through `orchestrator.process_message` which detects
intent, dispatches to the correct existing backend capability, and stores the
result against the project.

Progress is delivered via a lightweight polling endpoint (`/session/{id}/events`).
SSE/WebSockets can be plugged later without changing the client contract.
"""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from auth import get_current_user
from db import db
from chat_builder.orchestrator import process_message
from chat_builder.capabilities import CAPABILITIES

router = APIRouter(prefix='/chat', tags=['chat-builder'])


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class NewSessionIn(BaseModel):
    title: Optional[str] = None
    first_message: Optional[str] = None


class SendMessageIn(BaseModel):
    content: str


@router.get('/capabilities')
async def list_capabilities(user=Depends(get_current_user)):
    """List capabilities available to the caller (role-filtered)."""
    from auth import role_level, ROLE_LEVEL
    caller = role_level(user)
    out = []
    for cid, spec in CAPABILITIES.items():
        needed = ROLE_LEVEL.get(spec.get('min_role', 'customer'), 1)
        if needed > caller:
            continue
        out.append({'id': cid, 'desc': spec['desc'], 'params': spec.get('params', {}),
                    'result_kind': spec.get('result_kind', cid),
                    'min_role': spec.get('min_role', 'customer')})
    return {'capabilities': out, 'count': len(out), 'user_role': user.get('role', 'visitor')}


@router.post('/session')
async def new_session(payload: NewSessionIn, bg: BackgroundTasks, user=Depends(get_current_user)):
    proj_id = str(uuid.uuid4())
    doc = {
        'id': proj_id, 'user_id': user['id'],
        'title': (payload.title or (payload.first_message or 'New chat')[:60]).strip() or 'New chat',
        'status': 'active', 'capabilities_used': [], 'asset_kinds_used': [],
        'created_at': _iso(), 'updated_at': _iso(),
    }
    await db.chat_projects.insert_one(doc)
    doc.pop('_id', None)
    if payload.first_message:
        # Fire-and-forget so the client can start polling immediately.
        bg.add_task(process_message, proj_id, user, payload.first_message)
    return doc


@router.get('/sessions')
async def list_sessions(limit: int = 50, user=Depends(get_current_user)):
    cur = db.chat_projects.find({'user_id': user['id']}, {'_id': 0}).sort('updated_at', -1).limit(limit)
    return {'items': [d async for d in cur]}


@router.get('/session/{sid}')
async def get_session(sid: str, user=Depends(get_current_user)):
    proj = await db.chat_projects.find_one({'id': sid, 'user_id': user['id']}, {'_id': 0})
    if not proj:
        raise HTTPException(404, 'session not found')
    messages = [m async for m in db.chat_messages.find({'project_id': sid}, {'_id': 0}).sort('created_at', 1)]
    assets = [a async for a in db.chat_assets.find({'project_id': sid}, {'_id': 0}).sort('created_at', 1)]
    return {'project': proj, 'messages': messages, 'assets': assets}


@router.post('/session/{sid}/message')
async def send_message(sid: str, payload: SendMessageIn, bg: BackgroundTasks, user=Depends(get_current_user)):
    proj = await db.chat_projects.find_one({'id': sid, 'user_id': user['id']}, {'_id': 0, 'id': 1})
    if not proj:
        raise HTTPException(404, 'session not found')
    content = (payload.content or '').strip()
    if len(content) < 1:
        raise HTTPException(400, 'empty message')
    # Kick off processing in background; client polls /events for progress.
    bg.add_task(process_message, sid, user, content)
    return {'accepted': True, 'session_id': sid}


@router.get('/session/{sid}/events')
async def get_events(sid: str, since: str = '', user=Depends(get_current_user)):
    proj = await db.chat_projects.find_one({'id': sid, 'user_id': user['id']}, {'_id': 0, 'id': 1})
    if not proj:
        raise HTTPException(404, 'session not found')
    q: Dict[str, Any] = {'project_id': sid}
    if since:
        q['created_at'] = {'$gt': since}
    cur = db.chat_events.find(q, {'_id': 0}).sort('created_at', 1).limit(200)
    events = [d async for d in cur]
    # Also return the tail messages after `since` so UI can rehydrate.
    mq: Dict[str, Any] = {'project_id': sid}
    if since:
        mq['created_at'] = {'$gt': since}
    tail = [d async for d in db.chat_messages.find(mq, {'_id': 0}).sort('created_at', 1).limit(50)]
    tail_assets = [d async for d in db.chat_assets.find(mq, {'_id': 0}).sort('created_at', 1).limit(50)]
    now = _iso()
    return {'events': events, 'messages': tail, 'assets': tail_assets, 'server_time': now}


@router.delete('/session/{sid}')
async def delete_session(sid: str, user=Depends(get_current_user)):
    proj = await db.chat_projects.find_one({'id': sid, 'user_id': user['id']})
    if not proj:
        raise HTTPException(404, 'session not found')
    await db.chat_projects.delete_one({'id': sid})
    await db.chat_messages.delete_many({'project_id': sid})
    await db.chat_events.delete_many({'project_id': sid})
    await db.chat_assets.delete_many({'project_id': sid})
    return {'ok': True}


@router.patch('/session/{sid}')
async def rename_session(sid: str, payload: NewSessionIn, user=Depends(get_current_user)):
    r = await db.chat_projects.update_one(
        {'id': sid, 'user_id': user['id']},
        {'$set': {'title': (payload.title or 'Untitled').strip()[:120], 'updated_at': _iso()}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, 'session not found')
    return {'ok': True}
