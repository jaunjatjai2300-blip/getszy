"""
Open Source AI Providers — ALL FREE via HuggingFace

Tools integrated:
  1. FLUX.1-schnell  → HD Images (replaces Pollinations, 10x quality)
  2. Coqui XTTS-v2  → Voice Cloning (user uploads 30s audio)
  3. SadTalker       → AI Avatar (photo → talking head video)
  4. CogVideoX-5b    → AI Video Clips (text → cinematic video)
  5. OpenRouter      → 92 free LLMs (fallback after Groq/Gemini)

Env vars:
  HF_TOKEN        — huggingface.co/settings/tokens (free account)
  OPENROUTER_KEY  — openrouter.ai (free account)
"""
import asyncio
import base64
import httpx
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger('getszy.ai_providers')

HF_TOKEN       = os.environ.get('HF_TOKEN', '').strip()
OPENROUTER_KEY = os.environ.get('OPENROUTER_KEY', '').strip()

CACHE_DIR      = Path(__file__).parent.parent / 'media_cache'
IMG_DIR        = CACHE_DIR / 'images'
AUDIO_DIR      = CACHE_DIR / 'audio'
AVATAR_DIR     = CACHE_DIR / 'avatars'
CLIP_DIR       = CACHE_DIR / 'clips'

for _d in [IMG_DIR, AUDIO_DIR, AVATAR_DIR, CLIP_DIR]:
    _d.mkdir(parents=True, exist_ok=True)


# ─── 1. FLUX.1-schnell — HD Image Generation ─────────────────────────────────

_FLUX_URL  = 'https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell'
_HF_HDR    = lambda: {'Authorization': f'Bearer {HF_TOKEN}'} if HF_TOKEN else {}


async def flux_image(prompt: str, seed: int = 42) -> Optional[str]:
    """FLUX.1-schnell via HuggingFace Inference API. Returns local image path or None."""
    if not HF_TOKEN:
        logger.info('HF_TOKEN not set — skipping FLUX')
        return None
    payload = {'inputs': prompt, 'parameters': {'seed': seed, 'num_inference_steps': 4}}
    try:
        async with httpx.AsyncClient(timeout=60.0) as c:
            r = await c.post(_FLUX_URL, headers=_HF_HDR(), json=payload)
            if r.status_code == 200 and 'image' in r.headers.get('content-type', ''):
                path = IMG_DIR / f'flux_{uuid.uuid4().hex[:10]}.jpg'
                path.write_bytes(r.content)
                logger.info('FLUX image ok: %s', path.name)
                return str(path)
            if r.status_code == 503:
                # Model loading — wait 15s and retry once
                await asyncio.sleep(15)
                r2 = await c.post(_FLUX_URL, headers=_HF_HDR(), json=payload)
                if r2.status_code == 200:
                    path = IMG_DIR / f'flux_{uuid.uuid4().hex[:10]}.jpg'
                    path.write_bytes(r2.content)
                    return str(path)
            logger.warning('FLUX status=%s', r.status_code)
    except Exception as exc:
        logger.warning('FLUX error: %s', exc)
    return None


async def pollinations_image(prompt: str, seed: int = 42) -> Optional[str]:
    """Fallback: Pollinations (no key, unlimited, medium quality)."""
    import urllib.parse
    url = f'https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=768&height=1344&nologo=true&seed={seed}'
    try:
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as c:
            r = await c.get(url)
            if r.status_code == 200 and len(r.content) > 5000:
                path = IMG_DIR / f'poll_{uuid.uuid4().hex[:10]}.jpg'
                path.write_bytes(r.content)
                return str(path)
    except Exception as exc:
        logger.warning('Pollinations error: %s', exc)
    return None


async def fetch_image(prompt: str, seed: int = 42) -> Optional[str]:
    """Smart image fetch: FLUX (HD) first → Pollinations (fallback)."""
    if HF_TOKEN:
        result = await flux_image(prompt, seed)
        if result:
            return result
    # Retry Pollinations with different seed on failure
    result = await pollinations_image(prompt, seed)
    if not result:
        result = await pollinations_image(prompt, seed + 7)
    return result


# ─── 2. Coqui XTTS-v2 — Voice Cloning ────────────────────────────────────────

_XTTS_API = 'https://coqui-xtts.hf.space/run/predict'


async def xtts_clone_voice(text: str, speaker_wav_path: str, language: str = 'hi') -> Optional[str]:
    """Clone voice using Coqui XTTS-v2 (HuggingFace Space).
    speaker_wav_path: path to user reference audio (10-30 seconds).
    Returns synthesized audio WAV path or None."""
    try:
        ref_b64 = 'data:audio/wav;base64,' + base64.b64encode(Path(speaker_wav_path).read_bytes()).decode()
        async with httpx.AsyncClient(timeout=120.0) as c:
            r = await c.post(_XTTS_API, json={
                'fn_index': 0,
                'data': [text, ref_b64, ref_b64, language, True, True, False, 0]
            })
            if r.status_code == 200:
                data = r.json().get('data', [])
                if data and isinstance(data[0], dict) and data[0].get('data'):
                    raw = data[0]['data'].split(',')[-1]
                    path = AUDIO_DIR / f'xtts_{uuid.uuid4().hex[:10]}.wav'
                    path.write_bytes(base64.b64decode(raw))
                    logger.info('XTTS voice clone ok: %s', path.name)
                    return str(path)
        logger.warning('XTTS returned no audio, status=%s', r.status_code)
    except Exception as exc:
        logger.warning('XTTS error: %s', exc)
    return None


