"""Voice transcription using OpenAI Whisper API + free alternatives."""
import os
import httpx
import logging
from pathlib import Path

logger = logging.getLogger('getszy.whisper')

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
WHISPER_MODEL = 'whisper-1'
HF_API_KEY = os.environ.get('HF_API_KEY', '')


async def transcribe_audio(
    file_path: str = None,
    file_bytes: bytes = None,
    filename: str = 'audio.wav',
    language: str = None,
) -> dict:
    """Transcribe audio to text. Returns {text, language, duration}."""
    if file_bytes is None and file_path:
        with open(file_path, 'rb') as f:
            file_bytes = f.read()

    if not file_bytes:
        return {'text': '', 'error': 'No audio data'}

    # Try OpenAI Whisper first
    if OPENAI_API_KEY:
        try:
            return await _openai_whisper(file_bytes, filename, language)
        except Exception as e:
            logger.warning(f'OpenAI Whisper failed: {e}')

    # Fallback to HuggingFace Inference
    if HF_API_KEY:
        try:
            return await _hf_whisper(file_bytes, filename, language)
        except Exception as e:
            logger.warning(f'HF Whisper failed: {e}')

    return {'text': '', 'error': 'No transcription provider available. Add OPENAI_API_KEY or HF_API_KEY.'}


async def _openai_whisper(file_bytes: bytes, filename: str, language: str = None) -> dict:
    async with httpx.AsyncClient(timeout=120) as client:
        form_data = {
            'file': (filename, file_bytes, 'audio/wav'),
            'model': (None, WHISPER_MODEL),
        }
        if language:
            form_data['language'] = (None, language)
        resp = await client.post(
            'https://api.openai.com/v1/audio/transcriptions',
            headers={'Authorization': f'Bearer {OPENAI_API_KEY}'},
            files=form_data,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            'text': data.get('text', ''),
            'language': data.get('language', language or 'unknown'),
        }


async def _hf_whisper(file_bytes: bytes, filename: str, language: str = None) -> dict:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            'https://api-inference.huggingface.co/models/openai/whisper-large-v3',
            headers={'Authorization': f'Bearer {HF_API_KEY}'},
            files={'file': (filename, file_bytes, 'audio/wav')},
            data={'parameters': {'language': language}} if language else {},
        )
        resp.raise_for_status()
        data = resp.json()
        text = data.get('text', '') if isinstance(data, dict) else str(data)
        return {'text': text, 'language': language or 'unknown'}


async def transcribe_from_url(audio_url: str, language: str = None) -> dict:
    """Download audio from URL and transcribe."""
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.get(audio_url)
        resp.raise_for_status()
        return await transcribe_audio(
            file_bytes=resp.content,
            filename=audio_url.split('/')[-1] or 'audio.wav',
            language=language,
        )
