"""Skills Marketplace routes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
from datetime import datetime, timezone

from auth import get_current_admin
from db import db
from skills.registry import registry
import skills.builtins  # noqa: F401  - triggers @register side-effects

router = APIRouter(prefix='/admin/skills', tags=['skills'])


class SkillRunIn(BaseModel):
    params: Dict[str, Any] = {}


@router.get('')
async def list_skills(_=Depends(get_current_admin)):
    grouped = registry.by_category()
    out = {}
    for cat, items in grouped.items():
        out[cat] = [s.to_dict() for s in items]
    return {'count': sum(len(v) for v in out.values()), 'by_category': out, 'flat': [s.to_dict() for s in registry.all()]}


@router.get('/{name}')
async def get_skill(name: str, _=Depends(get_current_admin)):
    s = registry.get(name)
    if not s:
        raise HTTPException(status_code=404, detail='Skill not found')
    return s.to_dict()


@router.post('/{name}/run')
async def run_skill(name: str, payload: SkillRunIn, admin=Depends(get_current_admin)):
    s = registry.get(name)
    if not s:
        raise HTTPException(status_code=404, detail='Skill not found')
    run_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc).isoformat()
    try:
        result = await s.run(payload.params or {}, {'user_id': admin['id']})
        status = 'ok'
        err = None
    except Exception as e:
        result = None
        status = 'error'
        err = str(e)
    ended = datetime.now(timezone.utc).isoformat()
    record = {'id': run_id, 'skill': name, 'params': payload.params, 'status': status, 'error': err, 'result': result, 'admin_id': admin['id'], 'started_at': started, 'ended_at': ended}
    await db.skill_runs.insert_one(record)
    record.pop('_id', None)
    return record


@router.get('/runs/recent')
async def recent_runs(limit: int = 20, _=Depends(get_current_admin)):
    cur = db.skill_runs.find({}, {'_id': 0}).sort('started_at', -1).limit(limit)
    return {'items': [doc async for doc in cur]}
