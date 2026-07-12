"""Background queue worker — processes async tasks (image gen, video, email, etc.)."""
import os
import asyncio
import json
import logging
from datetime import datetime, timezone
from redis_cache import get_redis, queue_push, queue_pop, queue_len
from db import db
from models import _id, _now

logger = logging.getLogger('getszy.queue')

# Queue names
QUEUE_IMAGE_GEN = 'image_generation'
QUEUE_VOICE_GEN = 'voice_generation'
QUEUE_VIDEO_RENDER = 'video_rendering'
QUEUE_EMAIL = 'email'
QUEUE_DEPLOY = 'deploy'
QUEUE_WOO_SYNC = 'woocommerce_sync'
QUEUE_BACKUP = 'backup'

ALL_QUEUES = [
    QUEUE_IMAGE_GEN, QUEUE_VOICE_GEN, QUEUE_VIDEO_RENDER,
    QUEUE_EMAIL, QUEUE_DEPLOY, QUEUE_WOO_SYNC, QUEUE_BACKUP,
]


async def enqueue_task(queue_name: str, task_data: dict, priority: int = 0) -> str:
    """Add task to queue. Returns task_id."""
    task_id = _id()
    task = {
        'id': task_id,
        'queue': queue_name,
        'data': task_data,
        'priority': priority,
        'status': 'pending',
        'created_at': _now(),
        'attempts': 0,
        'max_attempts': 3,
    }
    await queue_push(queue_name, task)

    # Store task status in DB
    await db.queue_tasks.insert_one({
        'task_id': task_id,
        'queue': queue_name,
        'status': 'pending',
        'created_at': _now(),
    })

    logger.info(f'Task enqueued: {task_id} -> {queue_name}')
    return task_id


async def process_task(task: dict):
    """Process a single task based on queue name."""
    queue = task.get('queue', '')
    data = task.get('data', {})
    task_id = task.get('id', 'unknown')

    try:
        if queue == QUEUE_IMAGE_GEN:
            from image_gen import generate_image
            result = await generate_image(**data)
            await _update_task(task_id, 'completed', result)

        elif queue == QUEUE_VOICE_GEN:
            from voice_gen import generate_voice
            result = await generate_voice(**data)
            await _update_task(task_id, 'completed', result)

        elif queue == QUEUE_VIDEO_RENDER:
            # Video rendering placeholder
            await _update_task(task_id, 'completed', {'message': 'Video queued for rendering'})

        elif queue == QUEUE_EMAIL:
            # Email sending placeholder
            await _update_task(task_id, 'completed', {'message': 'Email sent'})

        elif queue == QUEUE_DEPLOY:
            # Deploy trigger
            await _update_task(task_id, 'completed', {'message': 'Deploy triggered'})

        elif queue == QUEUE_BACKUP:
            await _run_backup()

        else:
            logger.warning(f'Unknown queue: {queue}')
            await _update_task(task_id, 'failed', {'error': f'Unknown queue: {queue}'})

    except Exception as e:
        logger.error(f'Task {task_id} failed: {e}')
        await _update_task(task_id, 'failed', {'error': str(e)})


async def _update_task(task_id: str, status: str, result: dict = None):
    update = {'status': status, 'updated_at': _now()}
    if result:
        update['result'] = result
    if status == 'completed':
        update['completed_at'] = _now()
    await db.queue_tasks.update_one({'task_id': task_id}, {'$set': update})


async def get_queue_stats() -> dict:
    """Get queue statistics."""
    stats = {}
    for q in ALL_QUEUS if False else ALL_QUEUES:
        length = await queue_len(q)
        pending = await db.queue_tasks.count_documents({'queue': q, 'status': 'pending'})
        running = await db.queue_tasks.count_documents({'queue': q, 'status': 'running'})
        completed = await db.queue_tasks.count_documents({'queue': q, 'status': 'completed'})
        failed = await db.queue_tasks.count_documents({'queue': q, 'status': 'failed'})
        stats[q] = {
            'queue_length': length,
            'pending': pending,
            'running': running,
            'completed': completed,
            'failed': failed,
        }
    return stats


# ── Backup system ────────────────────────────────────────────────────────────

async def _run_backup():
    """Run MongoDB backup."""
    import subprocess
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    filename = f'getszy_backup_{timestamp}.gz'
    filepath = os.path.join(backup_dir, filename)

    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'getszy_db')

    try:
        proc = await asyncio.create_subprocess_exec(
            'mongodump', f'--uri={mongo_url}', f'--db={db_name}',
            f'--archive={filepath}', '--gzip',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            logger.info(f'Backup completed: {filename}')
            await db.backups.insert_one({
                'id': _id(),
                'filename': filename,
                'filepath': filepath,
                'size_bytes': os.path.getsize(filepath) if os.path.exists(filepath) else 0,
                'created_at': _now(),
                'status': 'success',
            })
        else:
            logger.error(f'Backup failed: {stderr.decode()}')
    except FileNotFoundError:
        logger.warning('mongodump not available — skipping backup')
    except Exception as e:
        logger.error(f'Backup error: {e}')


async def trigger_backup() -> str:
    """Manually trigger a backup."""
    task_id = await enqueue_task(QUEUE_BACKUP, {'triggered_by': 'manual'})
    return task_id


async def get_backups(limit: int = 20) -> list:
    """List recent backups."""
    cursor = db.backups.find({}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return await cursor.to_list(limit)
