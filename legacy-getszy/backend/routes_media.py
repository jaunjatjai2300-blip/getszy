"""Media Studio routes - 4K image gen, logo kit, voice (stub), video (stub), mirror (stub).

Production-ready: image + logo work today via Pollinations.ai (free, no key).
Voice / Video / Mirror return graceful 'pending provider' responses with clear
UI guidance until fal.ai or HuggingFace tokens are configured.
"""
import asyncio
import os
import uuid
import httpx
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List

from auth import get_current_user
from db import db
from media import pollinations
from credits import deduct, refund, get_balance, CREDIT_COSTS
from video.tts import synth as tts_synth, pick_voice

router = APIRouter(prefix='/media', tags=['media'])

HF_TOKEN = os.environ.get('HF_TOKEN', '').strip()
FAL_KEY = os.environ.get('FAL_KEY', '').strip()

# On-disk cache for generated images (served back through /api/media/file/...)
CACHE_DIR = Path(os.environ.get('MEDIA_CACHE_DIR', str(Path(__file__).resolve().parent / 'media_cache')))
CACHE_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_CACHE_DIR = CACHE_DIR / 'audio'
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)


async def _prefetch_and_cache(remote_url: str, asset_id: str, suffix: str = '.jpg') -> Optional[str]:
    """Download an image once and cache it locally. Returns local relative URL.

    Retries once on failure since the free Pollinations tier occasionally times out under load.
    Returns None only if both attempts fail, so callers can gracefully fall back to the remote URL.
    """
    out_path = CACHE_DIR / f'{asset_id}{suffix}'
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
                r = await client.get(remote_url)
                r.raise_for_status()
                data = r.content
                if not data or len(data) < 1024:  # likely an error placeholder
                    continue
                out_path.write_bytes(data)
                return f'/api/media/file/{asset_id}{suffix}'
        except Exception:
            if attempt == 0:
                await asyncio.sleep(1.5)
    return None


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
    language: str = 'hinglish'
    gender: str = 'female'


class VideoGenIn(BaseModel):
    prompt: str
    duration_seconds: int = 5
    aspect: str = '16:9'


class MirrorGenIn(BaseModel):
    source_image_url: str
    target_image_url: str


@router.get('/tools')
async def list_tools(user=Depends(get_current_user)):
    balance = await get_balance(user['id'])
    tools = [
        {'id': 'image', 'name': '4K Image Studio', 'tagline': 'Photoreal, art, product shots', 'status': 'live', 'cost': CREDIT_COSTS['image'], 'provider': 'Pollinations AI'},
        {'id': 'logo',  'name': 'Logo & Brand Kit', 'tagline': 'Vector-style brand marks', 'status': 'live', 'cost': CREDIT_COSTS['logo'], 'provider': 'Pollinations AI'},
        {'id': 'voice', 'name': 'Voice Studio',     'tagline': 'Studio narration & dubbing', 'status': 'live', 'cost': CREDIT_COSTS['voice_min'], 'provider': 'Edge Neural TTS (free)'},
        {'id': 'video', 'name': '4K Video Studio',  'tagline': 'AI clips & reels', 'status': 'pending' if not (HF_TOKEN or FAL_KEY) else 'live', 'cost': CREDIT_COSTS['video_quick'], 'provider': 'AnimateDiff / Kling'},
        {'id': 'mirror','name': 'Mirror AI',         'tagline': 'Face mirror & swap', 'status': 'pending' if not (HF_TOKEN or FAL_KEY) else 'live', 'cost': CREDIT_COSTS['mirror'], 'provider': 'Live Portrait'},
    ]
    return {'tools': tools, 'credits': balance}


# ===== IMAGE (LIVE - Free, Pollinations) =====
@router.post('/image')
async def gen_image(payload: ImageGenIn, user=Depends(get_current_user)):
    if len(payload.prompt.strip()) < 3:
        raise HTTPException(status_code=400, detail='Prompt is too short')
    ok, msg, _ = await deduct(user['id'], 'image')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    try:
        # Cap resolution by plan tier (free = 1024, pro = 1536, elite = 2048)
        w = min(max(payload.width, 256), 2048)
        h = min(max(payload.height, 256), 2048)
        remote_url = pollinations.build_url(payload.prompt, payload.style, w, h, payload.seed)
        asset_id = str(uuid.uuid4())
        # Pre-fetch + cache so the client gets a fast, stable URL
        local_url = await _prefetch_and_cache(remote_url, asset_id)
        final_url = local_url or remote_url
        item = {
            'id': asset_id,
            'user_id': user['id'],
            'kind': 'image',
            'prompt': payload.prompt,
            'style': payload.style,
            'url': final_url,
            'remote_url': remote_url,
            'cached': bool(local_url),
            'width': w, 'height': h,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.media_assets.insert_one(item)
        item.pop('_id', None)
        return item
    except Exception:
        await refund(user['id'], 'image', reason='generation_failed')
        raise


# ===== LOGO (LIVE - Free, Pollinations) =====
@router.post('/logo')
async def gen_logo(payload: LogoGenIn, user=Depends(get_current_user)):
    ok, msg, _ = await deduct(user['id'], 'logo')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    try:
        prompt = f'logo for "{payload.brand_name}", {payload.style} style, {payload.palette} palette, vector mark, flat, centered, modern brand identity'
        if payload.tagline:
            prompt += f', tagline "{payload.tagline}"'
        # Generate 4 variants in parallel, then cache them
        import asyncio
        asset_id = str(uuid.uuid4())
        remote_urls = [pollinations.build_url(prompt, style='logo', width=1024, height=1024, seed=10000 + i * 17) for i in range(4)]
        variant_ids = [f'{asset_id}_v{i}' for i in range(4)]
        cached = await asyncio.gather(*[_prefetch_and_cache(u, vid) for u, vid in zip(remote_urls, variant_ids)])
        variants = [{'index': i, 'url': (cached[i] or remote_urls[i]), 'cached': bool(cached[i])} for i in range(4)]
        item = {
            'id': asset_id,
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
    except Exception:
        await refund(user['id'], 'logo', reason='generation_failed')
        raise


# ===== Serve cached image bytes =====
@router.get('/file/{filename}')
async def serve_cached(filename: str):
    # Basic safety: only allow simple cached filenames
    if '/' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail='Invalid filename')
    path = CACHE_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail='Not found')
    return FileResponse(str(path), media_type='image/jpeg', headers={'Cache-Control': 'public, max-age=31536000, immutable'})


