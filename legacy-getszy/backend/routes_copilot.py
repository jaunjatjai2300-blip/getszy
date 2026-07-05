"""Getszy Copilot - natural language to skill invocation.

The Copilot uses the configured LLM to:
  1. Understand a user message
  2. Either reply conversationally, OR decide to call a skill
  3. Stream the result back to the chat panel

We keep the prompt deliberately small: pass the skill catalog (name + description)
as system context and let the LLM produce a JSON tool-call envelope.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_admin
from db import db
from llm_provider import chat_completion
from skills.registry import registry
import skills.builtins  # noqa: F401

router = APIRouter(prefix='/admin/copilot', tags=['copilot'])


class ChatIn(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None  # [{role, content}]


def _skill_catalog_for_llm() -> str:
    lines = []
    for s in registry.all():
        lines.append(f'  - {s.name}: {s.description}')
    return chr(10).join(lines)


SYSTEM_PROMPT = (
    "You are Getszy Copilot, a helpful Hinglish-speaking AI operations assistant for an Indian "
    "e-commerce + AI platform. Reply briefly. When the user asks for an action that a known skill can "
    "perform, reply ONLY with a JSON object: "
    '{"action":"call_skill","skill":"<skill_name>","params":{...},"summary":"<one line>"}.  '
    "If the request is conversational or unclear, reply with normal text. Available skills:\n"
)


def _try_extract_skill_call(text: str) -> Optional[Dict[str, Any]]:
    txt = (text or '').strip()
    # Look for a JSON object
    start = txt.find('{')
    end = txt.rfind('}')
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(txt[start:end + 1])
        if isinstance(data, dict) and data.get('action') == 'call_skill' and data.get('skill'):
            return data
    except Exception:
        return None
    return None


@router.post('/chat')
async def chat(payload: ChatIn, admin=Depends(get_current_admin)):
    user_msg = (payload.message or '').strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail='Empty message')

    system = SYSTEM_PROMPT + _skill_catalog_for_llm()
    # Build a single user prompt including light history
    history_lines = []
    for h in (payload.history or [])[-6:]:
        role = 'U' if h.get('role') == 'user' else 'A'
        history_lines.append(f'{role}: {h.get("content", "")}')
    history_lines.append(f'U: {user_msg}')
    user_prompt = chr(10).join(history_lines)

    raw = await chat_completion(system, user_prompt, temperature=0.4)
    call = _try_extract_skill_call(raw or '')

    response: Dict[str, Any] = {'id': str(uuid.uuid4()), 'at': datetime.now(timezone.utc).isoformat()}
    if call:
        skill_name = call['skill']
        s = registry.get(skill_name)
        if not s:
            response['kind'] = 'text'
            response['text'] = f"Mujhe '{skill_name}' skill nahi mili."
        else:
            try:
                result = await s.run(call.get('params', {}) or {}, {'user_id': admin['id']})
                response['kind'] = 'skill_result'
                response['skill'] = skill_name
                response['summary'] = call.get('summary') or f'Ran {skill_name}'
                response['result'] = result
                # Persist
                await db.skill_runs.insert_one({
                    'id': response['id'], 'skill': skill_name, 'params': call.get('params', {}),
                    'status': 'ok', 'result': result, 'admin_id': admin['id'], 'via': 'copilot',
                    'started_at': response['at'], 'ended_at': datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                response['kind'] = 'error'
                response['text'] = f'Skill failed: {e}'
    else:
        response['kind'] = 'text'
        response['text'] = (raw or '').strip()

    await db.copilot_messages.insert_one({
        'id': response['id'], 'user_id': admin['id'], 'user_msg': user_msg, 'response': response,
        'created_at': response['at'],
    })
    return response


@router.get('/history')
async def history(limit: int = 30, admin=Depends(get_current_admin)):
    cur = db.copilot_messages.find({'user_id': admin['id']}, {'_id': 0}).sort('created_at', -1).limit(limit)
    items = [doc async for doc in cur]
    items.reverse()
    return {'items': items}
