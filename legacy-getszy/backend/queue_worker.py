"""Background queue worker + backup scheduler."""
import uuid
import os
import asyncio
import logging
from datetime import datetime, timezone
from db import db

logger = logging.getLogger('getszy.queue')


async def enqueue(task_type: str, payload: dict, user_id: str = ''):
    task = {
        'id': str(uuid.uuid4()), 'type': task_type,
        'payload': payload, 'user_id': user_id,
        'status': 'queued', 'attempts': 0,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    await db.queue_tasks.insert_one(task)
    return task['id']


async def process_next():
    task = await db.queue_tasks.find_one_and_update(
        {'status': 'queued'},
        {'$set': {'status': 'running'}, '$inc': {'attempts': 1}},
        return_document=True
    )
    if not task:
        return None
    try:
        result = await _execute(task)
        await db.queue_tasks.update_one(
            {'id': task['id']},
            {'$set': {'status': 'completed', 'result': result, 'completed_at': datetime.now(timezone.utc).isoformat()}}
        )
        return result
    except Exception as e:
        await db.queue_tasks.update_one(
            {'id': task['id']},
            {'$set': {'status': 'failed', 'error': str(e)}}
        )
        return None


async def _execute(task: dict):
    t = task.get('type', '')
    p = task.get('payload', {})
    if t == 'backup_mongodb':
        return await _backup_mongodb(p)
    return {'status': 'unknown_task_type', 'type': t}


async def _backup_mongodb(params: dict):
    backup_dir = params.get('dir', '/opt/getszy/backups')
    os.makedirs(backup_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    path = f"{backup_dir}/getszy_{ts}"
    try:
        proc = await asyncio.create_subprocess_exec(
            'mongodump', '--uri', os.environ.get('MONGO_URL', 'mongodb://localhost:27017'), '--out', path,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
        try:
            _, err = await asyncio.wait_for(proc.communicate(), timeout=300)
        except asyncio.TimeoutError:
            try: proc.kill()
            except Exception as e: logger.warning('mongodump kill failed: %s', e)
            return {'status': 'error', 'error': 'mongodump timed out after 300s'}
        if proc.returncode != 0:
            return {'status': 'error', 'error': f'mongodump exited {proc.returncode}: {(err or b"")[:300].decode("utf-8", "ignore")}'}
        return {'status': 'success', 'path': path}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


async def get_queue_stats():
    pipeline = [
        {'$group': {'_id': '$status', 'count': {'$sum': 1}}}
    ]
    stats = await db.queue_tasks.aggregate(pipeline).to_list(10)
    return {s['_id']: s['count'] for s in stats}
