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

# ─── 6. Local media utilities (ffmpeg) ────────────────────────────────────────

def _ffmpeg_available() -> bool:
    import shutil
    return bool(shutil.which('ffmpeg'))


async def extract_audio(video_path: str, out_path: Optional[str] = None) -> Optional[str]:
    """Extract mono 16kHz WAV from a video (for voice-clone / translation)."""
    if not _ffmpeg_available():
        return None
    out = out_path or str(AUDIO_DIR / f'{uuid.uuid4().hex[:10]}.wav')
    proc = await asyncio.create_subprocess_exec(
        'ffmpeg', '-y', '-i', video_path, '-vn', '-ac', '1', '-ar', '16000', out,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    return out if proc.returncode == 0 and os.path.exists(out) else None


async def watermark_video(video_path: str, text: str = 'Made with Getszy.com', out_path: Optional[str] = None) -> Optional[str]:
    """Burn a watermark into a video (free-tier organic marketing)."""
    if not _ffmpeg_available():
        return None
    out = out_path or str(AVATAR_DIR / f'{uuid.uuid4().hex[:10]}_wm.mp4')
    draw = f"drawtext=text='{text}':fontcolor=white:fontsize=24:box=1:boxcolor=black@0.4:x=(w-tw)/2:y=h-th-10"
    proc = await asyncio.create_subprocess_exec(
        'ffmpeg', '-y', '-i', video_path, '-vf', draw, '-c:a', 'copy', out,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    return out if proc.returncode == 0 and os.path.exists(out) else None


def _ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds - int(seconds)) * 100)
    return f'{h:d}:{m:02d}:{s:02d}.{cs:02d}'


def build_hormozi_ass(segments: list, brand: Optional[dict] = None) -> str:
    """Build an ASS subtitle script for Hormozi-style dynamic captions.

    segments: [{'start': s, 'end': e, 'text': str, 'highlight': [words]}]
    brand:    {'accent': '#00E5FF', 'font': 'Arial', 'logo': '/path'}
    """
    brand = brand or {}
    accent = brand.get('accent', '#00E5FF')
    # ASS colours are BGR hex: strip '#', reverse bytes.
    hexc = accent.lstrip('#')
    if len(hexc) == 6:
        bgr = f'&H{hexc[4:6]}{hexc[2:4]}{hexc[0:2]}&'
    else:
        bgr = '&H00E5FF&'
    font = brand.get('font', 'Arial')
    lines = [
        '[Script Info]', 'PlayResX: 1080', 'PlayResY: 1920', '',
        '[V4+ Styles]',
        'Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, Bold, '
        'Italic, Alignment, MarginV, BorderStyle, Outline',
        f'Style: Default,{font},72,{bgr},&H000000&,1,0,2,180,1,6',
        '', '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text',
    ]
    for seg in segments:
        start = _ass_time(float(seg.get('start', 0)))
        end = _ass_time(float(seg.get('end', 0)))
        text = (seg.get('text') or '').replace('\n', '\\N')
        hl = seg.get('highlight') or []
        for w in hl:
            text = text.replace(w, f'{{\\c&HFFFFFF&}}{w}{{\\c{bgr}}}')
        # pop-in animation per word chunk
        text = '{\\fad(80,80)\\an2}' + text
        lines.append(f'Dialogue: 0,{start},{end},Default,,0,0,0,,{text}')
    return '\n'.join(lines)


