"""Video Tools — game-changing creator features (Phase 1/2).

Endpoints (prefix /video-tools):
  POST /text-to-video        Topic -> script + AI scenes + voiceover plan
  POST /image-to-video       Photo -> animated clip
  POST /video-translate      Video -> translated, lip-synced (best-effort) video
  POST /one-tap-repurposing  Long video / link -> vertical shorts plan
  POST /social-publish       One-click publish to YouTube / Instagram / Facebook
  POST /influencer-reply     AI auto-reply to a social comment
  GET  /status               provider + free-tier status

Credit gating uses credits.py (deduct + refund on failure). Free users get a
small monthly allowance of WATERMARKED video generations (FREE_TIER_ACTIONS).
Heavy media work (real lip-sync, compositing, social OAuth) degrades gracefully
to a "configured: False" state until providers/env are wired — never crashes.
"""
import asyncio
import json
import logging
import os
import re
import uuid
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from auth import get_current_user
from db import db
from credits import (
    deduct, get_balance, has_enough, free_tier_remaining, free_tier_record,
    FREE_TIER_ACTIONS, WATERMARK_TEXT,
)
from llm_provider import chat_completion, LLMServiceUnavailable
from whisper_stt import transcribe
from video.ai_providers import (
    fetch_image, cogvideo_clip, xtts_clone_voice, extract_audio,
    watermark_video, lip_sync_video, concat_videos, burn_hormozi_captions,
    providers_status, CLIP_DIR,
)

logger = logging.getLogger('getszy.video_tools')
router = APIRouter(prefix='/video-tools', tags=['video-tools'])

UPLOAD_DIR = Path(__file__).parent / 'media_cache' / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Social OAuth env (set to enable one-click publish).
YT_ENABLED = bool(os.environ.get('YOUTUBE_CLIENT_ID') and os.environ.get('YOUTUBE_CLIENT_SECRET'))
META_ENABLED = bool(os.environ.get('META_APP_ID') and os.environ.get('META_APP_SECRET'))


# ─── shared helpers ───────────────────────────────────────────────────────────

def _save_upload(data: bytes, ext: str) -> Path:
    path = UPLOAD_DIR / f'vt_{uuid.uuid4().hex[:10]}.{ext}'
    path.write_bytes(data)
    return path


def _extract_json_array(text: str) -> Optional[list]:
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r'\[.*\]', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


async def _authorize(user: dict, action: str) -> tuple[bool, bool, Optional[str]]:
    """Return (allowed, watermarked, error). Admin/founder bypass everything."""
    if user.get('role') in ('admin', 'founder'):
        return True, False, None
    if has_enough(user, action):
        return True, False, None
    # Free tier: watermarked allowance for video outputs.
    if action in FREE_TIER_ACTIONS and await free_tier_remaining(user['id']) > 0:
        return True, True, None
    bal = await get_balance(user['id'])
    return False, False, (
        f'Not enough credits (need {1} for this). You have {bal}. '
        'Upgrade to Creator Pass or use your free watermarked tier.'
    )


async def _refund(user_id: str, action: str):
    # Credits are only deducted on success; free-tier count is recorded only on
    # success too, so there is nothing to roll back here. Kept for symmetry.
    return


# ─── 1. Text-to-Video ──────────────────────────────────────────────────────────

class TextToVideoIn(BaseModel):
    topic: str = Field(..., min_length=3, max_length=300)
    style: str = 'story'          # story | meme | documentary | ad
    scenes: int = 6
    language: str = 'hinglish'


@router.post('/text-to-video')
async def text_to_video(payload: TextToVideoIn, bg: BackgroundTasks, user=Depends(get_current_user)):
    allowed, watermarked, err = await _authorize(user, 'text_to_video')
    if not allowed:
        raise HTTPException(status_code=402, detail=err)
    project_id = str(uuid.uuid4())
    await db.video_projects.insert_one({
        'id': project_id, 'user_id': user['id'], 'kind': 'text_to_video',
        'status': 'scripting', 'topic': payload.topic, 'watermarked': watermarked,
        'created_at': datetime.now(timezone.utc).isoformat(),
    })
    bg.add_task(_run_text_to_video, project_id, payload, user['id'], watermarked)
    return {'project_id': project_id, 'status': 'scripting',
            'watermarked': watermarked,
            'message': 'Writing script and generating scenes…'}


