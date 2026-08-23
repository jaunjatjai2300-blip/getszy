"""Free media-model registry + wrappers for the SamurAIGPT media suite.

This is the "model integrations" layer. It is intentionally FREE-ONLY:
- Text-to-Image: HuggingFace Inference free tier (FLUX.1-schnell, SDXL, and any
  HF model id you add) + Pollinations (no key).
- Text-to-Speech: Edge-TTS (free, no key).
- Speech-to-Text: Whisper via HF / OpenAI fallback (we only use the free HF path
  by default; OPENAI_API_KEY is optional and off by default).
- Text/Image-to-Video: Pollinations (free) + HF free video models when available.

Paid-only platforms (Midjourney / Runway / Kling / Luma) are NOT registered. The
registry is pluggable: add an HF repo id to ``FREE_MODELS`` to integrate it — no
code changes elsewhere. This is how the "200+ integrations" goal is reached
safely: every entry is a free, keyless-or-HF-token model.
"""
import os
import httpx
import logging

logger = logging.getLogger('getszy.media_models')

HF_TOKEN = os.environ.get('HF_TOKEN', '').strip()
POLLINATIONS_URL = 'https://image.pollinations.ai/prompt/{prompt}'


# Curated FREE model catalog. ``hf`` entries hit HF Inference; ``pollinations``
# needs no key. Extend freely — each new id is a new integration.
FREE_MODELS = {
    'image': [
        {'id': 'FLUX.1-schnell', 'label': 'FLUX.1-schnell (HF)', 'hf': 'black-forest-labs/FLUX.1-schnell', 'free': True},
        {'id': 'SDXL', 'label': 'Stable Diffusion XL (HF)', 'hf': 'stabilityai/stable-diffusion-xl-base-1.0', 'free': True},
        {'id': 'pollinations', 'label': 'Pollinations', 'hf': None, 'free': True},
    ],
    'video': [
        {'id': 'pollinations', 'label': 'Pollinations video', 'hf': None, 'free': True},
    ],
    'tts': [
        {'id': 'edge-tts', 'label': 'Edge-TTS (free)', 'hf': None, 'free': True},
    ],
    'stt': [
        {'id': 'whisper', 'label': 'Whisper (HF free)', 'hf': 'openai/whisper-large-v3', 'free': True},
    ],
}


def list_free_models() -> dict:
    return {cap: [m for m in models if m.get('free')] for cap, models in FREE_MODELS.items()}


async def generate_image_model(prompt: str, model_id: str = None, width: int = 1024, height: int = 1024) -> dict:
    """Generate an image using a specific free model id (HF repo or pollinations)."""
    model = None
    for m in FREE_MODELS['image']:
        if m['id'] == model_id:
            model = m
            break
    if model and model.get('hf'):
        if not HF_TOKEN:
            return {'error': 'HF_TOKEN not set'}
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(
                    f'https://api-inference.huggingface.co/models/{model["hf"]}',
                    headers={'Authorization': f'Bearer {HF_TOKEN}'},
                    json={'inputs': prompt, 'parameters': {'width': width, 'height': height}},
                )
                if resp.status_code == 200 and 'image' in resp.headers.get('content-type', ''):
                    import base64
                    return {'image': base64.b64encode(resp.content).decode(), 'provider': 'huggingface', 'model': model_id}
                return {'error': f'HF {model_id} returned {resp.status_code}', 'detail': resp.text[:200]}
        except Exception as e:  # noqa: BLE001
            return {'error': str(e)}
    # Default / pollinations path
    from image_gen import generate_image
    return await generate_image(prompt, width, height)


async def text_to_speech(text: str, voice: str = None, rate: str = None, pitch: str = None) -> dict:
    from voice_gen import generate_speech
    return await generate_speech(text, voice, rate, pitch)


async def transcribe(audio_bytes: bytes, filename: str = 'audio.wav') -> dict:
    from whisper_stt import transcribe as whisper_transcribe
    return await whisper_transcribe(audio_bytes, filename)
