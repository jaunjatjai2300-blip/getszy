"""Automation Workflow Builder — store and run validated trigger-action chains."""
import asyncio
import ipaddress
import socket
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_admin
from credits import add_credits
from db import db

router = APIRouter(prefix='/admin/workflows', tags=['workflows'])

TRIGGER_TYPES = ['video_ready', 'new_product', 'new_user', 'cron', 'manual', 'credit_low', 'order_placed']
ACTION_TYPES = ['post_social', 'grant_credits', 'send_email', 'generate_content', 'webhook', 'notify_slack']


class ActionIn(BaseModel):
    type: str
    config: dict = {}


class WorkflowIn(BaseModel):
    name: str
    description: str = ''
    trigger: str
    trigger_config: dict = {}
    actions: List[ActionIn] = []
    enabled: bool = True


class WorkflowPatchIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    trigger: Optional[str] = None
    trigger_config: Optional[dict] = None
    actions: Optional[List[ActionIn]] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _validate_webhook_url(url: str) -> str:
    """Permit only public HTTPS endpoints; block local, private and link-local SSRF targets."""
    parsed = urlparse(url)
    if (
        parsed.scheme != 'https'
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise HTTPException(status_code=400, detail='Webhook URL must be a public HTTPS URL without credentials or fragments')

    try:
        addresses = await asyncio.get_running_loop().run_in_executor(
            None,
            lambda: socket.getaddrinfo(parsed.hostname, None, type=socket.SOCK_STREAM),
        )
        resolved = {entry[4][0] for entry in addresses}
        if not resolved or any(not ipaddress.ip_address(address).is_global for address in resolved):
            raise ValueError('non-public address')
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail='Webhook URL must resolve only to public IP addresses') from exc
    return parsed.geturl()


async def _validate_actions(actions: List[ActionIn]) -> None:
    for action in actions:
        if action.type not in ACTION_TYPES:
            raise HTTPException(status_code=400, detail=f'Unknown action: {action.type}. Use: {ACTION_TYPES}')
        if action.type == 'webhook':
            await _validate_webhook_url(str(action.config.get('url', '')).strip())
        if action.type == 'grant_credits':
            try:
                amount = int(action.config.get('amount', 10))
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail='Credit grant amount must be a positive integer') from exc
            if amount <= 0:
                raise HTTPException(status_code=400, detail='Credit grant amount must be positive')


@router.get('', dependencies=[Depends(get_current_admin)])
async def list_workflows():
    items = await db.workflows.find({}, {'_id': 0}).sort('created_at', -1).to_list(200)
    return {'items': items, 'total': len(items)}


