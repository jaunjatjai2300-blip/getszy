"""Whisper STT — OpenAI Whisper API + HuggingFace fallback."""
import os
import httpx
import tempfile
import logging

logger = logging.getLogger('getszy.whisper')

OPENAI_KEY = os.environ.get('OPENAI_API_KEY', '').strip()
HF_TOKEN = os.environ.get('HF_TOKEN', '').strip()


async def transcribe_openai(audio_bytes: bytes, filename: str = 'audio.wav') -> dict:
    if not OPENAI_KEY:
        return {'error': 'OPENAI_API_KEY not set'}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                'https://api.openai.com/v1/audio/transcriptions',
                headers={'Authorization': f'Bearer {OPENAI_KEY}'},
                files={'file': (filename, audio_bytes, 'audio/wav')},
                data={'model': 'whisper-1', 'response_format': 'text'}
            )
            if resp.status_code == 200:
                return {'text': resp.text.strip(), 'provider': 'openai'}
            return {'error': f'OpenAI returned {resp.status_code}'}
    except Exception as e:
        return {'error': str(e)}


async def transcribe_hf(audio_bytes: bytes, filename: str = 'audio.wav') -> dict:
    if not HF_TOKEN:
        return {'error': 'HF_TOKEN not set'}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                'https://api-inference.huggingface.co/models/openai/whisper-large-v3',
                headers={'Authorization': f'Bearer {HF_TOKEN}'},
                files={'file': (filename, audio_bytes, 'audio/wav')}
            )
            if resp.status_code == 200:
                data = resp.json()
                return {'text': data.get('text', str(data)), 'provider': 'huggingface'}
            return {'error': f'HF returned {resp.status_code}'}
    except Exception as e:
        return {'error': str(e)}


async def transcribe(audio_bytes: bytes, filename: str = 'audio.wav') -> dict:
    result = await transcribe_openai(audio_bytes, filename)
    if 'text' in result:
        return result
    logger.warning('OpenAI STT failed, trying HuggingFace')
    return await transcribe_hf(audio_bytes, filename)
