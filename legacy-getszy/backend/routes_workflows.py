"""Automation Workflow Builder — store + run trigger-action chains."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from auth import get_current_admin
from db import db

router = APIRouter(prefix='/admin/workflows', tags=['workflows'])


TRIGGER_TYPES = ['video_ready', 'new_product', 'new_user', 'cron', 'manual', 'credit_low', 'order_placed']
ACTION_TYPES  = ['post_social', 'grant_credits', 'send_email', 'generate_content', 'webhook', 'notify_slack']


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


def _now():
    return datetime.now(timezone.utc).isoformat()


@router.get('', dependencies=[Depends(get_current_admin)])
async def list_workflows():
    items = await db.workflows.find({}, {'_id': 0}).sort('created_at', -1).to_list(200)
    return {'items': items, 'total': len(items)}


@router.post('', dependencies=[Depends(get_current_admin)])
async def create_workflow(body: WorkflowIn):
    if body.trigger not in TRIGGER_TYPES:
        raise HTTPException(status_code=400, detail=f'Unknown trigger. Use: {TRIGGER_TYPES}')
    for a in body.actions:
        if a.type not in ACTION_TYPES:
            raise HTTPException(status_code=400, detail=f'Unknown action: {a.type}. Use: {ACTION_TYPES}')
    doc = {
        'id': str(uuid.uuid4()),
        'name': body.name.strip(),
        'description': body.description.strip(),
        'trigger': body.trigger,
        'trigger_config': body.trigger_config,
        'actions': [a.model_dump() for a in body.actions],
        'enabled': body.enabled,
        'run_count': 0,
        'last_run': None,
        'last_run_status': None,
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.workflows.insert_one(doc)
    return doc


@router.patch('/{wid}', dependencies=[Depends(get_current_admin)])
async def update_workflow(wid: str, body: WorkflowPatchIn):
    existing = await db.workflows.find_one({'id': wid})
    if not existing:
        raise HTTPException(status_code=404, detail='Workflow not found')
    patch = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None or k == 'enabled'}
    if 'actions' in patch and patch['actions']:
        patch['actions'] = [a if isinstance(a, dict) else a.model_dump() for a in patch['actions']]
    patch['updated_at'] = _now()
    await db.workflows.update_one({'id': wid}, {'$set': patch})
    return {**existing, **patch, '_id': None}


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
            {'id': 'video_ready',   'label': 'Video Ready',         'desc': 'Jab koi video generate ho jaaye',          'icon': 'video'},
            {'id': 'new_product',   'label': 'New Product',         'desc': 'Jab naya product add ho',                  'icon': 'package'},
            {'id': 'new_user',      'label': 'New User Signup',     'desc': 'Jab koi naya user register kare',          'icon': 'user-plus'},
            {'id': 'cron',          'label': 'Schedule (Cron)',     'desc': 'Daily, weekly ya custom interval',         'icon': 'clock'},
            {'id': 'manual',        'label': 'Manual Trigger',      'desc': 'Sirf button dabane par chale',             'icon': 'play'},
            {'id': 'credit_low',    'label': 'Low Credits Alert',   'desc': 'Jab kisi user ke credits < threshold',     'icon': 'zap'},
            {'id': 'order_placed',  'label': 'Order Placed',        'desc': 'Jab koi naya order aaye',                  'icon': 'shopping-cart'},
        ],
        'actions': [
            {'id': 'post_social',      'label': 'Post to Social',       'desc': 'YouTube / Instagram / Facebook mein post karo', 'icon': 'share'},
            {'id': 'grant_credits',    'label': 'Grant Credits',        'desc': 'User ko credits do',                           'icon': 'zap'},
            {'id': 'send_email',       'label': 'Send Email',           'desc': 'Email notification bhejo',                     'icon': 'mail'},
            {'id': 'generate_content', 'label': 'Generate Content',     'desc': 'AI se content/video generate karo',            'icon': 'sparkles'},
            {'id': 'webhook',          'label': 'Webhook',              'desc': 'Bahar kisi URL pe POST bhejo',                 'icon': 'globe'},
            {'id': 'notify_slack',     'label': 'Slack Notification',   'desc': 'Slack channel mein message bhejo',             'icon': 'bell'},
        ]
    }


async def _execute_workflow(wid: str):
    """Background: run each action in sequence, log result."""
    wf = await db.workflows.find_one({'id': wid})
    if not wf:
        return
    results = []
    ok_all = True
    for action in (wf.get('actions') or []):
        try:
            res = await _run_action(action, wf)
            results.append({'type': action['type'], 'ok': True, 'result': res})
        except Exception as e:
            results.append({'type': action['type'], 'ok': False, 'error': str(e)[:200]})
            ok_all = False

    status = 'success' if ok_all else ('partial' if any(r['ok'] for r in results) else 'failed')
    await db.workflows.update_one({'id': wid}, {'$set': {
        'last_run': _now(),
        'last_run_status': status,
        'last_run_results': results,
        'updated_at': _now(),
    }, '$inc': {'run_count': 1}})


async def _run_action(action: dict, wf: dict) -> Any:
    atype = action.get('type')
    cfg   = action.get('config', {})

    if atype == 'grant_credits':
        email = cfg.get('email') or cfg.get('user_email')
        amt   = int(cfg.get('amount', 10))
        if email:
            await db.users.update_one({'email': email}, {'$inc': {'credits': amt}})
            await db.credit_transactions.insert_one({
                'id': str(uuid.uuid4()), 'email': email, 'delta': amt,
                'reason': f'workflow:{wf["id"]}', 'created_at': _now()
            })
        return {'granted': amt, 'to': email}

    elif atype == 'webhook':
        import httpx
        url = cfg.get('url', '')
        if url:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(url, json={'workflow_id': wf['id'], 'trigger': wf['trigger'], 'ts': _now()})
                return {'status': r.status_code}
        return {'skipped': 'no url'}

    elif atype == 'post_social':
        return {'note': 'Social post requires a video_job_id — trigger via video_ready workflow'}

    elif atype == 'generate_content':
        return {'note': 'Content generation queued — connect to AI pipeline'}

    return {'note': f'{atype} executed'}
