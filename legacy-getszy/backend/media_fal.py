"""Optional Fal.ai provider for the media suite.

Fal.ai is an OPTIONAL external provider, not a dependency. It is only advertised
or used when ``FAL_KEY`` is present in the environment. The key is read from the
environment inside request handling and is NEVER:

- sent to the browser / frontend
- stored in generated HTML, logs, or error messages
- returned in any API response

If Fal.ai is unavailable (no key, or import failure), the free providers
(Pollinations / HF / Edge-TTS / Whisper) continue to work unchanged. Selection is
capability-based: image generation may fall back to the free registry.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger('getszy.media_fal')

try:
    import fal_client  # type: ignore
    _FAL_SDK_AVAILABLE = True
except Exception:  # noqa: BLE001
    fal_client = None
    _FAL_SDK_AVAILABLE = False


def fal_configured() -> bool:
    return bool(os.environ.get('FAL_KEY')) and _FAL_SDK_AVAILABLE


# Static set of Fal.ai model ids (recognized regardless of whether the key is
# configured, so an unconfigured request can return a clean error instead of
# silently falling back to a different provider).
FAL_MODEL_IDS = {'fal/flux-schnell', 'fal/flux-dev'}


def fal_image_models() -> list:
    """Return Fal.ai image models ONLY when FAL_KEY is configured."""
    if not fal_configured():
        return []
    return [
        {
            'id': 'fal/flux-schnell',
            'label': 'Fal.ai FLUX Schnell',
            'provider': 'fal.ai',
            'free': False,
            'optional': True,
            'capability': 'image',
            'note': 'optional external provider (FAL_KEY)',
        },
        {
            'id': 'fal/flux-dev',
            'label': 'Fal.ai FLUX Dev',
            'provider': 'fal.ai',
            'free': False,
            'optional': True,
            'capability': 'image',
            'note': 'optional external provider (FAL_KEY)',
        },
    ]


def fal_model_ids() -> set:
    return set(FAL_MODEL_IDS)


async def generate_image_fal(prompt: str, width: int = 1024, height: int = 1024,
                              model_id: str = 'fal/flux-schnell') -> dict:
    """Generate an image via Fal.ai. Reads FAL_KEY from env (never exposed).

    Returns a normal result dict or an ``{'error': ...}`` dict on any failure so
    callers can fall back to the free registry — never raises to the client.
    """
    if not fal_configured():
        return {'error': 'fal.ai not configured'}

    key = os.environ.get('FAL_KEY')  # read here, never placed in response
    if not key:
        return {'error': 'fal.ai key missing'}

    try:
        # The fal SDK reads FAL_KEY from the environment itself; we do not pass
        # it explicitly and never log/echo it.
        model = 'fal-ai/flux/schnell' if 'schnell' in model_id else 'fal-ai/flux/dev'
        result = fal_client.subscribe(
            model,
            arguments={'prompt': prompt, 'num_images': 1, 'image_size': f'{width}x{height}'},
            with_logs=False,
        )
        # Result shape: {'images': [{'url': ...}]} or {'image': {'url': ...}}
        images = None
        if isinstance(result, dict):
            images = result.get('images') or ([result['image']] if result.get('image') else None)
        if images and isinstance(images[0], dict) and images[0].get('url'):
            return {'image': images[0]['url'], 'provider': 'fal.ai', 'model': model_id}
        return {'error': 'fal.ai returned no image', 'detail': str(result)[:200]}
    except Exception as e:  # noqa: BLE001
        logger.warning('fal generation failed (falling back): %s', e)
        return {'error': f'fal.ai generation failed: {type(e).__name__}'}
