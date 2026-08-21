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
    # P0-5: previously flipped status to 'rendered' with fake stub scenes
    # without ever invoking the video pipeline. Reject cleanly until a real
    # renderer is wired in (video/pipeline.py already exists for text-to-video
    # jobs — use that flow via /video-tools/text-to-video instead).
    reel = await db.creator_reels.find_one({'id': reel_id, 'user_id': user['id']})
    if not reel:
        raise HTTPException(status_code=404, detail='Reel not found')
    raise HTTPException(
        status_code=501,
        detail='Reel rendering is not yet implemented on this endpoint. Use /api/video-tools/text-to-video to render a video from a script.',
    )


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
    # P0-4: gate the LLM call behind the credit engine. Frontend now prefers
    # the credited /creator/thumbnail flow — but this endpoint is still mounted
    # for API compatibility, so it must be equally protected.
    thumb_id = str(uuid.uuid4())
    ok, msg, _ = await deduct(user['id'], 'platform_thumbnail')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    prompt = f"Create a YouTube thumbnail: title='{payload.title}', style={payload.style}, colors={payload.color_scheme}, elements={payload.elements}"
    try:
        result = await chat_completion(
            system=(
                'You are an elite YouTube thumbnail designer with millions of views of experience. '
                'Describe a detailed, high-CTR thumbnail layout: composition, focal point, color '
                'palette, typography, text overlay copy (short, punchy), and emotional angle. '
                'Be specific and visual.'
            ),
            user=prompt,
            max_tokens=1500,
        )
        description = result if isinstance(result, str) else result.get('content', str(result))
    except Exception:
        await refund(user['id'], 'platform_thumbnail', reason='generation_failed', ref_id=thumb_id)
        raise HTTPException(status_code=503, detail='AI service temporarily unavailable. Please try again shortly.')

    thumb = {
        'id': thumb_id, 'user_id': user['id'],
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
    # P0-4: gate the 4k-token LLM call behind the credit engine.
    script_id = str(uuid.uuid4())
    ok, msg, _ = await deduct(user['id'], 'platform_script')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    prompt = (
        f"Write a {payload.duration_minutes}-minute {payload.format} script about '{payload.topic}'. "
        f"Tone: {payload.tone}. Language: {payload.language}. "
        f"Structure it with: a scroll-stopping Hook (first 3 seconds), a clear Promise, "
        f"3-5 value-packed Sections, tasteful Story/example, and a strong Call-To-Action. "
        f"Make it natural, spoken-aloud friendly, and retention-optimized."
    )
    try:
        result = await chat_completion(
            system=(
                'You are a top-tier script writer for YouTube and short-form social video (10M+ '
                'subscriber calibre). Write engaging, hook-driven, retention-optimized scripts with '
                'clear sections, natural spoken language, and a compelling CTA. Avoid fluff.'
            ),
            user=prompt,
            max_tokens=4000,
        )
        content = result if isinstance(result, str) else result.get('content', str(result))
    except Exception:
        await refund(user['id'], 'platform_script', reason='generation_failed', ref_id=script_id)
        raise HTTPException(status_code=503, detail='AI service temporarily unavailable. Please try again shortly.')

    script = {
        'id': script_id, 'user_id': user['id'],
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
    # P0-6: previously returned fake success rows with non-existent output URLs.
    # Reject cleanly until batch rendering is really implemented.
    raise HTTPException(
        status_code=501,
        detail='Batch rendering is not yet implemented. Please render items individually via /api/video-tools/text-to-video.',
    )


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
    # P0-4: gate the LLM call.
    ok, msg, _ = await deduct(user['id'], 'platform_scenes')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    try:
        result = await chat_completion(
            system=(
                'You are a professional video editor. Break the given script into a JSON array of '
                'scenes. Each scene: {"index": int, "title": str, "description": str (visual + what '
                'happens), "duration_seconds": int (3-8), "visual_prompt": str (image-gen prompt)}. '
                'Return ONLY the JSON array, no markdown.'
            ),
            user=f'Script: {reel.get("script", "")}',
            max_tokens=4000,
        )
        import json
        import re
        content = result if isinstance(result, str) else result.get('content', str(result))
        content = re.sub(r'^```(?:json)?\s*|\s*```$', '', content.strip(), flags=re.IGNORECASE)
        try:
            scenes = json.loads(content)
        except Exception:
            scenes = [{'index': 0, 'title': 'Opening', 'description': content[:200], 'duration_seconds': 5}]
    except Exception:
        await refund(user['id'], 'platform_scenes', reason='generation_failed', ref_id=f'scenes:{reel_id}')
        raise HTTPException(status_code=503, detail='AI service temporarily unavailable. Please try again shortly.')
    await db.creator_reels.update_one({'id': reel_id}, {'$set': {'scenes': scenes, 'updated_at': _now()}})
    return {'scenes': scenes}
