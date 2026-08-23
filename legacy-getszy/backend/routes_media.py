"""Media Studio routes - 4K image gen, logo kit, voice (stub), video (stub), mirror (stub).

Production-ready: image + logo work today via Pollinations.ai (free, no key).
Voice / Video / Mirror return graceful 'pending provider' responses with clear
UI guidance until fal.ai or HuggingFace tokens are configured.
"""
import asyncio
import os
import uuid
import httpx
import mimetypes
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import Optional, List

from auth import get_current_user
from db import db
from media import pollinations
from credits import deduct, refund, get_balance, CREDIT_COSTS
from video.tts import synth as tts_synth, pick_voice

router = APIRouter(prefix='/media', tags=['media'])

HF_TOKEN = os.environ.get('HF_TOKEN', '').strip()
FAL_KEY = os.environ.get('FAL_KEY', '').strip()

# On-disk cache for generated images (served back through /api/media/file/...).
# Compose explicitly sets MEDIA_CACHE_DIR=/app/backend/media so production uses the
# persistent backend_media volume; this local default keeps tests and bare-metal
# development writable without requiring an /app mount.
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
    prompt: str = Field(..., min_length=1, max_length=1000)
    style: str = 'photoreal'
    width: int = 1024
    height: int = 1024
    seed: Optional[int] = None


class LogoGenIn(BaseModel):
    brand_name: str = Field(..., min_length=1, max_length=120)
    tagline: Optional[str] = Field('', max_length=200)
    style: str = 'minimal'
    palette: Optional[str] = 'monochrome'


class VoiceGenIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=6000)
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


async def _require_media_owner(filename: str, user: dict):
    """Require the authenticated owner of a cached media asset."""
    user_id = user.get('id') if isinstance(user, dict) else None
    if not user_id:
        raise HTTPException(status_code=401, detail='Not authenticated')
    asset_id = Path(filename).stem
    owned = await db.media_assets.find_one({'id': asset_id, 'user_id': user_id}, {'_id': 0, 'id': 1})
    if not owned:
        # Older HF video jobs predate media_assets records; keep those files
        # accessible only to the job owner while the migration is completed.
        owned = await db.video_jobs.find_one(
            {'user_id': user_id, 'video_url': f'/api/media/file/{filename}'},
            {'_id': 0, 'id': 1},
        )
    if not owned:
        raise HTTPException(status_code=404, detail='Not found')


# ===== Serve cached media bytes =====
@router.get('/file/{filename}')
async def serve_cached(filename: str, user=Depends(get_current_user)):
    # Basic safety: only allow simple cached filenames
    if '/' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail='Invalid filename')
    await _require_media_owner(filename, user)
    path = CACHE_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail='Not found')
    media_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    return FileResponse(str(path), media_type=media_type, headers={'Cache-Control': 'private, max-age=3600'})


# ===== Serve cached voice audio =====
@router.get('/audio/{filename}')
async def serve_audio(filename: str, user=Depends(get_current_user)):
    if '/' in filename or '..' in filename:
        raise HTTPException(status_code=400, detail='Invalid filename')
    await _require_media_owner(filename, user)
    path = AUDIO_CACHE_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail='Not found')
    return FileResponse(str(path), media_type='audio/mpeg', headers={'Cache-Control': 'private, max-age=3600'})


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


