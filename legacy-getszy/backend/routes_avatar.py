"""Avatar & AI Tools routes — FREE via open-source HuggingFace models.

Endpoints:
  POST /avatar/generate       — portrait + audio → talking avatar video (SadTalker)
  POST /avatar/voice-clone    — text + reference audio → cloned voice (Coqui XTTS)
  POST /avatar/ai-image       — text prompt → HD image (FLUX.1-schnell)
  POST /avatar/ai-video       — text prompt → AI video clip (CogVideoX-5b)
  GET  /avatar/status         — which providers are active

All tools: 100% open-source, self-hosted via HuggingFace Spaces, cost = ₹0
"""
import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from auth import get_current_user
from db import db
from datetime import datetime, timezone
from video.ai_providers import (
    fetch_image, xtts_clone_voice, sadtalker_avatar,
    cogvideo_clip, extract_audio, watermark_video,
    providers_status, HF_TOKEN, AVATAR_DIR, AUDIO_DIR, CLIP_DIR
)

logger = logging.getLogger('getszy.avatar')
router = APIRouter(prefix='/avatar', tags=['avatar'])

UPLOAD_DIR = Path(__file__).parent / 'media_cache' / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _save_upload(data: bytes, ext: str) -> Path:
    path = UPLOAD_DIR / f'upload_{uuid.uuid4().hex[:10]}.{ext}'
    path.write_bytes(data)
    return path


async def _job_update(job_id: str, **kwargs):
    await db.ai_jobs.update_one(
        {'id': job_id},
        {'$set': {**kwargs, 'updated_at': datetime.now(timezone.utc).isoformat()}}
    )


# ─── Status ───────────────────────────────────────────────────────────────────

@router.get('/status')
async def status(_=Depends(get_current_user)):
    """Which open-source AI tools are active."""
    s = providers_status()
    return {
        'providers': s,
        'setup_needed': not s.get('flux_images'),
        'message': (
            'All AI tools active! ✅' if s.get('flux_images')
            else 'Add HF_TOKEN env var (free at huggingface.co) to unlock HD images, avatar & voice clone'
        ),
    }


# ─── 1. FLUX HD Image ─────────────────────────────────────────────────────────

class ImageIn(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=500)
    seed: int = 42


@router.post('/ai-image')
async def ai_image(payload: ImageIn, user=Depends(get_current_user)):
    """Generate HD image with FLUX.1-schnell (free via HuggingFace)."""
    path = await fetch_image(payload.prompt, payload.seed)
    if not path:
        raise HTTPException(status_code=503, detail='Image generation failed. Add HF_TOKEN for FLUX, or Pollinations is temporarily down.')
    return {'url': f'/media/{Path(path).name}', 'provider': 'flux' if HF_TOKEN else 'pollinations', 'prompt': payload.prompt}


# ─── 2. Voice Clone (Coqui XTTS) ─────────────────────────────────────────────

