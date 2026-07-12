"""Queue + backup routes."""
from fastapi import APIRouter, Depends
from auth import get_current_admin
from queue_worker import enqueue, process_next, get_queue_stats

router = APIRouter(prefix='/admin/queue', tags=['queue'])


@router.get('/stats')
async def queue_stats(_=Depends(get_current_admin)):
    return await get_queue_stats()


@router.post('/backup')
async def trigger_backup(_=Depends(get_current_admin)):
    task_id = await enqueue('backup_mongodb', {})
    return {'status': 'queued', 'task_id': task_id}


@router.post('/process')
async def process_queue(_=Depends(get_current_admin)):
    result = await process_next()
    return {'result': result or {'status': 'no_tasks'}}