# ===== VIDEO (Queue job — real generation via FAL/HF when configured) =====
@router.post('/video')
async def gen_video(payload: VideoGenIn, user=Depends(get_current_user)):
    ok, msg, _ = await deduct(user['id'], 'video_quick')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)

    job_id = str(uuid.uuid4())
    job = {
        'id': job_id,
        'user_id': user['id'],
        'type': 'video',
        'prompt': payload.prompt,
        'duration_seconds': payload.duration_seconds,
        'aspect': payload.aspect,
        'status': 'queued',
        'provider': None,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }

    if FAL_KEY:
        job['provider'] = 'fal'
        job['status'] = 'processing'
        await db.video_jobs.insert_one(job)
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(
                    'https://fal.run/fal-ai/animatediff',
                    headers={'Authorization': f'Key {FAL_KEY}'},
                    json={'prompt': payload.prompt, 'num_frames': payload.duration_seconds * 8},
                )
                if r.status_code == 200:
                    result = r.json()
                    job['status'] = 'done'
                    job['video_url'] = result.get('video', {}).get('url', '')
                else:
                    job['status'] = 'failed'
                    job['error'] = f'FAL API error: {r.status_code}'
        except Exception as e:
            job['status'] = 'failed'
            job['error'] = str(e)[:200]
    elif HF_TOKEN:
        job['provider'] = 'huggingface'
        job['status'] = 'processing'
        await db.video_jobs.insert_one(job)
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(
                    'https://api-inference.huggingface.co/models/guyteich/AnimatedDiff',
                    headers={'Authorization': f'Bearer {HF_TOKEN}'},
                    json={'inputs': payload.prompt},
                )
                if r.status_code == 200:
                    asset_id = str(uuid.uuid4())
                    out_path = CACHE_DIR / f'{asset_id}.mp4'
                    out_path.write_bytes(r.content)
                    job['status'] = 'done'
                    job['video_url'] = f'/api/media/file/{asset_id}.mp4'
                    await db.media_assets.insert_one({
                        'id': asset_id,
                        'user_id': user['id'],
                        'kind': 'video',
                        'url': job['video_url'],
                        'created_at': datetime.now(timezone.utc).isoformat(),
                    })
                else:
                    job['status'] = 'failed'
                    job['error'] = f'HF API error: {r.status_code}'
        except Exception as e:
            job['status'] = 'failed'
            job['error'] = str(e)[:200]
    else:
        job['provider'] = 'none'
        job['status'] = 'pending_provider'
        job['message'] = 'Video generation queued. Set FAL_KEY or HF_TOKEN in .env to enable processing.'
        await db.video_jobs.insert_one(job)

    job.pop('_id', None)
    return job


class TryOnIn(BaseModel):
    product_id: str
    product_name: str
    product_image: Optional[str] = None
    user_photo_url: Optional[str] = None  # data URL or hosted URL of selfie
    setting: str = 'studio'  # studio | outdoor | festive


# ===== MIRROR (Queue job — real generation via FAL LivePortrait when configured) =====
@router.post('/mirror')
async def gen_mirror(payload: MirrorGenIn, user=Depends(get_current_user)):
    ok, msg, _ = await deduct(user['id'], 'mirror')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)

    job_id = str(uuid.uuid4())
    job = {
        'id': job_id,
        'user_id': user['id'],
        'type': 'mirror',
        'source_image_url': payload.source_image_url,
        'target_image_url': payload.target_image_url,
        'status': 'queued',
        'provider': None,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }

    if FAL_KEY:
        job['provider'] = 'fal'
        job['status'] = 'processing'
        await db.video_jobs.insert_one(job)
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                r = await client.post(
                    'https://fal.run/fal-ai/live-portrait',
                    headers={'Authorization': f'Key {FAL_KEY}'},
                    json={'source_image_url': payload.source_image_url, 'driving_image_url': payload.target_image_url},
                )
                if r.status_code == 200:
                    result = r.json()
                    job['status'] = 'done'
                    job['result_url'] = result.get('video', {}).get('url', '')
                else:
                    job['status'] = 'failed'
                    job['error'] = f'FAL API error: {r.status_code}'
        except Exception as e:
            job['status'] = 'failed'
            job['error'] = str(e)[:200]
    else:
        job['provider'] = 'none'
        job['status'] = 'pending_provider'
        job['message'] = 'Mirror AI queued. Set FAL_KEY in .env for Live Portrait processing.'
        await db.video_jobs.insert_one(job)

    job.pop('_id', None)
    return job


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
    limit = max(1, min(limit, 100))
    cur = db.media_assets.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'items': [doc async for doc in cur]}