@router.post('/voice-clone')
async def voice_clone(
    bg: BackgroundTasks,
    text: str = Form(...),
    language: str = Form('hi'),
    reference_audio: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """Clone user voice: upload 10-30s reference audio → synthesized speech."""
    if not HF_TOKEN:
        raise HTTPException(status_code=503, detail='Voice clone needs HF_TOKEN. Get free token at huggingface.co/settings/tokens')

    audio_data = await reference_audio.read()
    if len(audio_data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='Reference audio too large (max 25 MB)')
    if len(audio_data) < 10_000:
        raise HTTPException(status_code=400, detail='Reference audio too short. Upload at least 10 seconds of clear speech.')

    ref_path = _save_upload(audio_data, 'wav')
    job_id = str(uuid.uuid4())

    await db.ai_jobs.insert_one({
        'id': job_id, 'user_id': user['id'], 'type': 'voice_clone',
        'status': 'queued', 'created_at': datetime.now(timezone.utc).isoformat(),
    })

    async def _run():
        await _job_update(job_id, status='processing')
        try:
            result = await xtts_clone_voice(text, str(ref_path), language)
            if result:
                await _job_update(job_id, status='done', output_path=result,
                                  url=f'/media/audio/{Path(result).name}')
            else:
                await _job_update(job_id, status='failed', error='XTTS space returned no audio')
        except Exception as e:
            await _job_update(job_id, status='failed', error=str(e))

    bg.add_task(_run)
    return {'job_id': job_id, 'status': 'queued', 'message': 'Voice cloning started — takes ~30-60 seconds'}


# ─── 3. AI Talking Avatar (SadTalker) ────────────────────────────────────────

@router.post('/generate')
async def generate_avatar(
    bg: BackgroundTasks,
    portrait: UploadFile = File(...),
    audio: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """Portrait photo + audio → talking avatar video (SadTalker, free)."""
    if not HF_TOKEN:
        raise HTTPException(status_code=503, detail='Avatar needs HF_TOKEN. Get free at huggingface.co/settings/tokens')

    portrait_data = await portrait.read()
    audio_data = await audio.read()
    if len(portrait_data) > 15 * 1024 * 1024 or len(audio_data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='Upload too large (max 15 MB image / 25 MB audio)')

    portrait_path = _save_upload(portrait_data, 'jpg')
    audio_path = _save_upload(audio_data, 'wav')

    job_id = str(uuid.uuid4())
    await db.ai_jobs.insert_one({
        'id': job_id, 'user_id': user['id'], 'type': 'avatar',
        'status': 'queued', 'created_at': datetime.now(timezone.utc).isoformat(),
    })

    async def _run():
        await _job_update(job_id, status='processing', percent=10)
        try:
            result = await sadtalker_avatar(str(portrait_path), str(audio_path))
            if result:
                await _job_update(job_id, status='done', percent=100,
                                  output_path=result, url=f'/media/avatars/{Path(result).name}')
                logger.info('Avatar job %s done', job_id)
            else:
                await _job_update(job_id, status='failed', error='SadTalker returned no video')
        except Exception as e:
            await _job_update(job_id, status='failed', error=str(e))
            logger.warning('Avatar job %s failed: %s', job_id, e)

    bg.add_task(_run)
    return {'job_id': job_id, 'status': 'queued', 'message': 'Avatar generation started — takes 2-4 minutes'}


# ─── 4. CogVideoX AI Clip ────────────────────────────────────────────────────

class VideoClipIn(BaseModel):
    prompt: str = Field(..., min_length=5, max_length=400)
    duration: int = 6
    seed: int = 42


@router.post('/ai-video')
async def ai_video_clip(payload: VideoClipIn, bg: BackgroundTasks, user=Depends(get_current_user)):
    """Text prompt → cinematic AI video clip (CogVideoX-5b, free via HuggingFace)."""
    job_id = str(uuid.uuid4())
    await db.ai_jobs.insert_one({
        'id': job_id, 'user_id': user['id'], 'type': 'cogvideo',
        'status': 'queued', 'prompt': payload.prompt,
        'created_at': datetime.now(timezone.utc).isoformat(),
    })

    async def _run():
        await _job_update(job_id, status='generating', percent=5)
        try:
            result = await cogvideo_clip(payload.prompt, payload.seed, payload.duration)
            if result:
                await _job_update(job_id, status='done', percent=100,
                                  output_path=result, url=f'/media/clips/{Path(result).name}')
            else:
                await _job_update(job_id, status='failed', error='CogVideoX returned no video')
        except Exception as e:
            await _job_update(job_id, status='failed', error=str(e))

    bg.add_task(_run)
    return {'job_id': job_id, 'status': 'queued', 'message': 'AI video clip generating — takes 3-5 minutes'}


# ─── 5. Photo-to-Avatar (Text + Photo -> talking head) ────────────────────────

@router.post('/photo-to-avatar')
async def photo_to_avatar(
    bg: BackgroundTasks,
    portrait: UploadFile = File(...),
    script: str = Form(...),
    reference_audio: UploadFile = File(...),
    expression: str = Form('neutral'),
    user=Depends(get_current_user),
):
    """Text-to-Avatar: upload a photo + your script + a voice sample -> talking
    avatar that says your script in your cloned voice (expressive metadata kept)."""
    if not HF_TOKEN:
        raise HTTPException(status_code=503, detail='Avatar needs HF_TOKEN. Get free at huggingface.co/settings/tokens')
    portrait_data = await portrait.read()
    ref_data = await reference_audio.read()
    if len(portrait_data) > 15 * 1024 * 1024 or len(ref_data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='Upload too large (max 15 MB image / 25 MB audio)')
    if len(ref_data) < 10_000:
        raise HTTPException(status_code=400, detail='Voice sample too short. Upload at least 10 seconds of clear speech.')

    portrait_path = _save_upload(portrait_data, 'jpg')
    ref_path = _save_upload(ref_data, 'wav')
    job_id = str(uuid.uuid4())
    await db.ai_jobs.insert_one({
        'id': job_id, 'user_id': user['id'], 'type': 'photo_to_avatar',
        'status': 'queued', 'expression': expression,
        'created_at': datetime.now(timezone.utc).isoformat(),
    })

    async def _run():
        await _job_update(job_id, status='processing', percent=10)
        try:
            voice = await xtts_clone_voice(script, str(ref_path), language='hi')
            if not voice:
                await _job_update(job_id, status='failed', error='Voice clone returned no audio')
                return
            result = await sadtalker_avatar(str(portrait_path), voice)
            if result:
                await _job_update(job_id, status='done', percent=100,
                                  output_path=result, url=f'/media/avatars/{Path(result).name}',
                                  expression=expression)
            else:
                await _job_update(job_id, status='failed', error='SadTalker returned no video')
        except Exception as e:
            await _job_update(job_id, status='failed', error=str(e))

    bg.add_task(_run)
    return {'job_id': job_id, 'status': 'queued', 'expression': expression,
            'message': 'Building your talking avatar — takes 2-4 minutes'}


# ─── 6. Digital Twin (Video -> clone voice + face) ─────────────────────────────

@router.post('/digital-twin')
async def digital_twin(
    bg: BackgroundTasks,
    video: UploadFile = File(...),
    portrait: UploadFile = File(...),
    script: str = Form(...),
    user=Depends(get_current_user),
):
    """Video-to-Avatar: upload a short clip of you speaking + a clear portrait ->
    AI clones your voice and animates the portrait (your Digital Twin)."""
    if not HF_TOKEN:
        raise HTTPException(status_code=503, detail='Digital Twin needs HF_TOKEN. Get free at huggingface.co/settings/tokens')
    video_data = await video.read()
    portrait_data = await portrait.read()
    if len(video_data) > 100 * 1024 * 1024 or len(portrait_data) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='Upload too large (max 100 MB video / 15 MB image)')

    vid_path = _save_upload(video_data, 'mp4')
    portrait_path = _save_upload(portrait_data, 'jpg')
    job_id = str(uuid.uuid4())
    await db.ai_jobs.insert_one({
        'id': job_id, 'user_id': user['id'], 'type': 'digital_twin',
        'status': 'queued', 'created_at': datetime.now(timezone.utc).isoformat(),
    })

    async def _run():
        await _job_update(job_id, status='processing', percent=10)
        try:
            ref = await extract_audio(str(vid_path))
            if not ref:
                await _job_update(job_id, status='failed', error='ffmpeg unavailable — cannot extract voice from video')
                return
            voice = await xtts_clone_voice(script, ref, language='hi')
            if not voice:
                await _job_update(job_id, status='failed', error='Voice clone returned no audio')
                return
            result = await sadtalker_avatar(str(portrait_path), voice)
            if result:
                await _job_update(job_id, status='done', percent=100,
                                  output_path=result, url=f'/media/avatars/{Path(result).name}')
            else:
                await _job_update(job_id, status='failed', error='SadTalker returned no video')
        except Exception as e:
            await _job_update(job_id, status='failed', error=str(e))

    bg.add_task(_run)
    return {'job_id': job_id, 'status': 'queued',
            'message': 'Creating your Digital Twin — takes 3-5 minutes'}


# ─── Job status poll ──────────────────────────────────────────────────────────

@router.get('/job/{job_id}')
async def job_status(job_id: str, user=Depends(get_current_user)):
    job = await db.ai_jobs.find_one({'id': job_id, 'user_id': user['id']}, {'_id': 0})
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    return job


@router.post('/generate-image')
async def generate_image_alias(payload: ImageIn, user=Depends(get_current_user)):
    """Frontend calls /avatar/generate-image."""
    return await ai_image(payload, user)


@router.post('/clone-voice')
async def clone_voice_alias(bg: BackgroundTasks, text: str = Form(...), language: str = Form('hi'), reference_audio: UploadFile = File(...), user=Depends(get_current_user)):
    """Frontend calls /avatar/clone-voice (multipart form-data)."""
    return await voice_clone(bg, text, language, reference_audio, user)


@router.post('/talking-head')
async def talking_head_alias(bg: BackgroundTasks, portrait: UploadFile = File(...), audio: UploadFile = File(...), user=Depends(get_current_user)):
    """Frontend calls /avatar/talking-head (multipart) → SadTalker talking avatar."""
    return await generate_avatar(bg, portrait, audio, user)
