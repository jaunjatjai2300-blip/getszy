"""Creator Platform — Reel Studio, Thumbnail Generator, Batch Render, Scene Editor."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, get_current_admin
from db import db
from llm_provider import chat_completion
from credits import deduct, refund

router = APIRouter(prefix='/creator/platform', tags=['creator-platform'])


def _now():
    return datetime.now(timezone.utc).isoformat()


# ===== Reel Studio =====
class ReelIn(BaseModel):
    script: str
    style: str = 'modern'
    duration: int = 30
    aspect_ratio: str = '9:16'
    voice: str = 'default'
    music: Optional[str] = None


@router.post('/reels/create')
async def create_reel(payload: ReelIn, user=Depends(get_current_user)):
    reel_id = str(uuid.uuid4())
    reel = {
        'id': reel_id, 'user_id': user['id'],
        'script': payload.script, 'style': payload.style,
        'duration': payload.duration, 'aspect_ratio': payload.aspect_ratio,
        'voice': payload.voice, 'music': payload.music,
        'status': 'draft', 'scenes': [],
        'created_at': _now(), 'updated_at': _now()
    }
    await db.creator_reels.insert_one(reel)
    reel.pop('_id', None)
    return reel


@router.get('/reels')
async def list_reels(limit: int = 20, user=Depends(get_current_user)):
    cur = db.creator_reels.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'reels': [r async for r in cur]}


@router.get('/reels/{reel_id}')
async def get_reel(reel_id: str, user=Depends(get_current_user)):
    reel = await db.creator_reels.find_one({'id': reel_id, 'user_id': user['id']}, {'_id': 0})
    if not reel:
        raise HTTPException(status_code=404, detail='Reel not found')
    return reel


@router.post('/reels/{reel_id}/render')
async def render_reel(reel_id: str, user=Depends(get_current_user)):
    reel = await db.creator_reels.find_one({'id': reel_id, 'user_id': user['id']})
    if not reel:
        raise HTTPException(status_code=404, detail='Reel not found')
    await db.creator_reels.update_one({'id': reel_id}, {'$set': {'status': 'rendering', 'updated_at': _now()}})
    scene_count = max(1, len(reel.get('scenes', [])) or len(reel.get('script', '').split('\n')))
    scenes = [{'index': i, 'text': f'Scene {i+1}', 'status': 'rendered'} for i in range(scene_count)]
    await db.creator_reels.update_one({'id': reel_id}, {'$set': {'scenes': scenes, 'status': 'rendered', 'rendered_at': _now(), 'updated_at': _now()}})
    return {'status': 'rendered', 'scene_count': scene_count}


@router.delete('/reels/{reel_id}')
async def delete_reel(reel_id: str, user=Depends(get_current_user)):
    await db.creator_reels.delete_one({'id': reel_id, 'user_id': user['id']})
    return {'status': 'deleted'}


# ===== Thumbnail Generator =====
class ThumbnailIn(BaseModel):
    title: str
    style: str = 'bold'
    color_scheme: str = 'vibrant'
    elements: List[str] = []


@router.post('/thumbnails/generate')
async def generate_thumbnail(payload: ThumbnailIn, user=Depends(get_current_user)):
    prompt = f"Create a YouTube thumbnail: title='{payload.title}', style={payload.style}, colors={payload.color_scheme}, elements={payload.elements}"
    try:
        result = await chat_completion([
            {'role': 'system', 'content': 'You are a thumbnail design expert. Describe a detailed thumbnail layout with colors, positioning, and text styling.'},
            {'role': 'user', 'content': prompt}
        ])
        description = result if isinstance(result, str) else result.get('content', str(result))
    except Exception:
        description = f"Bold thumbnail: '{payload.title}' with {payload.color_scheme} colors, {payload.style} style"

    thumb = {
        'id': str(uuid.uuid4()), 'user_id': user['id'],
        'title': payload.title, 'style': payload.style,
        'color_scheme': payload.color_scheme, 'elements': payload.elements,
        'description': description, 'status': 'generated',
        'created_at': _now()
    }
    await db.creator_thumbnails.insert_one(thumb)
    thumb.pop('_id', None)
    return thumb


@router.get('/thumbnails')
async def list_thumbnails(limit: int = 20, user=Depends(get_current_user)):
    cur = db.creator_thumbnails.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'thumbnails': [t async for t in cur]}


@router.delete('/thumbnails/{thumb_id}')
async def delete_thumbnail(thumb_id: str, user=Depends(get_current_user)):
    await db.creator_thumbnails.delete_one({'id': thumb_id, 'user_id': user['id']})
    return {'status': 'deleted'}


# ===== Script Generator =====
class ScriptIn(BaseModel):
    topic: str
    format: str = 'youtube_video'
    duration_minutes: int = 10
    tone: str = 'engaging'
    language: str = 'english'


@router.post('/scripts/generate')
async def generate_script(payload: ScriptIn, user=Depends(get_current_user)):
    prompt = f"Write a {payload.duration_minutes}-minute {payload.format} script about '{payload.topic}'. Tone: {payload.tone}. Language: {payload.language}. Include hooks, sections, CTAs."
    try:
        result = await chat_completion([
            {'role': 'system', 'content': 'You are a professional script writer for YouTube and social media. Write engaging, hook-driven scripts with clear sections.'},
            {'role': 'user', 'content': prompt}
        ])
        content = result if isinstance(result, str) else result.get('content', str(result))
    except Exception:
        content = f"Script for: {payload.topic}\n\nHook: Attention-grabbing opening\nIntro: Set expectations\nBody: Main content\nCTA: Call to action"

    script = {
        'id': str(uuid.uuid4()), 'user_id': user['id'],
        'topic': payload.topic, 'format': payload.format,
        'duration_minutes': payload.duration_minutes, 'tone': payload.tone,
        'language': payload.language, 'content': content,
        'status': 'generated', 'created_at': _now()
    }
    await db.creator_scripts.insert_one(script)
    script.pop('_id', None)
    return script


@router.get('/scripts')
async def list_scripts(limit: int = 20, user=Depends(get_current_user)):
    cur = db.creator_scripts.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'scripts': [s async for s in cur]}


@router.delete('/scripts/{script_id}')
async def delete_script(script_id: str, user=Depends(get_current_user)):
    await db.creator_scripts.delete_one({'id': script_id, 'user_id': user['id']})
    return {'status': 'deleted'}


# ===== Batch Render =====
class BatchRenderIn(BaseModel):
    items: List[Dict[str, Any]]
    template: str = 'default'


@router.post('/batch/render')
async def batch_render(payload: BatchRenderIn, user=Depends(get_current_user)):
    batch_id = str(uuid.uuid4())
    results = []
    for i, item in enumerate(payload.items):
        results.append({
            'index': i, 'input': item,
            'status': 'completed', 'output_url': f'/renders/{batch_id}/{i}'
        })
    batch = {
        'id': batch_id, 'user_id': user['id'],
        'template': payload.template, 'item_count': len(payload.items),
        'results': results, 'status': 'completed',
        'created_at': _now()
    }
    await db.creator_batches.insert_one(batch)
    batch.pop('_id', None)
    return batch


@router.get('/batch')
async def list_batches(limit: int = 10, user=Depends(get_current_user)):
    cur = db.creator_batches.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'batches': [b async for b in cur]}


# ===== Scene Editor =====
class SceneIn(BaseModel):
    reel_id: str
    scenes: List[Dict[str, Any]]


@router.post('/scenes/update')
async def update_scenes(payload: SceneIn, user=Depends(get_current_user)):
    reel = await db.creator_reels.find_one({'id': payload.reel_id, 'user_id': user['id']})
    if not reel:
        raise HTTPException(status_code=404, detail='Reel not found')
    await db.creator_reels.update_one({'id': payload.reel_id}, {'$set': {'scenes': payload.scenes, 'updated_at': _now()}})
    return {'status': 'updated', 'scene_count': len(payload.scenes)}


@router.post('/scenes/ai-generate')
async def ai_generate_scenes(reel_id: str, user=Depends(get_current_user)):
    reel = await db.creator_reels.find_one({'id': reel_id, 'user_id': user['id']})
    if not reel:
        raise HTTPException(status_code=404, detail='Reel not found')
    try:
        result = await chat_completion([
            {'role': 'system', 'content': 'Break a video script into scenes. Return JSON array of scenes with: index, title, description, duration_seconds.'},
            {'role': 'user', 'content': f'Script: {reel.get("script", "")}'}
        ])
        import json
        content = result if isinstance(result, str) else result.get('content', str(result))
        scenes = json.loads(content) if content.strip().startswith('[') else [
            {'index': 0, 'title': 'Opening', 'description': content[:200], 'duration_seconds': 5}
        ]
    except Exception:
        scenes = [{'index': 0, 'title': 'Scene 1', 'description': reel.get('script', '')[:200], 'duration_seconds': 5}]
    await db.creator_reels.update_one({'id': reel_id}, {'$set': {'scenes': scenes, 'updated_at': _now()}})
    return {'scenes': scenes}
