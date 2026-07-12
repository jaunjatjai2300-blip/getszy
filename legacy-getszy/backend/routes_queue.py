"""Queue and backup routes."""
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_admin
from queue_worker import enqueue_task, get_queue_stats, trigger_backup, get_backups
from audit_log import log_action

router = APIRouter(prefix='/admin/queue', tags=['queue'])


@router.get('/stats', dependencies=[Depends(get_current_admin)])
async def queue_stats():
    return await get_queue_stats()


@router.post('/enqueue', dependencies=[Depends(get_current_admin)])
async def enqueue(queue_name: str, task_data: dict):
    task_id = await enqueue_task(queue_name, task_data)
    return {'task_id': task_id, 'queue': queue_name}


@router.post('/backup', dependencies=[Depends(get_current_admin)])
async def backup():
    task_id = await trigger_backup()
    await log_action('backup.triggered', details={'task_id': task_id})
    return {'task_id': task_id, 'status': 'queued'}


@router.get('/backups', dependencies=[Depends(get_current_admin)])
async def list_backups():
    return await get_backups()