async def _run_text_to_video(project_id, payload, user_id, watermarked):
    await db.video_projects.update_one({'id': project_id}, {'$set': {'status': 'scripting'}})
    try:
        system = (
            'You are a short-form video scriptwriter for Indian creators. '
            'Given a topic, return ONLY a JSON array of scene objects: '
            '[{"visual": "<image prompt for the shot>", '
            '"narration": "<1 short Hinglish sentence to speak>", '
            '"caption": "<2-4 word on-screen caption>"}]. '
            f'Produce exactly {payload.scenes} scenes. No markdown, no commentary.'
        )
        raw = await chat_completion(system, payload.topic, temperature=0.7)
        scenes = _extract_json_array(raw) or []
        if not scenes:
            raise ValueError('LLM did not return a valid scene list')
        built = []
        for i, sc in enumerate(scenes[:payload.scenes]):
            visual = sc.get('visual') or payload.topic
            img = await fetch_image(visual, seed=42 + i)
            clip = await cogvideo_clip(visual, seed=42 + i, duration=4)
            built.append({
                'scene': i + 1,
                'visual': visual,
                'narration': sc.get('narration', ''),
                'caption': sc.get('caption', ''),
                'image_url': (f'/media/{Path(img).name}' if img else None),
                'clip_url': (f'/media/clips/{Path(clip).name}' if clip else None),
            })
        if watermarked:
            await free_tier_record(user_id, 1)
        else:
            await deduct(user_id, 'text_to_video', user={'id': user_id})

        # Optional: compose a single captioned final video (FFmpeg + Hormozi ASS).
        final_url = None
        captions = []
        clips = []
        for i, s in enumerate(built):
            if s.get('clip_url'):
                name = s['clip_url'].split('/')[-1]
                p = str(CLIP_DIR / name)
                if os.path.exists(p):
                    clips.append(p)
                    captions.append({
                        'start': i * 4, 'end': i * 4 + 4,
                        'text': s.get('caption') or s.get('narration', ''),
                        'highlight': [],
                    })
        if clips:
            merged = await concat_videos(clips)
            if merged:
                brand = (await db.users.find_one({'id': user_id}, {'_id': 0, 'brand_kit': 1}) or {}).get('brand_kit')
                capped = await burn_hormozi_captions(merged, captions, brand)
                if capped:
                    final_url = f'/media/avatars/{Path(capped).name}'

        await db.video_projects.update_one(
            {'id': project_id},
            {'$set': {'status': 'done', 'storyboard': built, 'captions': captions,
                      'final_video_url': final_url,
                      'updated_at': datetime.now(timezone.utc).isoformat()}},
        )
    except LLMServiceUnavailable as e:
        await db.video_projects.update_one({'id': project_id}, {'$set': {'status': 'failed', 'error': str(e)}})
    except Exception as e:
        await db.video_projects.update_one({'id': project_id}, {'$set': {'status': 'failed', 'error': str(e)}})
        logger.warning('text_to_video %s failed: %s', project_id, e)


# ─── 2. Image-to-Video ─────────────────────────────────────────────────────────

@router.post('/image-to-video')
async def image_to_video(
    bg: BackgroundTasks,
    image: UploadFile = File(...),
    prompt: str = Form(...),
    duration: int = Form(5),
    user=Depends(get_current_user),
):
    allowed, watermarked, err = await _authorize(user, 'image_to_video')
    if not allowed:
        raise HTTPException(status_code=402, detail=err)
    data = await image.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='Image too large (max 20 MB)')
    img_path = _save_upload(data, 'jpg')
    job_id = str(uuid.uuid4())
    await db.ai_jobs.insert_one({
        'id': job_id, 'user_id': user['id'], 'type': 'image_to_video',
        'status': 'queued', 'watermarked': watermarked,
        'created_at': datetime.now(timezone.utc).isoformat(),
    })
    bg.add_task(_run_image_to_video, job_id, str(img_path), prompt, duration, user['id'], watermarked)
    return {'job_id': job_id, 'status': 'queued', 'watermarked': watermarked,
            'message': 'Animating your photo…'}


