"""Edge-TTS voice generation — 400+ voices, 12 languages, completely free."""
import os
import tempfile
import logging

logger = logging.getLogger('getszy.voice_gen')

DEFAULT_VOICE = os.environ.get('TTS_VOICE', 'en-US-AriaNeural')
DEFAULT_RATE = os.environ.get('TTS_RATE', '+0%')
DEFAULT_PITCH = os.environ.get('TTS_PITCH', '+0Hz')


async def list_voices():
    try:
        import edge_tts
        voices = await edge_tts.list_voices()
        return [{'id': v['ShortName'], 'name': v['FriendlyName'], 'locale': v['Locale'], 'gender': v['Gender']} for v in voices]
    except Exception as e:
        return [{'error': str(e)}]


async def generate_speech(text: str, voice: str = None, rate: str = None, pitch: str = None) -> dict:
    voice = voice or DEFAULT_VOICE
    rate = rate or DEFAULT_RATE
    pitch = pitch or DEFAULT_PITCH
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        tmp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        tmp.close()
        await communicate.save(tmp.name)
        import base64
        with open(tmp.name, 'rb') as f:
            audio_b64 = base64.b64encode(f.read()).decode()
        os.unlink(tmp.name)
        return {'audio': audio_b64, 'format': 'mp3', 'voice': voice, 'provider': 'edge-tts'}
    except Exception as e:
        logger.error(f'Edge-TTS error: {e}')
        return {'error': str(e)}


async def generate_speech_stream(text: str, voice: str = None, rate: str = None):
    voice = voice or DEFAULT_VOICE
    rate = rate or DEFAULT_RATE
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                yield chunk['data']
    except Exception as e:
        logger.error(f'Edge-TTS stream error: {e}')
        yield b''