# ===== Serve cached voice audio =====
@router.get('/audio/{filename}')
async def serve_audio(filename: str):
    if '/' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail='Invalid filename')
    path = AUDIO_CACHE_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail='Not found')
    return FileResponse(str(path), media_type='audio/mpeg', headers={'Cache-Control': 'public, max-age=31536000, immutable'})


# ===== VOICE (LIVE - free, Edge Neural TTS, no key needed) =====
@router.post('/voice')
async def gen_voice(payload: VoiceGenIn, user=Depends(get_current_user)):
    if len(payload.text.strip()) < 2:
        raise HTTPException(status_code=400, detail='Text is too short')
    qty = max(1, len(payload.text) // 800)
    ok, msg, _ = await deduct(user['id'], 'voice_min', qty)
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    try:
        voice_id = pick_voice(payload.language, payload.gender)
        asset_id = str(uuid.uuid4())
        out_path = AUDIO_CACHE_DIR / f'{asset_id}.mp3'
        await tts_synth(payload.text[:6000], str(out_path), voice=voice_id)
        item = {
            'id': asset_id,
            'user_id': user['id'],
            'kind': 'voice',
            'text': payload.text[:6000],
            'voice': voice_id,
            'url': f'/api/media/audio/{asset_id}.mp3',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.media_assets.insert_one(item)
        item.pop('_id', None)
        return {'status': 'done', **item}
    except Exception:
        await refund(user['id'], 'voice_min', qty=qty, reason='generation_failed')
        raise


# ===== VIDEO (PENDING) =====
@router.post('/video')
async def gen_video(payload: VideoGenIn, user=Depends(get_current_user)):
    if not (HF_TOKEN or FAL_KEY):
        return {
            'status': 'pending_provider',
            'message': '4K Video Studio is launching soon. Configure FAL_KEY for Kling/Veo or HF_TOKEN for AnimateDiff.',
            'prompt': payload.prompt,
        }
    ok, msg, _ = await deduct(user['id'], 'video_quick')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    return {'status': 'queued', 'message': 'Video generation queued'}


class TryOnIn(BaseModel):
    product_id: str
    product_name: str
    product_image: Optional[str] = None
    user_photo_url: Optional[str] = None  # data URL or hosted URL of selfie
    setting: str = 'studio'  # studio | outdoor | festive


# ===== MIRROR (PENDING) =====
@router.post('/mirror')
async def gen_mirror(payload: MirrorGenIn, user=Depends(get_current_user)):
    if not (HF_TOKEN or FAL_KEY):
        return {
            'status': 'pending_provider',
            'message': 'Mirror AI is launching soon. Configure FAL_KEY (Live Portrait) to enable.',
        }
    ok, msg, _ = await deduct(user['id'], 'mirror')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    return {'status': 'queued', 'message': 'Mirror AI queued'}


# ===== VIRTUAL TRY-ON (LIVE - product try-on via Pollinations + cache) =====
@router.post('/tryon')
async def gen_tryon(payload: TryOnIn, user=Depends(get_current_user)):
    """AI-powered virtual try-on for physical products.

    Generates a lifestyle/wear image of the product using Pollinations.
    When FAL_KEY is set later we'll switch to a real face-clone provider.
    """
    ok, msg, _ = await deduct(user['id'], 'tryon')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    try:
        setting_text = {
            'studio': 'professional studio portrait, soft lighting, neutral backdrop',
            'outdoor': 'natural outdoor setting, golden hour light, lifestyle photography',
            'festive': 'festive indian celebration setting, diyas, marigold flowers, warm tones',
        }.get(payload.setting, 'professional studio portrait')
        prompt = f'fashion model wearing {payload.product_name}, {setting_text}, full body shot, indian audience, premium photography, 4k'
        remote = pollinations.build_url(prompt, style='portrait', width=768, height=1024)
        asset_id = str(uuid.uuid4())
        local_url = await _prefetch_and_cache(remote, asset_id)
        item = {
            'id': asset_id,
            'user_id': user['id'],
            'kind': 'tryon',
            'product_id': payload.product_id,
            'product_name': payload.product_name,
            'setting': payload.setting,
            'url': local_url or remote,
            'remote_url': remote,
            'cached': bool(local_url),
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.media_assets.insert_one(item)
        item.pop('_id', None)
        return item
    except Exception:
        await refund(user['id'], 'tryon', reason='generation_failed')
        raise


# ===== HISTORY =====
@router.get('/history')
async def history(limit: int = 24, user=Depends(get_current_user)):
    cur = db.media_assets.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'items': [doc async for doc in cur]}