async def _run_image_to_video(job_id, img_path, prompt, duration, user_id, watermarked):
    await db.ai_jobs.update_one({'id': job_id}, {'$set': {'status': 'processing'}})
    try:
        clip = await cogvideo_clip(prompt, duration=duration)
        out = clip
        if clip and watermarked:
            wm = await watermark_video(clip, WATERMARK_TEXT)
            if wm:
                out = wm
        if watermarked:
            await free_tier_record(user_id, 1)
        else:
            await deduct(user_id, 'image_to_video', user={'id': user_id})
        await db.ai_jobs.update_one(
            {'id': job_id},
            {'$set': {'status': 'done', 'output_path': out,
                      'url': (f'/media/clips/{Path(out).name}' if out else None)}},
        )
    except Exception as e:
        await db.ai_jobs.update_one({'id': job_id}, {'$set': {'status': 'failed', 'error': str(e)}})
        logger.warning('image_to_video %s failed: %s', job_id, e)


# ─── 3. Video Translation (lip-sync, best-effort) ──────────────────────────────

@router.post('/video-translate')
async def video_translate(
    bg: BackgroundTasks,
    video: UploadFile = File(...),
    target_lang: str = Form('hindi'),
    transcript: str = Form(''),
    reference_audio: UploadFile = File(None),
    user=Depends(get_current_user),
):
    allowed, watermarked, err = await _authorize(user, 'video_translate')
    if not allowed:
        raise HTTPException(status_code=402, detail=err)
    data = await video.read()
    if len(data) > 200 * 1024 * 1024:
        raise HTTPException(status_code=413, detail='Video too large (max 200 MB)')
    vid_path = _save_upload(data, 'mp4')
    ref_path = None
    if reference_audio:
        ref_data = await reference_audio.read()
        if ref_data:
            ref_path = str(_save_upload(ref_data, 'wav'))
    job_id = str(uuid.uuid4())
    await db.ai_jobs.insert_one({
        'id': job_id, 'user_id': user['id'], 'type': 'video_translate',
        'status': 'queued', 'target_lang': target_lang, 'watermarked': watermarked,
        'created_at': datetime.now(timezone.utc).isoformat(),
    })
    bg.add_task(_run_video_translate, job_id, str(vid_path), target_lang, transcript, ref_path, user['id'], watermarked)
    return {'job_id': job_id, 'status': 'queued', 'watermarked': watermarked,
            'message': 'Translating and dubbing…'}


async def _run_video_translate(job_id, vid_path, target_lang, transcript, ref_path, user_id, watermarked):
    await db.ai_jobs.update_one({'id': job_id}, {'$set': {'status': 'translating'}})
    try:
        if not transcript:
            raise ValueError('Provide a transcript to translate (whisper ingest pending yt-dlp/whisper wiring).')
        system = (
            f'Translate the following transcript into {target_lang} (keep it natural, '
            'Hinglish-friendly). Return ONLY a JSON object: '
            '{"translated_text": "...", "captions": ["line1","line2",...]}. No markdown.'
        )
        raw = await chat_completion(system, transcript, temperature=0.3)
        try:
            res = json.loads(raw)
        except Exception:
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            res = json.loads(m.group(0)) if m else {'translated_text': raw, 'captions': []}
        translated = res.get('translated_text', '')
        # Voice: clone original voice if reference provided, else skip dubbing.
        dubbed_audio = None
        if ref_path:
            dubbed_audio = await xtts_clone_voice(translated, ref_path, language='hi')
        # Lip-sync: graceful no-op until a Wav2Lip/SadTalker-Face model is wired.
        synced = await lip_sync_video(vid_path, dubbed_audio) if dubbed_audio else None
        if watermarked:
            await free_tier_record(user_id, 1)
        else:
            await deduct(user_id, 'video_translate', user={'id': user_id})
        await db.ai_jobs.update_one(
            {'id': job_id},
            {'$set': {
                'status': 'done' if synced or dubbed_audio else 'done_no_lipsync',
                'translated_text': translated,
                'captions': res.get('captions', []),
                'dubbed_audio_url': (f'/media/audio/{Path(dubbed_audio).name}' if dubbed_audio else None),
                'synced_video_url': (f'/media/avatars/{Path(synced).name}' if synced else None),
                'note': (None if synced else 'Lip-sync model pending; dubbed audio + captions ready.'),
            }},
        )
    except LLMServiceUnavailable as e:
        await db.ai_jobs.update_one({'id': job_id}, {'$set': {'status': 'failed', 'error': str(e)}})
    except Exception as e:
        await db.ai_jobs.update_one({'id': job_id}, {'$set': {'status': 'failed', 'error': str(e)}})
        logger.warning('video_translate %s failed: %s', job_id, e)


