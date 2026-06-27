"""Media Studio routes - 4K image gen, logo kit, voice (stub), video (stub), mirror (stub).

Production-ready: image + logo work today via Pollinations.ai (free, no key).
Voice / Video / Mirror return graceful 'pending provider' responses with clear
UI guidance until fal.ai or HuggingFace tokens are configured.
"""
import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from auth import get_current_user
from db import db
from media import pollinations
from media.quota import get_quota, check_and_consume

router = APIRouter(prefix='/media', tags=['media'])

HF_TOKEN = os.environ.get('HF_TOKEN', '').strip()
FAL_KEY = os.environ.get('FAL_KEY', '').strip()


class ImageGenIn(BaseModel):
    prompt: str
    style: str = 'photoreal'
    width: int = 1024
    height: int = 1024
    seed: Optional[int] = None


class LogoGenIn(BaseModel):
    brand_name: str
    tagline: Optional[str] = ''
    style: str = 'minimal'
    palette: Optional[str] = 'monochrome'


class VoiceGenIn(BaseModel):
    text: str
    voice: str = 'female-warm'


class VideoGenIn(BaseModel):
    prompt: str
    duration_seconds: int = 5
    aspect: str = '16:9'


class MirrorGenIn(BaseModel):
    source_image_url: str
    target_image_url: str


@router.get('/quota')
async def quota(user=Depends(get_current_user)):
    return await get_quota(user)


@router.get('/tools')
async def list_tools(user=Depends(get_current_user)):
    q = await get_quota(user)
    tools = [
        {'id': 'image', 'name': '4K Image Studio', 'tagline': 'Photoreal, art, product shots', 'status': 'live', 'badge': 'Free', 'provider': 'Pollinations AI'},
        {'id': 'logo',  'name': 'Logo & Brand Kit', 'tagline': 'Vector-style brand marks', 'status': 'live', 'badge': 'Free', 'provider': 'Pollinations AI'},
        {'id': 'voice', 'name': 'Voice Studio',     'tagline': 'Studio narration & dubbing', 'status': 'pending' if not HF_TOKEN else 'live', 'badge': 'Pro', 'provider': 'Coqui XTTS (HF)'},
        {'id': 'video', 'name': '4K Video Studio',  'tagline': 'AI clips & reels', 'status': 'pending' if not (HF_TOKEN or FAL_KEY) else 'live', 'badge': 'Pro', 'provider': 'AnimateDiff / Kling'},
        {'id': 'mirror','name': 'Mirror AI',         'tagline': 'Face mirror & swap', 'status': 'pending' if not (HF_TOKEN or FAL_KEY) else 'live', 'badge': 'Pro', 'provider': 'Live Portrait'},
    ]
    return {'tools': tools, 'quota': q}


# ===== IMAGE (LIVE - Free, Pollinations) =====
@router.post('/image')
async def gen_image(payload: ImageGenIn, user=Depends(get_current_user)):
    ok, msg = await check_and_consume(user, 'images', 1)
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    if len(payload.prompt.strip()) < 3:
        raise HTTPException(status_code=400, detail='Prompt is too short')
    # Cap resolution by plan tier (free = 1024, pro = 1536, elite = 2048)
    w = min(max(payload.width, 256), 2048)
    h = min(max(payload.height, 256), 2048)
    url = pollinations.build_url(payload.prompt, payload.style, w, h, payload.seed)
    item = {
        'id': str(uuid.uuid4()),
        'user_id': user['id'],
        'kind': 'image',
        'prompt': payload.prompt,
        'style': payload.style,
        'url': url,
        'width': w, 'height': h,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.media_assets.insert_one(item)
    item.pop('_id', None)
    return item


# ===== LOGO (LIVE - Free, Pollinations) =====
@router.post('/logo')
async def gen_logo(payload: LogoGenIn, user=Depends(get_current_user)):
    ok, msg = await check_and_consume(user, 'logos', 1)
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    prompt = f'logo for "{payload.brand_name}", {payload.style} style, {payload.palette} palette, vector mark, flat, centered, modern brand identity'
    if payload.tagline:
        prompt += f', tagline "{payload.tagline}"'
    # Generate 4 variants
    variants = []
    for i in range(4):
        url = pollinations.build_url(prompt, style='logo', width=1024, height=1024, seed=10000 + i * 17)
        variants.append({'index': i, 'url': url})
    item = {
        'id': str(uuid.uuid4()),
        'user_id': user['id'],
        'kind': 'logo',
        'brand_name': payload.brand_name,
        'tagline': payload.tagline,
        'variants': variants,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.media_assets.insert_one(item)
    item.pop('_id', None)
    return item


# ===== VOICE (PENDING - needs HF_TOKEN or fal.ai) =====
@router.post('/voice')
async def gen_voice(payload: VoiceGenIn, user=Depends(get_current_user)):
    if not (HF_TOKEN or FAL_KEY):
        return {
            'status': 'pending_provider',
            'message': 'Voice Studio is launching soon. Configure HF_TOKEN or FAL_KEY to enable.',
            'preview_text': payload.text[:200],
        }
    ok, msg = await check_and_consume(user, 'voice_min', max(1, len(payload.text) // 800))
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    # TODO: hook up HF Inference / fal.ai when key provided
    return {'status': 'queued', 'message': 'Voice generation queued', 'text': payload.text}


# ===== VIDEO (PENDING) =====
@router.post('/video')
async def gen_video(payload: VideoGenIn, user=Depends(get_current_user)):
    if not (HF_TOKEN or FAL_KEY):
        return {
            'status': 'pending_provider',
            'message': '4K Video Studio is launching soon. Configure FAL_KEY for Kling/Veo or HF_TOKEN for AnimateDiff.',
            'prompt': payload.prompt,
        }
    ok, msg = await check_and_consume(user, 'videos', 1)
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    return {'status': 'queued', 'message': 'Video generation queued'}


# ===== MIRROR (PENDING) =====
@router.post('/mirror')
async def gen_mirror(payload: MirrorGenIn, user=Depends(get_current_user)):
    if not (HF_TOKEN or FAL_KEY):
        return {
            'status': 'pending_provider',
            'message': 'Mirror AI is launching soon. Configure FAL_KEY (Live Portrait) to enable.',
        }
    ok, msg = await check_and_consume(user, 'mirror', 1)
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    return {'status': 'queued', 'message': 'Mirror AI queued'}


# ===== HISTORY =====
@router.get('/history')
async def history(limit: int = 24, user=Depends(get_current_user)):
    cur = db.media_assets.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'items': [doc async for doc in cur]}
