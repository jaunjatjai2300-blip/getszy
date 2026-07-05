"""Project Workspace API — expands chat_projects into a full workspace.

Every chat project already stores: chat_messages, chat_events, chat_assets.
This module adds first-class support for:
  - Plan (a structured LLM-written project plan)
  - Tasks (checklist items the user or Neo maintains)
  - Timeline (chronologically merged events + messages + asset creations + deployments)
  - Versions (snapshots of the workspace state — for rollback)
  - Deployments (references — actual deploy lives in existing routes_deploy)

Backward compatibility: all data lives in NEW collections that reference chat_projects
by id, so existing endpoints/collections are untouched.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from db import db

router = APIRouter(prefix='/workspace', tags=['workspace'])


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _project_or_404(project_id: str, user: dict) -> dict:
    doc = await db.chat_projects.find_one({'id': project_id, 'user_id': user['id']}, {'_id': 0})
    if not doc:
        raise HTTPException(404, 'workspace not found')
    return doc


# ---------- Full workspace view ----------
@router.get('/{project_id}')
async def get_workspace(project_id: str, user=Depends(get_current_user)):
    """Return the complete workspace: project + chat + assets + plan + tasks + timeline + versions."""
    project = await _project_or_404(project_id, user)
    messages = [m async for m in db.chat_messages.find({'project_id': project_id}, {'_id': 0}).sort('created_at', 1)]
    assets = [a async for a in db.chat_assets.find({'project_id': project_id}, {'_id': 0}).sort('created_at', 1)]
    plan = await db.workspace_plans.find_one({'project_id': project_id}, {'_id': 0})
    tasks = [t async for t in db.workspace_tasks.find({'project_id': project_id}, {'_id': 0}).sort('created_at', 1)]
    versions = [v async for v in db.workspace_versions.find({'project_id': project_id}, {'_id': 0}).sort('created_at', -1).limit(20)]
    deployments = [d async for d in db.workspace_deployments.find({'project_id': project_id}, {'_id': 0}).sort('created_at', -1).limit(30)]
    return {'project': project, 'messages': messages, 'assets': assets,
            'plan': plan, 'tasks': tasks, 'versions': versions, 'deployments': deployments}


# ---------- Pin / Unpin assets ----------
class PinIn(BaseModel):
    pinned: bool = True


@router.patch('/{project_id}/asset/{asset_id}/pin')
async def pin_asset(project_id: str, asset_id: str, body: PinIn, user=Depends(get_current_user)):
    await _project_or_404(project_id, user)
    r = await db.chat_assets.update_one(
        {'id': asset_id, 'project_id': project_id, 'user_id': user['id']},
        {'$set': {'pinned': bool(body.pinned), 'pinned_at': _iso() if body.pinned else None}}
    )
    if r.matched_count == 0:
        raise HTTPException(404, 'asset not found')
    return {'ok': True, 'pinned': bool(body.pinned)}


# ---------- Auto-plan from chat (Neo generates plan) ----------
@router.post('/{project_id}/plan/generate')
async def generate_plan(project_id: str, user=Depends(get_current_user)):
    """Ask the LLM to summarize the chat so far into a plan + steps."""
    project = await _project_or_404(project_id, user)
    msgs = [m async for m in db.chat_messages.find({'project_id': project_id}, {'_id': 0, 'role': 1, 'content': 1}).sort('created_at', 1).limit(40)]
    if len(msgs) < 2:
        raise HTTPException(400, 'Not enough conversation to plan — chat some more first')

    try:
        from llm_provider import chat_completion
    except Exception:
        raise HTTPException(500, 'LLM provider unavailable')

    convo = '\n'.join([f"{'User' if m.get('role') == 'user' else 'Neo'}: {(m.get('content') or '')[:400]}" for m in msgs])
    system = ("You are Neo, an AI Builder. Read the conversation and produce a project PLAN as strict JSON with keys "
              "\"summary\" (1-2 sentences describing what the user is building) and \"steps\" (array of 4-8 short "
              "action-focused steps). Respond with ONLY the JSON object, no code fences, no extra prose.")
    prompt = f"Conversation so far:\n{convo}\n\nReturn JSON: {{\"summary\":\"…\",\"steps\":[\"…\"]}}"

    try:
        raw = await chat_completion(system=system, user=prompt, temperature=0.4, session_id=f'plan-{project_id}')
    except Exception as e:
        raise HTTPException(500, f'LLM error: {str(e)[:120]}')

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
        raise HTTPException(500, f'Could not parse plan JSON. Raw: {raw[:200]}')

    summary = str(data.get('summary', '')).strip()[:2000]
    steps = [str(s).strip()[:400] for s in (data.get('steps') or []) if str(s).strip()]
    if not summary:
        raise HTTPException(500, 'LLM did not return a summary')

    doc = {'project_id': project_id, 'user_id': user['id'],
           'summary': summary, 'steps': steps[:12], 'updated_at': _iso()}
    await db.workspace_plans.update_one({'project_id': project_id},
                                        {'$set': doc, '$setOnInsert': {'created_at': _iso()}}, upsert=True)
    return {'ok': True, 'summary': summary, 'steps': steps[:12]}


# ---------- Plan ----------
class PlanIn(BaseModel):
    summary: str
    steps: List[str] = []


@router.put('/{project_id}/plan')
async def set_plan(project_id: str, body: PlanIn, user=Depends(get_current_user)):
    await _project_or_404(project_id, user)
    doc = {'project_id': project_id, 'user_id': user['id'],
           'summary': body.summary.strip()[:2000],
           'steps': [s.strip()[:400] for s in (body.steps or []) if s.strip()],
           'updated_at': _iso()}
    await db.workspace_plans.update_one({'project_id': project_id},
                                        {'$set': doc, '$setOnInsert': {'created_at': _iso()}}, upsert=True)
    return {'ok': True}


# ---------- Tasks ----------
class TaskIn(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = 'todo'  # todo|doing|done|blocked
    priority: str = 'normal'  # low|normal|high


class TaskPatch(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None


@router.post('/{project_id}/task')
async def add_task(project_id: str, body: TaskIn, user=Depends(get_current_user)):
    await _project_or_404(project_id, user)
    doc = {'id': str(uuid.uuid4()), 'project_id': project_id, 'user_id': user['id'],
           'title': body.title.strip()[:280], 'description': (body.description or '').strip()[:2000],
           'status': body.status, 'priority': body.priority,
           'created_at': _iso(), 'updated_at': _iso()}
    await db.workspace_tasks.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.patch('/{project_id}/task/{task_id}')
async def update_task(project_id: str, task_id: str, body: TaskPatch, user=Depends(get_current_user)):
    upd = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    upd['updated_at'] = _iso()
    r = await db.workspace_tasks.update_one({'id': task_id, 'project_id': project_id, 'user_id': user['id']}, {'$set': upd})
    if r.matched_count == 0:
        raise HTTPException(404, 'task not found')
    doc = await db.workspace_tasks.find_one({'id': task_id}, {'_id': 0})
    return doc


@router.delete('/{project_id}/task/{task_id}')
async def delete_task(project_id: str, task_id: str, user=Depends(get_current_user)):
    r = await db.workspace_tasks.delete_one({'id': task_id, 'project_id': project_id, 'user_id': user['id']})
    return {'deleted': r.deleted_count}


# ---------- Versions (snapshot) ----------
class VersionIn(BaseModel):
    label: Optional[str] = None


@router.post('/{project_id}/version')
async def snapshot(project_id: str, body: VersionIn, user=Depends(get_current_user)):
    await _project_or_404(project_id, user)
    # Count-only snapshot (lightweight) — captures message + asset counts + last asset kind.
    n_messages = await db.chat_messages.count_documents({'project_id': project_id})
    n_assets = await db.chat_assets.count_documents({'project_id': project_id})
    last_asset = await db.chat_assets.find_one({'project_id': project_id}, {'_id': 0, 'kind': 1, 'title': 1},
                                                sort=[('created_at', -1)])
    doc = {'id': str(uuid.uuid4()), 'project_id': project_id, 'user_id': user['id'],
           'label': (body.label or '').strip()[:120] or f'v{n_messages}-{n_assets}',
           'message_count': n_messages, 'asset_count': n_assets,
           'last_asset': last_asset, 'created_at': _iso()}
    await db.workspace_versions.insert_one(doc)
    doc.pop('_id', None)
    return doc


# ---------- Timeline ----------
@router.get('/{project_id}/timeline')
async def timeline(project_id: str, limit: int = 100, user=Depends(get_current_user)):
    await _project_or_404(project_id, user)
    items: List[Dict[str, Any]] = []
    async for m in db.chat_messages.find({'project_id': project_id}, {'_id': 0}).sort('created_at', 1).limit(limit):
        items.append({'type': 'message', 'at': m['created_at'], 'data': m})
    async for a in db.chat_assets.find({'project_id': project_id}, {'_id': 0}).sort('created_at', 1).limit(limit):
        items.append({'type': 'asset', 'at': a['created_at'], 'data': a})
    async for e in db.chat_events.find({'project_id': project_id, 'kind': {'$in': ['progress', 'done', 'error']}}, {'_id': 0}).sort('created_at', 1).limit(limit):
        items.append({'type': 'event', 'at': e['created_at'], 'data': e})
    async for d in db.workspace_deployments.find({'project_id': project_id}, {'_id': 0}).sort('created_at', 1).limit(limit):
        items.append({'type': 'deployment', 'at': d['created_at'], 'data': d})
    items.sort(key=lambda x: x['at'])
    return {'items': items[-limit:]}


# ---------- Deployments (metadata; actual deploy uses existing webhook) ----------
class DeploymentIn(BaseModel):
    kind: str  # webapp | starter | channel | video | other
    target: str  # e.g. subdomain, github repo path
    url: Optional[str] = None
    meta: Dict[str, Any] = {}


@router.post('/{project_id}/deployment')
async def record_deployment(project_id: str, body: DeploymentIn, user=Depends(get_current_user)):
    await _project_or_404(project_id, user)
    doc = {'id': str(uuid.uuid4()), 'project_id': project_id, 'user_id': user['id'],
           'kind': body.kind, 'target': body.target, 'url': body.url,
           'meta': body.meta or {}, 'status': 'recorded', 'created_at': _iso()}
    await db.workspace_deployments.insert_one(doc)
    doc.pop('_id', None)
    return doc
