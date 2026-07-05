"""AI Workforce REST."""
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from db import db
from workforce.agents import list_agents, run_agent

router = APIRouter(prefix='/workforce', tags=['workforce'])


class TaskIn(BaseModel):
    params: Dict[str, Any] = {}


@router.get('/agents')
async def agents(_=Depends(get_current_user)):
    return {'agents': list_agents()}


@router.post('/{agent_id}/task')
async def task(agent_id: str, payload: TaskIn, user=Depends(get_current_user)):
    try:
        out = await run_agent(agent_id, payload.params or {})
    except KeyError:
        raise HTTPException(status_code=404, detail=f'unknown agent: {agent_id}')
    rec = {'id': str(uuid.uuid4()), 'user_id': user['id'], 'agent_id': agent_id,
           'params': payload.params, 'output': out,
           'created_at': datetime.now(timezone.utc).isoformat()}
    await db.workforce_runs.insert_one(rec)
    rec.pop('_id', None)
    return rec


@router.get('/history')
async def history(limit: int = 30, user=Depends(get_current_user)):
    cur = db.workforce_runs.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'items': [doc async for doc in cur]}