# ─── 4. One-Tap Repurposing (long -> shorts) ───────────────────────────────────

class RepurposeIn(BaseModel):
    source: str = 'upload'        # 'upload' | 'youtube'
    url: Optional[str] = None
    transcript: str = ''
    count: int = 5


@router.post('/one-tap-repurposing')
async def one_tap_repurposing(payload: RepurposeIn, bg: BackgroundTasks, user=Depends(get_current_user)):
    allowed, watermarked, err = await _authorize(user, 'one_tap_repurposing')
    if not allowed:
        raise HTTPException(status_code=402, detail=err)
    if payload.source == 'youtube' and not payload.url:
        raise HTTPException(status_code=400, detail='Provide a YouTube URL or use source=upload with a transcript.')
    if payload.source == 'upload' and not payload.transcript.strip():
        raise HTTPException(status_code=400, detail='Paste the video transcript to extract shorts (yt-dlp ingest pending).')
    project_id = str(uuid.uuid4())
    await db.video_projects.insert_one({
        'id': project_id, 'user_id': user['id'], 'kind': 'repurpose',
        'status': 'analyzing', 'watermarked': watermarked, 'source': payload.source,
        'created_at': datetime.now(timezone.utc).isoformat(),
    })
    bg.add_task(_run_repurpose, project_id, payload, user['id'], watermarked)
    return {'project_id': project_id, 'status': 'analyzing', 'watermarked': watermarked,
            'message': 'Finding your best moments…'}


