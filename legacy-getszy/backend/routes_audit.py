"""Audit log routes — security and compliance."""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from auth import get_current_admin
from audit_log import get_audit_logs, get_audit_stats

router = APIRouter(prefix='/admin/audit', tags=['audit'])


@router.get('/logs', dependencies=[Depends(get_current_admin)])
async def list_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await get_audit_logs(user_id, action, resource_type, limit, offset)


@router.get('/stats', dependencies=[Depends(get_current_admin)])
async def stats(days: int = Query(30, ge=1, le=365)):
    return await get_audit_stats(days)
