"""YAML Campaign Stacks routes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timezone

from auth import get_current_admin
from db import db
from stacks.executor import parse, execute

router = APIRouter(prefix='/admin/stacks', tags=['stacks'])


class StackIn(BaseModel):
    yaml: str
    save: bool = True


class StackUpdate(BaseModel):
    yaml: str


@router.get('')
async def list_stacks(_=Depends(get_current_admin)):
    cur = db.campaign_stacks.find({}, {'_id': 0}).sort('updated_at', -1)
    return {'items': [doc async for doc in cur]}


@router.post('/parse')
async def parse_stack(payload: StackIn, _=Depends(get_current_admin)):
    try:
        data = parse(payload.yaml)
        return {'ok': True, 'parsed': data, 'step_count': len(data.get('steps', []) or [])}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/save')
async def save_stack(payload: StackIn, admin=Depends(get_current_admin)):
    try:
        data = parse(payload.yaml)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    sid = str(uuid.uuid4())
    doc = {
        'id': sid,
        'name': data['name'],
        'yaml': payload.yaml,
        'parsed': data,
        'admin_id': admin['id'],
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.campaign_stacks.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.put('/{stack_id}')
async def update_stack(stack_id: str, payload: StackUpdate, _=Depends(get_current_admin)):
    try:
        data = parse(payload.yaml)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    update = {'yaml': payload.yaml, 'parsed': data, 'name': data['name'], 'updated_at': datetime.now(timezone.utc).isoformat()}
    r = await db.campaign_stacks.update_one({'id': stack_id}, {'$set': update})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail='Stack not found')
    return {'ok': True}


@router.delete('/{stack_id}')
async def delete_stack(stack_id: str, _=Depends(get_current_admin)):
    r = await db.campaign_stacks.delete_one({'id': stack_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Stack not found')
    return {'ok': True}


@router.post('/{stack_id}/run')
async def run_stack(stack_id: str, admin=Depends(get_current_admin)):
    doc = await db.campaign_stacks.find_one({'id': stack_id}, {'_id': 0})
    if not doc:
        raise HTTPException(status_code=404, detail='Stack not found')
    result = await execute(doc['parsed'], admin)
    record = {**result, 'stack_id': stack_id, 'admin_id': admin['id']}
    await db.stack_runs.insert_one(record)
    record.pop('_id', None)
    return record


@router.post('/run-once')
async def run_once(payload: StackIn, admin=Depends(get_current_admin)):
    """Parse + execute without saving — for quick experiments."""
    try:
        data = parse(payload.yaml)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return await execute(data, admin)


@router.get('/runs/recent')
async def recent_runs(limit: int = 20, _=Depends(get_current_admin)):
    cur = db.stack_runs.find({}, {'_id': 0}).sort('started_at', -1).limit(limit)
    return {'items': [doc async for doc in cur]}