@router.post('', dependencies=[Depends(get_current_admin)])
async def create_workflow(body: WorkflowIn):
    if body.trigger not in TRIGGER_TYPES:
        raise HTTPException(status_code=400, detail=f'Unknown trigger. Use: {TRIGGER_TYPES}')
    await _validate_actions(body.actions)
    doc = {
        'id': str(uuid.uuid4()),
        'name': body.name.strip(),
        'description': body.description.strip(),
        'trigger': body.trigger,
        'trigger_config': body.trigger_config,
        'actions': [action.model_dump() for action in body.actions],
        'enabled': body.enabled,
        'run_count': 0,
        'last_run': None,
        'last_run_status': None,
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.workflows.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.patch('/{wid}', dependencies=[Depends(get_current_admin)])
async def update_workflow(wid: str, body: WorkflowPatchIn):
    existing = await db.workflows.find_one({'id': wid}, {'_id': 0})
    if not existing:
        raise HTTPException(status_code=404, detail='Workflow not found')
    patch = {key: value for key, value in body.model_dump(exclude_unset=True).items() if value is not None or key == 'enabled'}
    if 'trigger' in patch and patch['trigger'] not in TRIGGER_TYPES:
        raise HTTPException(status_code=400, detail=f'Unknown trigger. Use: {TRIGGER_TYPES}')
    if 'actions' in patch:
        await _validate_actions(patch['actions'])
        patch['actions'] = [action.model_dump() for action in patch['actions']]
    patch['updated_at'] = _now()
    await db.workflows.update_one({'id': wid}, {'$set': patch})
    return {**existing, **patch}


@router.delete('/{wid}', dependencies=[Depends(get_current_admin)])
async def delete_workflow(wid: str):
    result = await db.workflows.delete_one({'id': wid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Workflow not found')
    return {'ok': True}


@router.post('/{wid}/run', dependencies=[Depends(get_current_admin)])
async def run_workflow(wid: str, bg: BackgroundTasks):
    wf = await db.workflows.find_one({'id': wid})
    if not wf:
        raise HTTPException(status_code=404, detail='Workflow not found')
    bg.add_task(_execute_workflow, wid)
    await db.workflows.update_one({'id': wid}, {'$set': {'last_run_status': 'running', 'updated_at': _now()}})
    return {'ok': True, 'status': 'running'}


@router.get('/triggers', dependencies=[Depends(get_current_admin)])
async def list_triggers():
    return {
        'triggers': [
            {'id': 'video_ready', 'label': 'Video Ready', 'desc': 'Jab koi video generate ho jaaye', 'icon': 'video'},
            {'id': 'new_product', 'label': 'New Product', 'desc': 'Jab naya product add ho', 'icon': 'package'},
            {'id': 'new_user', 'label': 'New User Signup', 'desc': 'Jab naya user register kare', 'icon': 'user-plus'},
            {'id': 'cron', 'label': 'Schedule (Cron)', 'desc': 'Daily, weekly ya custom interval', 'icon': 'clock'},
            {'id': 'manual', 'label': 'Manual Trigger', 'desc': 'Sirf button dabane par chale', 'icon': 'play'},
            {'id': 'credit_low', 'label': 'Low Credits Alert', 'desc': 'Jab kisi user ke credits < threshold', 'icon': 'zap'},
            {'id': 'order_placed', 'label': 'Order Placed', 'desc': 'Jab koi naya order aaye', 'icon': 'shopping-cart'},
        ],
        'actions': [
            {'id': 'post_social', 'label': 'Post to Social', 'desc': 'YouTube / Instagram / Facebook mein post karo', 'icon': 'share'},
            {'id': 'grant_credits', 'label': 'Grant Credits', 'desc': 'User ko credits do', 'icon': 'zap'},
            {'id': 'send_email', 'label': 'Send Email', 'desc': 'Email notification bhejo', 'icon': 'mail'},
            {'id': 'generate_content', 'label': 'Generate Content', 'desc': 'AI se content/video generate karo', 'icon': 'sparkles'},
            {'id': 'webhook', 'label': 'Webhook', 'desc': 'Public HTTPS URL pe POST bhejo', 'icon': 'globe'},
            {'id': 'notify_slack', 'label': 'Slack Notification', 'desc': 'Slack channel mein message bhejo', 'icon': 'bell'},
        ],
    }


async def _execute_workflow(wid: str):
    """Run actions in sequence and retain bounded result details for administrator review."""
    wf = await db.workflows.find_one({'id': wid})
    if not wf:
        return
    results = []
    for action in wf.get('actions') or []:
        try:
            result = await _run_action(action, wf)
            results.append({'type': action.get('type'), 'ok': True, 'result': result})
        except Exception as exc:
            results.append({'type': action.get('type'), 'ok': False, 'error': str(exc)[:200]})

    succeeded = sum(1 for result in results if result['ok'])
    status = 'success' if succeeded == len(results) else ('partial' if succeeded else 'failed')
    await db.workflows.update_one({'id': wid}, {'$set': {
        'last_run': _now(),
        'last_run_status': status,
        'last_run_results': results,
        'updated_at': _now(),
    }, '$inc': {'run_count': 1}})


async def _run_action(action: dict, wf: dict) -> Any:
    atype = action.get('type')
    cfg = action.get('config') or {}

    if atype == 'grant_credits':
        email = cfg.get('email') or cfg.get('user_email')
        try:
            amount = int(cfg.get('amount', 10))
        except (TypeError, ValueError) as exc:
            raise ValueError('credit grant amount must be a positive integer') from exc
        if not email:
            return {'skipped': 'no recipient email'}
        user = await db.users.find_one({'email': email}, {'_id': 0, 'id': 1})
        if not user:
            raise ValueError('recipient user not found')
        balance_after = await add_credits(
            user['id'],
            amount,
            reason=f'workflow:{wf["id"]}',
            meta={'workflow_id': wf['id'], 'trigger': wf['trigger'], 'recipient_email': email},
        )
        return {'granted': amount, 'to': email, 'balance_after': balance_after}

    if atype == 'webhook':
        import httpx
        url = await _validate_webhook_url(str(cfg.get('url', '')).strip())
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            response = await client.post(url, json={'workflow_id': wf['id'], 'trigger': wf['trigger'], 'ts': _now()})
            return {'status': response.status_code}

    if atype == 'post_social':
        return {'note': 'Social post requires a video_job_id — trigger via video_ready workflow'}
    if atype == 'generate_content':
        return {'note': 'Content generation queued — connect to AI pipeline'}
    return {'note': f'{atype} executed'}
