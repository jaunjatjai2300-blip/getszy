"""Voice generation using Edge-TTS (Microsoft) — free, 400+ voices."""
import os
import asyncio
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger('getszy.voice')

MEDIA_DIR = Path(__file__).parent / 'media' / 'voice'
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# Available voices (Indian + popular)
VOICES = {
    'hindi-female': 'hi-IN-SwaraNeural',
    'hindi-male': 'hi-IN-MadhurNeural',
    'english-female': 'en-US-JennyNeural',
    'english-male': 'en-US-GuyNeural',
    'english-indian-female': 'en-IN-NeerjaNeural',
    'english-indian-male': 'en-IN-PrabhatNeural',
    'tamil-female': 'ta-IN-PallaviNeural',
    'telugu-female': 'te-IN-ShrutiNeural',
    'bengali-female': 'bn-IN-TanishaaNeural',
    'marathi-female': 'mr-IN-AarohiNeural',
    'gujarati-female': 'gu-IN-DhwaniNeural',
    'punjabi-female': 'pa-IN-GurpreetNeural',
}


async def generate_voice(
    text: str,
    voice: str = 'english-indian-female',
    rate: str = '+0%',
    volume: str = '+0%',
    pitch: str = '+0Hz',
) -> dict:
    """Generate speech from text. Returns {file_path, duration_estimate, voice}."""
    import edge_tts

    voice_id = VOICES.get(voice, voice)
    filename = f'{hash(text) & 0xFFFFFFFF:08x}_{voice_id}.mp3'
    filepath = MEDIA_DIR / filename

    if filepath.exists():
        return {'file_path': str(filepath), 'voice': voice_id}

    try:
        communicate = edge_tts.Communicate(text, voice_id, rate=rate, volume=volume, pitch=pitch)
        await communicate.save(str(filepath))
        # Estimate duration (rough: 150 words per minute)
        word_count = len(text.split())
        duration_sec = max(1, int(word_count / 2.5))
        logger.info(f'Voice generated: {filename} ({duration_sec}s)')
        return {
            'file_path': str(filepath),
            'filename': filename,
            'voice': voice_id,
            'duration_estimate': duration_sec,
        }
    except Exception as e:
        logger.error(f'Voice generation failed: {e}')
        return {'file_path': '', 'error': str(e)}


async def generate_video_voiceover(
    script: list[dict],
    voice: str = 'english-indian-female',
) -> dict:
    """Generate voiceover for video scenes.
    script: [{'text': '...', 'pause_after': 0.5}, ...]
    Returns {segments: [{text, file_path, duration}]}
    """
    segments = []
    for i, scene in enumerate(script):
        text = scene.get('text', '')
        if not text:
            continue
        result = await generate_voice(text, voice=voice)
        segments.append({
            'index': i,
            'text': text,
            'file_path': result.get('file_path', ''),
            'duration': result.get('duration_estimate', 0),
            'pause_after': scene.get('pause_after', 0.5),
        })
    return {'segments': segments}


async def list_voices(language: str = None) -> list:
    """List available voices."""
    if language:
        return [
            {'key': k, 'voice_id': v}
            for k, v in VOICES.items()
            if language.lower() in k.lower() or language.lower() in v.lower()
        ]
    return [{'key': k, 'voice_id': v} for k, v in VOICES.items()]