# ─── 3. SadTalker — AI Talking Avatar ────────────────────────────────────────

_SADTALKER_API = 'https://vinthony-sadtalker.hf.space/run/predict'


async def sadtalker_avatar(portrait_path: str, audio_path: str) -> Optional[str]:
    """Generate talking avatar video from portrait photo + audio (SadTalker HF Space).
    Returns output MP4 path or None."""
    try:
        img_b64  = 'data:image/jpeg;base64,' + base64.b64encode(Path(portrait_path).read_bytes()).decode()
        audio_b64 = 'data:audio/wav;base64,' + base64.b64encode(Path(audio_path).read_bytes()).decode()
        async with httpx.AsyncClient(timeout=180.0) as c:
            r = await c.post(_SADTALKER_API, json={
                'fn_index': 0,
                'data': [img_b64, audio_b64, 256, False, 'crop', False, 'facevid2vid']
            })
            if r.status_code == 200:
                data = r.json().get('data', [])
                if data and isinstance(data[0], dict) and data[0].get('data'):
                    raw = data[0]['data'].split(',')[-1]
                    path = AVATAR_DIR / f'avatar_{uuid.uuid4().hex[:10]}.mp4'
                    path.write_bytes(base64.b64decode(raw))
                    logger.info('SadTalker avatar ok: %s', path.name)
                    return str(path)
        logger.warning('SadTalker returned no video, status=%s', r.status_code)
    except Exception as exc:
        logger.warning('SadTalker error: %s', exc)
    return None


# ─── 4. CogVideoX-5b — AI Video Clip Generation ──────────────────────────────

_COGVIDEO_API = 'https://thudm-cogvideox.hf.space/run/predict'


async def cogvideo_clip(prompt: str, seed: int = 42, duration: int = 6) -> Optional[str]:
    """Generate cinematic AI video clip from text prompt (CogVideoX-5b HF Space).
    Returns MP4 path or None. Note: can take 2-5 minutes."""
    try:
        async with httpx.AsyncClient(timeout=360.0) as c:
            r = await c.post(_COGVIDEO_API, json={
                'fn_index': 0,
                'data': [prompt, seed, duration, 1, 'cogvideox-5b']
            })
            if r.status_code == 200:
                data = r.json().get('data', [])
                if data and isinstance(data[0], dict) and data[0].get('data'):
                    raw = data[0]['data'].split(',')[-1]
                    path = CLIP_DIR / f'cogvideo_{uuid.uuid4().hex[:10]}.mp4'
                    path.write_bytes(base64.b64decode(raw))
                    logger.info('CogVideoX clip ok: %s', path.name)
                    return str(path)
        logger.warning('CogVideoX returned no video, status=%s', r.status_code)
    except Exception as exc:
        logger.warning('CogVideoX error: %s', exc)
    return None


# ─── 5. OpenRouter — 92 Free LLMs ────────────────────────────────────────────

_OPENROUTER_FREE_MODELS = [
    'meta-llama/llama-3.1-8b-instruct:free',
    'mistralai/mistral-7b-instruct:free',
    'google/gemma-2-9b-it:free',
    'qwen/qwen-2-7b-instruct:free',
    'microsoft/phi-3-mini-128k-instruct:free',
]


async def openrouter_chat(system: str, user_msg: str, temperature: float = 0.7) -> Optional[str]:
    """Call OpenRouter free models (92 available). Returns text or None."""
    if not OPENROUTER_KEY:
        return None
    for model in _OPENROUTER_FREE_MODELS:
        try:
            async with httpx.AsyncClient(timeout=60.0) as c:
                r = await c.post(
                    'https://openrouter.ai/api/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {OPENROUTER_KEY}',
                        'HTTP-Referer': 'https://getszy.com',
                        'X-Title': 'Getszy',
                    },
                    json={
                        'model': model,
                        'messages': [
                            {'role': 'system', 'content': system},
                            {'role': 'user', 'content': user_msg},
                        ],
                        'temperature': temperature,
                    },
                )
                if r.status_code == 200:
                    text = r.json()['choices'][0]['message']['content']
                    logger.info('OpenRouter ok model=%s', model)
                    return text
                logger.warning('OpenRouter model=%s status=%s', model, r.status_code)
        except Exception as exc:
            logger.warning('OpenRouter model=%s error: %s', model, exc)
    return None


# ─── Status / health check ────────────────────────────────────────────────────

def providers_status() -> dict:
    """Return which providers are enabled (for /api/status endpoint)."""
    return {
        'flux_images':    bool(HF_TOKEN),
        'xtts_voice':     bool(HF_TOKEN),
        'sadtalker':      bool(HF_TOKEN),
        'cogvideox':      bool(HF_TOKEN),
        'openrouter':     bool(OPENROUTER_KEY),
        'pollinations':   True,   # always available
    }
