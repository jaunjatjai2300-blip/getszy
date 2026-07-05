"""Faceless Video Studio - REST routes."""
import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel

from auth import get_current_user
from db import db
from video.pipeline import run_job
from video.compose import VIDEO_DIR
from video.tts import LIST_VOICES
from credits import deduct, refund

router = APIRouter(prefix='/video', tags=['video'])


class GenerateIn(BaseModel):
    topic: str
    orientation: str = '9:16'        # 9:16 / 16:9 / 1:1
    language: str = 'hinglish'
    voice_gender: str = 'female'
    target_seconds: int = 45
    tone: str = 'energetic'
    subtitles: bool = True
    audience: str = 'indian creators'


class BatchIn(BaseModel):
    topics: List[str]
    orientation: str = '9:16'
    language: str = 'hinglish'
    voice_gender: str = 'female'
    target_seconds: int = 45


@router.get('/voices')
async def voices(_=Depends(get_current_user)):
    return {'voices': LIST_VOICES,
            'providers': {'tts': 'edge-tts (free)',
                          'visuals': 'pollinations (free)',
                          'compose': 'ffmpeg'}}


@router.post('/generate')
async def generate(payload: GenerateIn, bg: BackgroundTasks, user=Depends(get_current_user)):
    if len(payload.topic.strip()) < 4:
        raise HTTPException(status_code=400, detail='Topic too short')
    ok, msg, _ = await deduct(user['id'], 'faceless_video')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    job_id = str(uuid.uuid4())
    await db.video_jobs.insert_one({
        'id': job_id, 'user_id': user['id'], 'topic': payload.topic,
        'orientation': payload.orientation, 'language': payload.language,
        'status': 'queued', 'percent': 0, 'params': payload.model_dump(),
        'created_at': datetime.now(timezone.utc).isoformat(),
    })
    bg.add_task(run_job, job_id, payload.model_dump(), user['id'], 1)
    return {'id': job_id, 'status': 'queued'}


@router.post('/batch')
async def batch(payload: BatchIn, bg: BackgroundTasks, user=Depends(get_current_user)):
    if not payload.topics:
        raise HTTPException(status_code=400, detail='topics required')
    if len(payload.topics) > 10:
        raise HTTPException(status_code=400, detail='max 10 topics per batch')
    ok, msg, _ = await deduct(user['id'], 'faceless_video', qty=len(payload.topics))
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    ids = []
    base = payload.model_dump()
    base.pop('topics')
    for t in payload.topics:
        job_id = str(uuid.uuid4())
        params = {**base, 'topic': t}
        await db.video_jobs.insert_one({
            'id': job_id, 'user_id': user['id'], 'topic': t,
            'orientation': payload.orientation, 'language': payload.language,
            'status': 'queued', 'percent': 0, 'params': params,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'batch_id': str(uuid.uuid4())[:8] if not ids else ids[0]['batch_id'],
        })
        bg.add_task(run_job, job_id, params, user['id'], 1)
        ids.append({'id': job_id, 'topic': t, 'batch_id': 'b'})
    return {'jobs': ids, 'count': len(ids)}


@router.get('/jobs')
async def jobs(limit: int = 30, user=Depends(get_current_user)):
    cur = db.video_jobs.find({'user_id': user['id']}, {'_id': 0, 'script': 0, 'scenes': 0}).sort('created_at', -1).limit(limit)
    return {'items': [doc async for doc in cur]}


@router.get('/jobs/{job_id}')
async def job_detail(job_id: str, user=Depends(get_current_user)):
    doc = await db.video_jobs.find_one({'id': job_id, 'user_id': user['id']}, {'_id': 0})
    if not doc:
        raise HTTPException(status_code=404, detail='not found')
    return doc


@router.delete('/jobs/{job_id}')
async def delete_job(job_id: str, user=Depends(get_current_user)):
    doc = await db.video_jobs.find_one({'id': job_id, 'user_id': user['id']})
    if not doc:
        raise HTTPException(status_code=404, detail='not found')
    await db.video_jobs.delete_one({'id': job_id})
    for ext in ('mp4', 'mp3', 'srt'):
        p = os.path.join(VIDEO_DIR, f'{job_id}.{ext}')
        try:
            if os.path.exists(p): os.remove(p)
        except Exception: pass
    return {'ok': True}


@router.get('/files/{filename}')
async def serve_file(filename: str):
    # No auth on file serve so user can embed in <video src=...>; URL contains UUID which is unguessable.
    safe = os.path.basename(filename)
    path = os.path.join(VIDEO_DIR, safe)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail='file not found')
    media_type = {'mp4': 'video/mp4', 'mp3': 'audio/mpeg', 'srt': 'text/plain'}.get(safe.split('.')[-1].lower(), 'application/octet-stream')
    return FileResponse(path, media_type=media_type, filename=safe)
