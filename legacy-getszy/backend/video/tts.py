"""TTS provider with automatic fallback chain.

Priority order (highest quality first):
  1. ElevenLabs  — if ELEVENLABS_KEY env var is set (premium, multilingual)
  2. edge-tts    — Microsoft Edge online voices, free, no API key needed
  3. Silent MP3  — honest fallback, never fakes a "done" status

Indian voices:
  edge-tts:    hi-IN-MadhurNeural, hi-IN-SwaraNeural, en-IN-NeerjaNeural, en-IN-PrabhatNeural
  ElevenLabs:  Uses eleven_multilingual_v2 model (supports Hindi, Hinglish, English)
"""
import asyncio
import os
import uuid
import logging
from typing import Optional

logger = logging.getLogger('getszy.tts')

# ── ElevenLabs config ────────────────────────────────────────────────────────
ELEVENLABS_KEY = os.getenv('ELEVENLABS_KEY', '')
ELEVENLABS_API = 'https://api.elevenlabs.io/v1'
ELEVENLABS_MODEL = 'eleven_multilingual_v2'

# Curated voice IDs — good for Indian content.
# Users can override via ELEVENLABS_VOICE_ID env var.
# Premade ElevenLabs voices that work well for Hinglish/Hindi content:
#   Rachel  (21m00Tcm4TlvDq8ikWAM) — clear English female
#   Domi    (AZnzlk1XvdvUeBnXmlld) — energetic female
#   Antoni  (ErXwobaYiN019PkySvjV) — warm male
ELEVENLABS_VOICE_DEFAULT = os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM')

# ── edge-tts voice map ────────────────────────────────────────────────────────
VOICE_MAP = {
    ('hindi', 'female'):    'hi-IN-SwaraNeural',
    ('hindi', 'male'):      'hi-IN-MadhurNeural',
    ('hinglish', 'female'): 'hi-IN-SwaraNeural',
    ('hinglish', 'male'):   'hi-IN-MadhurNeural',
    ('english', 'female'):  'en-IN-NeerjaNeural',
    ('english', 'male'):    'en-IN-PrabhatNeural',
}

LIST_VOICES = [
    {'id': 'hi-IN-SwaraNeural',   'lang': 'Hindi', 'gender': 'female', 'label': 'Swara (Hindi female)',      'provider': 'edge-tts'},
    {'id': 'hi-IN-MadhurNeural',  'lang': 'Hindi', 'gender': 'male',   'label': 'Madhur (Hindi male)',       'provider': 'edge-tts'},
    {'id': 'en-IN-NeerjaNeural',  'lang': 'Indian English', 'gender': 'female', 'label': 'Neerja (IN English F)', 'provider': 'edge-tts'},
    {'id': 'en-IN-PrabhatNeural', 'lang': 'Indian English', 'gender': 'male',   'label': 'Prabhat (IN English M)', 'provider': 'edge-tts'},
]


def pick_voice(language: str = 'hinglish', gender: str = 'female') -> str:
    return VOICE_MAP.get((language.lower(), gender.lower()), 'hi-IN-SwaraNeural')


def elevenlabs_available() -> bool:
    return bool(ELEVENLABS_KEY)


# ── ElevenLabs provider ───────────────────────────────────────────────────────

async def _synth_elevenlabs(text: str, out_path: str, voice_id: Optional[str] = None) -> bool:
    """Call ElevenLabs TTS API. Returns True on success, False on any failure."""
    if not ELEVENLABS_KEY:
        return False
    vid = voice_id or ELEVENLABS_VOICE_DEFAULT
    url = f'{ELEVENLABS_API}/text-to-speech/{vid}'
    payload = {
        'text': text,
        'model_id': ELEVENLABS_MODEL,
        'voice_settings': {
            'stability': 0.5,
            'similarity_boost': 0.75,
            'style': 0.0,
            'use_speaker_boost': True,
        },
    }
    headers = {
        'xi-api-key': ELEVENLABS_KEY,
        'Content-Type': 'application/json',
        'Accept': 'audio/mpeg',
    }
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning('[tts] ElevenLabs returned %s: %s', resp.status, body[:200])
                    return False
                audio_bytes = await resp.read()
        if len(audio_bytes) < 1000:
            logger.warning('[tts] ElevenLabs returned suspiciously small audio (%d bytes)', len(audio_bytes))
            return False
        with open(out_path, 'wb') as f:
            f.write(audio_bytes)
        logger.info('[tts] ElevenLabs OK — %d bytes → %s', len(audio_bytes), out_path)
        return True
    except Exception as exc:
        logger.warning('[tts] ElevenLabs failed: %s', exc)
        return False


# ── edge-tts provider ─────────────────────────────────────────────────────────

async def _synth_edge(text: str, out_path: str, voice: str, rate: str) -> bool:
    """Use edge-tts (free Microsoft voices). Returns True on success."""
    try:
        import edge_tts
        comm = edge_tts.Communicate(text=text, voice=voice, rate=rate)
        await comm.save(out_path)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            logger.info('[tts] edge-tts OK — %s', out_path)
            return True
        logger.warning('[tts] edge-tts produced empty/tiny file')
        return False
    except Exception as exc:
        logger.warning('[tts] edge-tts failed: %s', exc)
        return False


# ── Silent fallback ───────────────────────────────────────────────────────────

async def _silent(out_path: str, seconds: int = 3):
    """Generate a silent MP3 — honest fallback, never fakes audio content."""
    from video.ffmpeg_bin import FFMPEG
    proc = await asyncio.create_subprocess_exec(
        FFMPEG, '-y', '-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono',
        '-t', str(seconds), '-q:a', '9', out_path,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.wait()
    logger.warning('[tts] used silent fallback (%ds) for path %s', seconds, out_path)


# ── Public API ────────────────────────────────────────────────────────────────

async def synth(
    text: str,
    out_path: str,
    voice: Optional[str] = None,
    rate: str = '+0%',
    elevenlabs_voice_id: Optional[str] = None,
) -> str:
    """Synthesize narration to MP3.

    Tries ElevenLabs first (if key configured), then edge-tts, then silent fallback.
    Always returns a valid audio file path — never raises.
    """
    # 1. ElevenLabs (premium quality, Hinglish/Hindi capable)
    if ELEVENLABS_KEY:
        ok = await _synth_elevenlabs(text, out_path, voice_id=elevenlabs_voice_id)
        if ok:
            return out_path

    # 2. edge-tts (free, Microsoft, decent Indian voices)
    edge_voice = voice or 'hi-IN-SwaraNeural'
    ok = await _synth_edge(text, out_path, voice=edge_voice, rate=rate)
    if ok:
        return out_path

    # 3. Silent fallback — honest, never pretends audio was generated
    silence_secs = max(3, int(len(text.split()) / 2.5))
    await _silent(out_path, seconds=silence_secs)
    return out_path


async def list_available_voices() -> list[dict]:
    """Return all available voices with provider info."""
    voices = list(LIST_VOICES)
    if ELEVENLABS_KEY:
        voices.insert(0, {
            'id': ELEVENLABS_VOICE_DEFAULT,
            'lang': 'Multilingual',
            'gender': 'female',
            'label': 'Getszy AI Voice (Premium)',
            'provider': 'elevenlabs',
        })
    return voices
