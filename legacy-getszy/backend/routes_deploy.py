"""Phase 9 - Master Build-&-Deploy Dashboard.

Admin can trigger an agent-swarm style pipeline that:
  1. Plans a feature/page from a natural-language brief
  2. Records the deploy intent
  3. Optionally pushes a marker commit to GitHub via PAT
  4. Triggers VPS pull (via webhook url the user configures on the VPS)

Secrets used (env, never logged):
  GITHUB_TOKEN, GITHUB_REPO (e.g. jaunjatjai2300-blip/getszy), DEPLOY_WEBHOOK_URL

If GITHUB_TOKEN / REPO are not configured the endpoints work in DRY-RUN mode and
return a clear preview instead of attempting real network operations.
"""
import os
import uuid
import asyncio
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_admin
from db import db
from llm_provider import chat_completion

logger = logging.getLogger('getszy.deploy')
router = APIRouter(prefix='/admin/deploy', tags=['deploy'])

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '').strip()
GITHUB_REPO = os.environ.get('GITHUB_REPO', '').strip()  # owner/repo
DEPLOY_WEBHOOK_URL = os.environ.get('DEPLOY_WEBHOOK_URL', '').strip()


class BuildIn(BaseModel):
    brief: str
    target: str = 'page'  # page | landing | tool | bundle
    autopush: bool = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _redact(token: str) -> str:
    if not token:
        return ''
    if len(token) < 10:
        return '****'
    return f'{token[:4]}...{token[-4:]}'


@router.get('/status')
async def status(_=Depends(get_current_admin)):
    return {
        'github': {
            'configured': bool(GITHUB_TOKEN and GITHUB_REPO),
            'repo': GITHUB_REPO or '(not set)',
            'token_preview': _redact(GITHUB_TOKEN),
        },
        'webhook': {
            'configured': bool(DEPLOY_WEBHOOK_URL),
            'url': DEPLOY_WEBHOOK_URL or '(not set)',
        },
        'guide': {
            'env_keys': ['GITHUB_TOKEN', 'GITHUB_REPO', 'DEPLOY_WEBHOOK_URL'],
            'webhook_instructions': "On your VPS run: docker run -d --restart=always -p 9000:9000 -e WEBHOOK_TOKEN=<secret> -v /opt/getszy:/repo deploy/webhook. Then point DEPLOY_WEBHOOK_URL at https://getszy.com/hooks/deploy.",
        },
    }


# ===== Agent Swarm Pipeline =====
async def _agent_call(role: str, system: str, user: str, temperature: float = 0.4) -> str:
    try:
        out = await chat_completion(system, user, temperature=temperature)
        return (out or '').strip()
    except Exception as e:
        logger.warning(f'agent {role} failed: {e}')
        return f'[{role} unavailable: {e}]'


async def _run_swarm(brief: str, target: str) -> Dict[str, Any]:
    """Run the 6-agent orchestration pipeline (returns a structured plan)."""
    planner_sys = 'You are an elite product planner for a multi-purpose AI-native e-commerce platform called Getszy. Break the brief into 4-6 concrete build steps.'
    coder_sys = 'You are a senior full-stack engineer. Given a plan, write a concise implementation summary (no code, just clear technical steps).'
    designer_sys = 'You are a UI/UX designer focused on premium minimal aesthetics. Suggest layout + color tokens.'
    reviewer_sys = 'You are a strict QA reviewer. Spot risks, missing pieces, and acceptance criteria.'

    plan, design = await asyncio.gather(
        _agent_call('planner', planner_sys, f'Brief: {brief}\nTarget: {target}\nReply with a numbered list of build steps.'),
        _agent_call('designer', designer_sys, f'Suggest 5 design tokens (colors, type, spacing) for: {brief}'),
    )
    impl, review = await asyncio.gather(
        _agent_call('coder', coder_sys, f'Plan:\n{plan}\nProduce a concise implementation summary.'),
        _agent_call('reviewer', reviewer_sys, f'Plan:\n{plan}\nList top 3 risks and acceptance criteria.'),
    )
    return {
        'planner': plan,
        'designer': design,
        'coder': impl,
        'reviewer': review,
    }


@router.post('/build')
async def build(payload: BuildIn, admin=Depends(get_current_admin)):
    """Run the agent swarm to plan a deployable change, persist it, and return the plan."""
    brief = (payload.brief or '').strip()
    if len(brief) < 8:
        raise HTTPException(status_code=400, detail='Brief is too short')

    swarm = await _run_swarm(brief, payload.target)
    job_id = str(uuid.uuid4())
    job = {
        'id': job_id,
        'brief': brief,
        'target': payload.target,
        'admin_id': admin['id'],
        'status': 'planned',
        'agents': swarm,
        'deploy_status': None,
        'created_at': _now(),
    }
    await db.deploy_jobs.insert_one(job)

    deploy_result = None
    if payload.autopush:
        deploy_result = await _push_marker_commit(job_id, brief, swarm)
        await db.deploy_jobs.update_one({'id': job_id}, {'$set': {'deploy_status': deploy_result, 'status': 'pushed' if deploy_result.get('ok') else 'planned'}})

    job.pop('_id', None)
    job['deploy_status'] = deploy_result
    return job