async def _youtube_to_transcript(url: str) -> Optional[str]:
    """Download a video's audio via yt-dlp, convert to 16k WAV, and transcribe
    with Whisper. Returns transcript text or None if yt-dlp/ffmpeg missing."""
    import shutil
    import tempfile
    if not shutil.which('yt-dlp') or not _ffmpeg_available():
        return None
    tmp = tempfile.mkdtemp()
    out_tmpl = os.path.join(tmp, 'audio.%(ext)s')
    proc = await asyncio.create_subprocess_exec(
        'yt-dlp', '-x', '--audio-format', 'wav', '-o', out_tmpl, url,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    await proc.wait()
    wav = next((os.path.join(tmp, f) for f in os.listdir(tmp) if f.endswith('.wav')), None)
    if not wav:
        return None
    wav16 = await extract_audio(wav)
    if not wav16:
        return None
    with open(wav16, 'rb') as fh:
        data = fh.read()
    res = await transcribe(data, 'audio.wav')
    return res.get('text') if 'text' in res else None


async def _run_repurpose(project_id, payload, user_id, watermarked):
    await db.video_projects.update_one({'id': project_id}, {'$set': {'status': 'analyzing'}})
    transcript = payload.transcript
    if not transcript.strip() and payload.source == 'youtube' and payload.url:
        await db.video_projects.update_one({'id': project_id}, {'$set': {'status': 'fetching_transcript'}})
        transcript = await _youtube_to_transcript(payload.url) or ''
    if not transcript.strip():
        await db.video_projects.update_one(
            {'id': project_id},
            {'$set': {'status': 'failed',
                      'error': 'Could not get a transcript. Install yt-dlp+ffmpeg for YouTube auto-extract, or paste a transcript.'}})
        return
    try:
        system = (
            'You are a YouTube Shorts editor. From a transcript, pick the most '
            f'engaging moments and return ONLY a JSON array of {payload.count} objects: '
            '[{"start": <sec>, "end": <sec>, "hook": "<scroll-stopping line>", '
            '"caption": "<2-4 word vertical caption>"}]. Moments must be 8-20s. No markdown.'
        )
        raw = await chat_completion(system, transcript, temperature=0.6)
        shorts = _extract_json_array(raw) or []
        if watermarked:
            await free_tier_record(user_id, 1)
        else:
            await deduct(user_id, 'one_tap_repurposing', user={'id': user_id})
        await db.video_projects.update_one(
            {'id': project_id},
            {'$set': {'status': 'done', 'shorts': shorts[:payload.count],
                      'updated_at': datetime.now(timezone.utc).isoformat()}},
        )
    except LLMServiceUnavailable as e:
        await db.video_projects.update_one({'id': project_id}, {'$set': {'status': 'failed', 'error': str(e)}})
    except Exception as e:
        await db.video_projects.update_one({'id': project_id}, {'$set': {'status': 'failed', 'error': str(e)}})
        logger.warning('repurpose %s failed: %s', project_id, e)


# ─── 5. One-Click Social Distribution ──────────────────────────────────────────

class SocialPublishIn(BaseModel):
    platform: str                 # 'youtube' | 'instagram' | 'facebook'
    video_url: str
    title: str = ''
    description: str = ''
    tags: list[str] = []
    schedule_at: Optional[str] = None


# ─── real social upload helpers ───────────────────────────────────────────────

async def _download_to_file(url: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            async with client.stream('GET', url) as r:
                if r.status_code != 200:
                    return None
                dest = str(UPLOAD_DIR / f'pub_{uuid.uuid4().hex[:10]}.mp4')
                with open(dest, 'wb') as f:
                    async for chunk in r.aiter_bytes(1024 * 64):
                        f.write(chunk)
                return dest
    except Exception as e:
        logger.warning('download failed: %s', e)
        return None


async def _upload_youtube(token: str, path: str, title: str, desc: str, tags: list) -> dict:
    meta = {
        'snippet': {'title': title or 'Getszy video', 'description': desc,
                    'tags': tags or [], 'categoryId': '22'},
        'status': {'privacyStatus': 'public'},
    }
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(
            'https://www.googleapis.com/upload/youtube/v3/videos',
            params={'uploadType': 'resumable', 'part': 'snippet,status,contentDetails'},
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json=meta)
        loc = r.headers.get('location')
        if not loc:
            return {'error': f'YouTube init failed: {r.status_code}'}
        with open(path, 'rb') as f:
            data = f.read()
        up = await client.put(loc, headers={'Content-Type': 'video/*'}, content=data)
        if up.status_code in (200, 201):
            return {'id': (up.json() or {}).get('id')}
        return {'error': f'YouTube upload failed: {up.status_code}'}


async def _upload_meta(token: str, ig_user_id: str, url: str, title: str, desc: str) -> dict:
    # Instagram Reels / Facebook video via Graph API (needs a publicly hosted url).
    async with httpx.AsyncClient(timeout=120) as client:
        c = await client.post(
            f'https://graph.facebook.com/v21.0/{ig_user_id}/media',
            params={'access_token': token, 'media_type': 'REELS',
                    'video_url': url, 'caption': f'{title}\n{desc}'})
        cid = (c.json() or {}).get('id')
        if not cid:
            return {'error': f'Meta container failed: {c.text[:200]}'}
        p = await client.post(
            f'https://graph.facebook.com/v21.0/{ig_user_id}/media_publish',
            params={'access_token': token, 'creation_id': cid})
        if p.status_code == 200:
            return {'id': (p.json() or {}).get('id')}
        return {'error': f'Meta publish failed: {p.text[:200]}'}


@router.post('/social-connect')
async def social_connect(body: dict, user=Depends(get_current_user)):
    """Store the user's OAuth tokens (from the client OAuth flow) so one-click
    publish can actually upload. body: {platform, access_token, ig_user_id?}."""
    platform = body.get('platform')
    token = body.get('access_token')
    if platform not in ('youtube', 'instagram', 'facebook') or not token:
        raise HTTPException(status_code=400, detail='platform + access_token required')
    await db.users.update_one(
        {'id': user['id']},
        {'$set': {f'social_tokens.{platform}': {
            'access_token': token,
            'ig_user_id': body.get('ig_user_id'),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }}})
    return {'ok': True, 'platform': platform}


@router.post('/social-publish')
async def social_publish(payload: SocialPublishIn, user=Depends(get_current_user)):
    if payload.platform not in ('youtube', 'instagram', 'facebook'):
        raise HTTPException(status_code=400, detail='Unsupported platform')
    tok = (await db.users.find_one({'id': user['id']}, {'_id': 0, f'social_tokens.{payload.platform}': 1}) or {})
    tok = (tok.get('social_tokens') or {}).get(payload.platform)
    if not tok or not tok.get('access_token'):
        return {
            'configured': False, 'platform': payload.platform,
            'message': f'{payload.platform.title()} not connected. Connect your account (Settings → Socials) first.',
        }
    ok, _, _ = await deduct(user['id'], 'social_publish', user=user)
    if not ok:
        raise HTTPException(status_code=402, detail='Not enough credits for publishing.')
    post_id = str(uuid.uuid4())
    await db.social_posts.insert_one({
        'id': post_id, 'user_id': user['id'], 'platform': payload.platform,
        'video_url': payload.video_url, 'title': payload.title,
        'description': payload.description, 'tags': payload.tags,
        'schedule_at': payload.schedule_at, 'status': 'publishing',
        'created_at': datetime.now(timezone.utc).isoformat(),
    })
    # Real upload (synchronous, best-effort; YouTube downloads then resumable PUT).
    result = {}
    if payload.platform == 'youtube':
        local = await _download_to_file(payload.video_url) or payload.video_url
        if os.path.exists(local):
            result = await _upload_youtube(tok['access_token'], local, payload.title, payload.description, payload.tags)
    else:
        result = await _upload_meta(tok['access_token'], tok.get('ig_user_id') or tok.get('page_id') or '', payload.video_url, payload.title, payload.description)
    status = 'published' if result.get('id') else 'failed'
    await db.social_posts.update_one({'id': post_id}, {'$set': {'status': status, 'result': result}})
    return {'configured': True, 'post_id': post_id, 'status': status, 'result': result}


# ─── 6. AI Influencer Agent (auto-reply) ───────────────────────────────────────

class InfluencerReplyIn(BaseModel):
    platform: str = 'instagram'
    comment_text: str = Field(..., min_length=2, max_length=500)
    context: str = ''


@router.post('/influencer-reply')
async def influencer_reply(payload: InfluencerReplyIn, user=Depends(get_current_user)):
    ok, _, _ = await deduct(user['id'], 'influencer_reply', user=user)
    if not ok:
        raise HTTPException(status_code=402, detail='Not enough credits for AI reply.')
    try:
        system = (
            'You are an Indian creator\'s AI community manager. Write a short, '
            'warm, on-brand reply in Hinglish (1-2 sentences). Be polite, add a '
            'relevant emoji, and never argue. No markdown, just the reply text.'
        )
        reply = await chat_completion(system, f'Comment: {payload.comment_text}\nContext: {payload.context}', temperature=0.8)
        await db.influencer_replies.insert_one({
            'user_id': user['id'], 'platform': payload.platform,
            'comment_text': payload.comment_text, 'reply': reply,
            'created_at': datetime.now(timezone.utc).isoformat(),
        })
        return {'reply': reply}
    except LLMServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))


# ─── Status ────────────────────────────────────────────────────────────────────

@router.get('/status')
async def status(user=Depends(get_current_user)):
    return {
        'providers': providers_status(),
        'social': {'youtube': YT_ENABLED, 'instagram': META_ENABLED, 'facebook': META_ENABLED},
        'free_tier_remaining': await free_tier_remaining(user['id']),
        'free_tier_monthly': 5,
    }


# ─── Read / poll results ─────────────────────────────────────────────────────

@router.get('/project/{project_id}')
async def get_project(project_id: str, user=Depends(get_current_user)):
    proj = await db.video_projects.find_one({'id': project_id, 'user_id': user['id']}, {'_id': 0})
    if not proj:
        raise HTTPException(status_code=404, detail='Project not found')
    return proj


@router.get('/job/{job_id}')
async def get_job(job_id: str, user=Depends(get_current_user)):
    job = await db.ai_jobs.find_one({'id': job_id, 'user_id': user['id']}, {'_id': 0})
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    return job
