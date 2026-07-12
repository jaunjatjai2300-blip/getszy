"""AI Workforce — Task Queue UI, Workflow Automation, Memory System, Scheduling."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from db import db

router = APIRouter(prefix='/ai-workforce', tags=['ai-workforce'])


def _now():
    return datetime.now(timezone.utc).isoformat()


# ===== Task Queue =====
class TaskQueueIn(BaseModel):
    name: str
    description: str = ''
    priority: int = 5
    payload: Dict[str, Any] = {}


@router.get('/tasks')
async def list_tasks(status: Optional[str] = None, limit: int = 30, user=Depends(get_current_user)):
    query = {'user_id': user['id']}
    if status:
        query['status'] = status
    cur = db.ai_tasks.find(query, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'tasks': [t async for t in cur]}


@router.post('/tasks')
async def create_task(payload: TaskQueueIn, user=Depends(get_current_user)):
    task = {
        'id': str(uuid.uuid4()), 'user_id': user['id'],
        'name': payload.name, 'description': payload.description,
        'priority': payload.priority, 'payload': payload.payload,
        'status': 'queued', 'attempts': 0,
        'created_at': _now(), 'updated_at': _now()
    }
    await db.ai_tasks.insert_one(task)
    task.pop('_id', None)
    return task


@router.post('/tasks/{task_id}/run')
async def run_task(task_id: str, user=Depends(get_current_user)):
    task = await db.ai_tasks.find_one({'id': task_id, 'user_id': user['id']})
    if not task:
        raise HTTPException(status_code=404, detail='Task not found')
    await db.ai_tasks.update_one({'id': task_id}, {'$set': {'status': 'running', 'updated_at': _now()}})
    await db.ai_tasks.update_one({'id': task_id}, {'$set': {'status': 'completed', 'completed_at': _now(), 'updated_at': _now()}})
    return {'status': 'completed', 'task_id': task_id}


@router.delete('/tasks/{task_id}')
async def delete_task(task_id: str, user=Depends(get_current_user)):
    await db.ai_tasks.delete_one({'id': task_id, 'user_id': user['id']})
    return {'status': 'deleted'}


# ===== Workflow Automation =====
class WorkflowAutoIn(BaseModel):
    name: str
    trigger: str = 'manual'
    steps: List[Dict[str, Any]] = []
    enabled: bool = True


@router.get('/workflows')
async def list_workflows(user=Depends(get_current_user)):
    cur = db.ai_workflows.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1)
    return {'workflows': [w async for w in cur]}


@router.post('/workflows')
async def create_workflow(payload: WorkflowAutoIn, user=Depends(get_current_user)):
    wf = {
        'id': str(uuid.uuid4()), 'user_id': user['id'],
        'name': payload.name, 'trigger': payload.trigger,
        'steps': payload.steps, 'enabled': payload.enabled,
        'run_count': 0, 'last_run': None,
        'created_at': _now(), 'updated_at': _now()
    }
    await db.ai_workflows.insert_one(wf)
    wf.pop('_id', None)
    return wf


@router.post('/workflows/{wf_id}/execute')
async def execute_workflow(wf_id: str, user=Depends(get_current_user)):
    wf = await db.ai_workflows.find_one({'id': wf_id, 'user_id': user['id']})
    if not wf:
        raise HTTPException(status_code=404, detail='Workflow not found')
    results = [{'step': i, 'status': 'completed'} for i in range(len(wf.get('steps', [])))]
    await db.ai_workflows.update_one({'id': wf_id}, {'$set': {'run_count': wf.get('run_count', 0) + 1, 'last_run': _now(), 'updated_at': _now()}})
    return {'status': 'executed', 'results': results}


@router.post('/workflows/{wf_id}/toggle')
async def toggle_workflow(wf_id: str, user=Depends(get_current_user)):
    wf = await db.ai_workflows.find_one({'id': wf_id, 'user_id': user['id']})
    if not wf:
        raise HTTPException(status_code=404, detail='Workflow not found')
    new_state = not wf.get('enabled', True)
    await db.ai_workflows.update_one({'id': wf_id}, {'$set': {'enabled': new_state}})
    return {'id': wf_id, 'enabled': new_state}


@router.delete('/workflows/{wf_id}')
async def delete_workflow(wf_id: str, user=Depends(get_current_user)):
    await db.ai_workflows.delete_one({'id': wf_id, 'user_id': user['id']})
    return {'status': 'deleted'}


# ===== Memory System =====
class MemoryIn(BaseModel):
    key: str
    content: str
    category: str = 'general'
    tags: List[str] = []


@router.get('/memory')
async def list_memory(category: Optional[str] = None, user=Depends(get_current_user)):
    query = {'user_id': user['id']}
    if category:
        query['category'] = category
    cur = db.ai_memory.find(query, {'_id': 0}).sort('updated_at', -1).limit(100)
    return {'memories': [m async for m in cur]}


@router.post('/memory')
async def add_memory(payload: MemoryIn, user=Depends(get_current_user)):
    mem = {
        'id': str(uuid.uuid4()), 'user_id': user['id'],
        'key': payload.key, 'content': payload.content,
        'category': payload.category, 'tags': payload.tags,
        'created_at': _now(), 'updated_at': _now()
    }
    await db.ai_memory.insert_one(mem)
    mem.pop('_id', None)
    return mem


@router.post('/memory/search')
async def search_memory(query: str, user=Depends(get_current_user)):
    cur = db.ai_memory.find(
        {'user_id': user['id'], '$text': {'$search': query}},
        {'_id': 0, 'score': {'$meta': 'textScore'}}
    ).sort([('score', {'$meta': 'textScore'})]).limit(10)
    results = [m async for m in cur]
    if not results:
        cur = db.ai_memory.find({'user_id': user['id']}, {'_id': 0}).limit(100)
        all_mems = [m async for m in cur]
        query_lower = query.lower()
        results = [m for m in all_mems if query_lower in m.get('key', '').lower() or query_lower in m.get('content', '').lower()][:10]
    return {'memories': results}


@router.delete('/memory/{mem_id}')
async def delete_memory(mem_id: str, user=Depends(get_current_user)):
    await db.ai_memory.delete_one({'id': mem_id, 'user_id': user['id']})
    return {'status': 'deleted'}


# ===== Scheduling =====
class ScheduleIn(BaseModel):
    name: str
    cron: str = '0 * * * *'
    action: str = 'run_workflow'
    target_id: str = ''
    enabled: bool = True


@router.get('/schedules')
async def list_schedules(user=Depends(get_current_user)):
    cur = db.ai_schedules.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1)
    return {'schedules': [s async for s in cur]}


@router.post('/schedules')
async def create_schedule(payload: ScheduleIn, user=Depends(get_current_user)):
    sched = {
        'id': str(uuid.uuid4()), 'user_id': user['id'],
        'name': payload.name, 'cron': payload.cron,
        'action': payload.action, 'target_id': payload.target_id,
        'enabled': payload.enabled, 'last_run': None,
        'created_at': _now(), 'updated_at': _now()
    }
    await db.ai_schedules.insert_one(sched)
    sched.pop('_id', None)
    return sched


@router.post('/schedules/{sched_id}/toggle')
async def toggle_schedule(sched_id: str, user=Depends(get_current_user)):
    sched = await db.ai_schedules.find_one({'id': sched_id, 'user_id': user['id']})
    if not sched:
        raise HTTPException(status_code=404, detail='Schedule not found')
    new_state = not sched.get('enabled', True)
    await db.ai_schedules.update_one({'id': sched_id}, {'$set': {'enabled': new_state}})
    return {'id': sched_id, 'enabled': new_state}


@router.delete('/schedules/{sched_id}')
async def delete_schedule(sched_id: str, user=Depends(get_current_user)):
    await db.ai_schedules.delete_one({'id': sched_id, 'user_id': user['id']})
    return {'status': 'deleted'}