async def _push_marker_commit(job_id: str, brief: str, swarm: Dict[str, Any]) -> Dict[str, Any]:
    """Push a small marker file to the repo via the GitHub Contents API.

    This proves the pipeline is wired end-to-end without yet writing application
    code. Real code generation will be added in a follow-up once the deploy loop
    is verified safe.
    """
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return {'ok': False, 'mode': 'dry_run', 'message': 'GITHUB_TOKEN / GITHUB_REPO not configured. Plan saved locally only.'}
    path = f'.getszy/deploy-jobs/{job_id}.md'
    content_md = (
        f'# Getszy Deploy Job {job_id}\n\n'
        f'**When:** {_now()}\n\n'
        f'**Brief:** {brief}\n\n'
        f'## Planner\n{swarm.get("planner", "")}\n\n'
        f'## Designer\n{swarm.get("designer", "")}\n\n'
        f'## Coder\n{swarm.get("coder", "")}\n\n'
        f'## Reviewer\n{swarm.get("reviewer", "")}\n'
    )
    import base64
    b64 = base64.b64encode(content_md.encode()).decode()
    url = f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}'
    headers = {'Authorization': f'Bearer {GITHUB_TOKEN}', 'Accept': 'application/vnd.github+json'}
    body = {
        'message': f'getszy ai-ops: deploy job {job_id[:8]}',
        'content': b64,
        'branch': os.environ.get('GITHUB_BRANCH', 'main'),
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.put(url, json=body, headers=headers)
        if r.status_code in (200, 201):
            data = r.json()
            return {'ok': True, 'mode': 'live', 'commit_sha': (data.get('commit') or {}).get('sha'), 'path': path}
        return {'ok': False, 'mode': 'live', 'http': r.status_code, 'message': r.text[:200]}
    except Exception as e:
        return {'ok': False, 'mode': 'live', 'message': str(e)}


@router.post('/{job_id}/push')
async def push_existing(job_id: str, _=Depends(get_current_admin)):
    job = await db.deploy_jobs.find_one({'id': job_id}, {'_id': 0})
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    res = await _push_marker_commit(job_id, job.get('brief', ''), job.get('agents', {}))
    await db.deploy_jobs.update_one({'id': job_id}, {'$set': {'deploy_status': res, 'status': 'pushed' if res.get('ok') else job.get('status')}})
    return res


@router.post('/{job_id}/webhook')
async def fire_webhook(job_id: str, _=Depends(get_current_admin)):
    if not DEPLOY_WEBHOOK_URL:
        return {'ok': False, 'message': 'DEPLOY_WEBHOOK_URL not configured. Set this env var on the backend to enable VPS auto-pull.'}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(DEPLOY_WEBHOOK_URL, json={'job_id': job_id, 'at': _now()})
        return {'ok': r.status_code < 400, 'http': r.status_code, 'response': r.text[:200]}
    except Exception as e:
        return {'ok': False, 'message': str(e)}


@router.get('/jobs')
async def list_jobs(limit: int = 25, _=Depends(get_current_admin)):
    cur = db.deploy_jobs.find({}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'items': [doc async for doc in cur]}


@router.get('/jobs/{job_id}')
async def get_job(job_id: str, _=Depends(get_current_admin)):
    job = await db.deploy_jobs.find_one({'id': job_id}, {'_id': 0})
    if not job:
        raise HTTPException(status_code=404, detail='Not found')
    return job


@router.get('/commits')
async def recent_commits(limit: int = 10, _=Depends(get_current_admin)):
    """Fetch recent commits from configured GitHub repo (for rollback context)."""
    if not (GITHUB_TOKEN and GITHUB_REPO):
        return {'ok': False, 'message': 'GITHUB_TOKEN / GITHUB_REPO not configured', 'items': []}
    url = f'https://api.github.com/repos/{GITHUB_REPO}/commits?per_page={min(limit, 30)}'
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, headers={
                'Authorization': f'Bearer {GITHUB_TOKEN}',
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28',
            })
        if r.status_code >= 400:
            return {'ok': False, 'message': f'GitHub returned {r.status_code}', 'items': []}
        data = r.json() or []
        items = [{
            'sha': c.get('sha', '')[:12],
            'sha_full': c.get('sha', ''),
            'message': (c.get('commit', {}).get('message') or '').split('\n')[0][:200],
            'author': c.get('commit', {}).get('author', {}).get('name'),
            'date': c.get('commit', {}).get('author', {}).get('date'),
            'html_url': c.get('html_url'),
        } for c in data]
        return {'ok': True, 'items': items, 'repo': GITHUB_REPO}
    except Exception as e:
        return {'ok': False, 'message': str(e), 'items': []}
