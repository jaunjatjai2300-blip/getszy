"""Multi-platform publishing REST routes."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from db import db
from publishing.adapters import publish, connections, PLATFORMS
from publishing.metadata import build_metadata

router = APIRouter(prefix='/publishing', tags=['publishing'])


class ScheduleIn(BaseModel):
    platforms: List[str]
    topic: str
    video_job_id: Optional[str] = None
    media_url: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    scheduled_at: Optional[str] = None  # ISO
    auto_generate_meta: bool = True


class RunNowIn(BaseModel):
    queue_id: str


@router.get('/connections')
async def get_connections(_=Depends(get_current_user)):
    return {'platforms': connections(), 'supported': PLATFORMS}


@router.post('/schedule')
async def schedule(payload: ScheduleIn, user=Depends(get_current_user)):
    if not payload.platforms:
        raise HTTPException(status_code=400, detail='Pick at least one platform')
    for p in payload.platforms:
        if p not in PLATFORMS:
            raise HTTPException(status_code=400, detail=f'unknown platform: {p}')

    # Resolve script if a video job is referenced
    script = {}
    media_url = payload.media_url
    if payload.video_job_id:
        vj = await db.video_jobs.find_one({'id': payload.video_job_id, 'user_id': user['id']}, {'_id': 0})
        if vj:
            script = vj.get('script') or {}
            media_url = media_url or vj.get('video_url')

    queue_id = str(uuid.uuid4())
    items = []
    for platform in payload.platforms:
        meta = {}
        if payload.auto_generate_meta:
            try:
                meta = await build_metadata(platform, payload.topic, script or {'hook': payload.caption or payload.topic, 'cta': ''})
            except Exception as e:
                meta = {'title': payload.topic, 'caption': payload.caption or '', 'hashtags': payload.hashtags or []}
        item = {
            'id': str(uuid.uuid4()), 'queue_id': queue_id, 'user_id': user['id'],
            'platform': platform, 'topic': payload.topic,
            'video_job_id': payload.video_job_id, 'media_url': media_url,
            'title': meta.get('title', payload.topic),
            'caption': meta.get('caption') or payload.caption or '',
            'hashtags': meta.get('hashtags') or payload.hashtags or [],
            'call_to_action': meta.get('call_to_action', ''),
            'scheduled_at': payload.scheduled_at,
            'status': 'scheduled' if payload.scheduled_at else 'ready',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.publish_queue.insert_one(item)
        item.pop('_id', None)
        items.append(item)
    return {'queue_id': queue_id, 'items': items}


@router.get('/queue')
async def get_queue(limit: int = 50, user=Depends(get_current_user)):
    cur = db.publish_queue.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'items': [doc async for doc in cur]}


@router.post('/run-now')
async def run_now(payload: RunNowIn, user=Depends(get_current_user)):
    item = await db.publish_queue.find_one({'id': payload.queue_id, 'user_id': user['id']}, {'_id': 0})
    if not item:
        raise HTTPException(status_code=404, detail='not found')
    result = await publish(item['platform'], {
        'caption': item.get('caption', ''),
        'title': item.get('title', ''),
        'hashtags': item.get('hashtags', []),
        'media_url': item.get('media_url'),
        'scheduled_at': item.get('scheduled_at'),
    })
    await db.publish_queue.update_one({'id': payload.queue_id}, {'$set': {
        'status': result.get('status'), 'result': result,
        'posted_at': datetime.now(timezone.utc).isoformat(),
    }})
    return result


@router.delete('/queue/{item_id}')
async def cancel(item_id: str, user=Depends(get_current_user)):
    r = await db.publish_queue.delete_one({'id': item_id, 'user_id': user['id']})
    return {'deleted': r.deleted_count}
