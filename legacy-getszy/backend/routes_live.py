"""AI Live Co-Host — Neo co-pilots a creator's livestream.

Real, useful feature (not a fake): given a show topic/vibe, Neo generates an on-air
opening + a queue of co-host cues (teleprompter) and can suggest the co-host's next
line in real time based on what the host just said. No streaming infra required.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from db import db

router = APIRouter(prefix='/live', tags=['live'])


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LiveSessionIn(BaseModel):
    topic: str
    vibe: Optional[str] = "energetic"   # energetic|chill|professional|funny
    audience: Optional[str] = ""
    platform: Optional[str] = "youtube"


class LiveLineIn(BaseModel):
    transcript: str = ""                # what the host just said


@router.get('/topics')
async def topics(_=Depends(get_current_user)):
    return {'topics': [
        'Q&A with my audience — clear their top doubts live',
        'Product launch livestream — build the hype',
        'Behind the scenes of my creator journey',
        'Reacting to comments live with the audience',
        'Tutorial / walkthrough session',
    ]}


@router.post('/session')
async def create_session(body: LiveSessionIn, user=Depends(get_current_user)):
    if len(body.topic.strip()) < 4:
        raise HTTPException(400, 'Topic is too short')
    try:
        from llm_provider import chat_completion
    except Exception:
        raise HTTPException(503, 'AI service temporarily unavailable')

    system = ("You are Neo, an AI live co-host for a content creator's livestream. Given the show topic, vibe, "
             "audience and platform, produce a JSON object with: 'opening' (the co-host's 2-3 sentence on-air "
             "intro), 'segments' (array of 4-6 co-host cue objects each with 'title' and 'line' — short spoken "
             "lines the co-host says to keep the show moving), and 'cta' (a call-to-action the co-host repeats). "
             "Respond with ONLY the JSON object, no code fences.")
    prompt = (f"Topic: {body.topic}\nVibe: {body.vibe}\nAudience: {body.audience}\nPlatform: {body.platform}\n\n"
              "Return JSON: {'opening':'…','segments':[{'title':'…','line':'…'}],'cta':'…'}")
    try:
        raw = await chat_completion(system=system, user=prompt, temperature=0.6,
                                    session_id=f'live-{uuid.uuid4().hex[:8]}')
    except Exception:
        raise HTTPException(503, 'AI service temporarily unavailable')

    import json as _json
    import re as _re
    raw = (raw or '').strip()
    raw = _re.sub(r'^```(?:json)?\s*', '', raw)
    raw = _re.sub(r'\s*```\s*$', '', raw)
    m = _re.search(r'\{.*\}', raw, _re.DOTALL)
    if m:
        raw = m.group(0)
    try:
        data = _json.loads(raw)
    except Exception:
        raise HTTPException(500, f'Could not parse live plan JSON. Raw: {raw[:200]}')

    opening = str(data.get('opening', '')).strip()
    segments = [
        {'id': str(uuid.uuid4()),
         'title': str(s.get('title', '')).strip()[:200],
         'line': str(s.get('line', '')).strip()[:600]}
        for s in (data.get('segments') or []) if isinstance(s, dict) and str(s.get('line', '')).strip()
    ]
    cta = str(data.get('cta', '')).strip()
    doc = {'id': str(uuid.uuid4()), 'user_id': user['id'],
           'topic': body.topic.strip()[:300], 'vibe': body.vibe,
           'audience': (body.audience or '')[:300], 'platform': body.platform,
           'opening': opening, 'segments': segments, 'cta': cta,
           'cursor': 0, 'created_at': _iso(), 'updated_at': _iso()}
    await db.live_sessions.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.get('/session/{session_id}')
async def get_session(session_id: str, user=Depends(get_current_user)):
    doc = await db.live_sessions.find_one({'id': session_id, 'user_id': user['id']}, {'_id': 0})
    if not doc:
        raise HTTPException(404, 'session not found')
    return doc


@router.post('/session/{session_id}/next')
async def next_cue(session_id: str, user=Depends(get_current_user)):
    doc = await db.live_sessions.find_one({'id': session_id, 'user_id': user['id']}, {'_id': 0})
    if not doc:
        raise HTTPException(404, 'session not found')
    segs = doc.get('segments') or []
    cursor = doc.get('cursor', 0)
    if cursor >= len(segs):
        return {'done': True, 'cta': doc.get('cta', ''), 'cue': None, 'progress': f'{len(segs)}/{len(segs)}'}
    cue = segs[cursor]
    new_cursor = cursor + 1
    await db.live_sessions.update_one({'id': session_id}, {'$set': {'cursor': new_cursor, 'updated_at': _iso()}})
    return {'done': False, 'cue': cue, 'cta': doc.get('cta', ''), 'progress': f'{new_cursor}/{len(segs)}'}


@router.post('/session/{session_id}/suggest')
async def suggest_line(session_id: str, body: LiveLineIn, user=Depends(get_current_user)):
    """Given what the host just said, Neo suggests the co-host's next spoken line."""
    doc = await db.live_sessions.find_one({'id': session_id, 'user_id': user['id']}, {'_id': 0})
    if not doc:
        raise HTTPException(404, 'session not found')
    try:
        from llm_provider import chat_completion
    except Exception:
        raise HTTPException(503, 'AI service temporarily unavailable')
    system = ("You are Neo, an AI live co-host. The host just said the line below during a livestream about "
             f"\"{doc.get('topic', '')}\". Suggest the co-host's natural next spoken line (1-2 sentences, match the "
             f"vibe: {doc.get('vibe', '')}). Respond with ONLY the line, no quotes, no preamble.")
    try:
        line = await chat_completion(system=system, user=body.transcript or '(host paused)',
                                     temperature=0.7, session_id=f'suggest-{session_id}')
    except Exception:
        raise HTTPException(503, 'AI service temporarily unavailable')
    return {'line': (line or '').strip()}
