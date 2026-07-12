"""Audit log routes."""
from typing import Optional
from fastapi import APIRouter, Depends
from auth import get_current_admin
from audit_log import get_logs, get_stats

router = APIRouter(prefix='/admin/audit', tags=['audit'])


@router.get('/logs')
async def logs(user_id: Optional[str] = None, action: Optional[str] = None, limit: int = 50, _=Depends(get_current_admin)):
    result = await get_logs(user_id=user_id or '', action=action or '', limit=limit)
    return {'logs': result}


@router.get('/stats')
async def stats(_=Depends(get_current_admin)):
    return await get_stats()