async def burn_hormozi_captions(video_path: str, segments: list, brand: Optional[dict] = None,
                                out_path: Optional[str] = None) -> Optional[str]:
    """Burn Hormozi-style dynamic captions into a video (FFmpeg + ASS)."""
    if not _ffmpeg_available():
        return None
    out = out_path or str(AVATAR_DIR / f'{uuid.uuid4().hex[:10]}_caps.mp4')
    ass_path = str(AVATAR_DIR / f'{uuid.uuid4().hex[:10]}.ass')
    try:
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write(build_hormozi_ass(segments, brand))
        cmd = ['ffmpeg', '-y', '-i', video_path, '-vf', f"ass={ass_path}", '-c:a', 'copy', out]
        if brand and brand.get('logo'):
            cmd = ['ffmpeg', '-y', '-i', video_path, '-i', brand['logo'],
                   '-filter_complex', f"[0:v]ass={ass_path}[v];[v][1:v]overlay=W-w-20:H-h-20",
                   '-c:a', 'copy', out]
        proc = await asyncio.create_subprocess_exec(*cmd,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await proc.wait()
        return out if proc.returncode == 0 and os.path.exists(out) else None
    except Exception as e:
        logger.warning('burn_hormozi_captions failed: %s', e)
        return None
    finally:
        if os.path.exists(ass_path):
            os.remove(ass_path)


async def concat_videos(paths: list, out_path: Optional[str] = None) -> Optional[str]:
    """Concatenate mp4 clips into one video (FFmpeg concat demuxer)."""
    if not _ffmpeg_available() or not paths:
        return None
    out = out_path or str(CLIP_DIR / f'{uuid.uuid4().hex[:10]}_final.mp4')
    list_path = str(CLIP_DIR / f'{uuid.uuid4().hex[:10]}.txt')
    try:
        with open(list_path, 'w', encoding='utf-8') as f:
            for p in paths:
                f.write(f"file '{p}'\n")
        proc = await asyncio.create_subprocess_exec(
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_path,
            '-c', 'copy', out,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await proc.wait()
        return out if proc.returncode == 0 and os.path.exists(out) else None
    except Exception as e:
        logger.warning('concat_videos failed: %s', e)
        return None
    finally:
        if os.path.exists(list_path):
            os.remove(list_path)


async def lip_sync_video(video_path: str, audio_path: str, out_path: Optional[str] = None) -> Optional[str]:
    """Lip-sync a video to new audio via the configured GPU provider.

    Resolution order (repo scaling path, see creator/providers.py):
      1. Self-hosted GPU box (GPU_HOST) — POST multipart {video, audio} to
         `{GPU_HOST}/lipsync`; expects JSON {"video_url": "..."} back. We
         download the result locally.
      2. fal.ai Wav2Lip/LivePortrait (FAL_KEY) — JSON {video_url, audio_url}.
    Returns the local output path, or None if no GPU provider is configured
    (graceful — caller falls back to plain audio dubbing).
    """
    import creator.providers as cp
    if not (cp.GPU_HOST or cp.FAL_KEY):
        return None
    out = out_path or str(AVATAR_DIR / f'{uuid.uuid4().hex[:10]}_sync.mp4')
    try:
        if cp.GPU_HOST:
            async with httpx.AsyncClient(timeout=600) as client:
                resp = await client.post(
                    f'{cp.GPU_HOST.rstrip("/")}/lipsync',
                    files={'video': open(video_path, 'rb'), 'audio': open(audio_path, 'rb')},
                )
                if resp.status_code != 200:
                    logger.warning('GPU lipsync returned %s', resp.status_code)
                    return None
                url = (resp.json() or {}).get('video_url') or (resp.json() or {}).get('output')
                if not url:
                    return None
                dl = await client.get(url)
                if dl.status_code == 200:
                    out_path_w = out
                    open(out_path_w, 'wb').write(dl.content)
                    return out_path_w
                return None
        if cp.FAL_KEY:
            # fal expects public URLs; callers should host the inputs first.
            logger.warning('FAL lip-sync needs public input URLs; skipping')
            return None
    except Exception as e:
        logger.warning('lip_sync_video failed: %s', e)
        return None
    return None


def providers_status() -> dict:
    """Return which providers are enabled (for /api/status endpoint)."""
    return {
        'flux_images':    bool(HF_TOKEN),
        'xtts_voice':     bool(HF_TOKEN),
        'sadtalker':      bool(HF_TOKEN),
        'cogvideox':      bool(HF_TOKEN),
        'openrouter':     bool(OPENROUTER_KEY),
        'pollinations':   True,   # always available
        'ffmpeg':         _ffmpeg_available(),
    }
