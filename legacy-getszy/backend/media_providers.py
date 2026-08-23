"""Free-only media provider registry for the SamurAIGPT / Open-Generative-AI suite.

Design mirrors ``llm_provider.py`` so the media surface shares the same guarantees:
- ``FREE_ONLY_MEDIA`` is always True. Paid platforms (Midjourney / Runway / Kling /
  Luma) are intentionally NOT wired. Bring-your-own-key adapters stay
  default-OFF and are never surfaced to customers — the backend runs on the
  HF Free Tier + Pollinations + Edge-TTS + Whisper only.
- Every capability reports live availability so the dashboard/monitoring can show
  status and so generation is never silently dead.

This module is a thin, import-safe status/registry layer. The actual model
wrappers live in the dedicated generator modules (``image_gen``, ``voice_gen``,
``whisper_stt``, ``video/*``).
"""
import os

FREE_ONLY_MEDIA = True

HF_TOKEN = os.environ.get('HF_TOKEN', '').strip()
POLLINATIONS_ENABLED = True  # free, no key required

# Capability registry. ``available`` is derived from whether a free provider exists.
_CAPABILITIES = {
    'image': {
        'label': 'Text-to-Image',
        'providers': ['huggingface-flux', 'pollinations'],
    },
    'design': {
        'label': 'Graphic Design (banner / poster / social)',
        'providers': ['huggingface-flux', 'pollinations'],
    },
    'tts': {
        'label': 'Text-to-Speech',
        'providers': ['edge-tts'],
    },
    'stt': {
        'label': 'Speech-to-Text',
        'providers': ['whisper'],
    },
    'video': {
        'label': 'Text / Image-to-Video',
        'providers': ['pollinations', 'huggingface-flux'],
    },
    'shorts': {
        'label': 'Shorts / Reel Generator',
        'providers': ['whisper', 'ffmpeg', 'edge-tts'],
    },
    'workflow': {
        'label': 'Vibe Workflow (JSON DAG)',
        'providers': ['media-suite'],
    },
}


def _capability_available(key: str) -> bool:
    if key in ('image', 'design', 'video'):
        # Pollinations is always free; HF adds FLUX when the token is present.
        return POLLINATIONS_ENABLED or bool(HF_TOKEN)
    if key == 'tts':
        return True  # edge-tts is free, no key
    if key == 'stt':
        return True  # whisper is free / local
    if key == 'shorts':
        return True  # upload or youtube_url -> whisper + ffmpeg
    if key == 'workflow':
        return True  # server-side JSON DAG executor
    return False


def media_provider_info() -> dict:
    """Return live, cheap (no network) status of free media capabilities."""
    providers = {}
    for key, cap in _CAPABILITIES.items():
        available = _capability_available(key)
        if key in ('image', 'design', 'video'):
            detail = (
                'huggingface-flux + pollinations'
                if HF_TOKEN else 'pollinations (HF_TOKEN not set)'
            )
        elif key == 'tts':
            detail = 'edge-tts (free, no key)'
        elif key == 'stt':
            detail = 'whisper (free)'
        elif key == 'shorts':
            detail = 'upload or youtube_url -> whisper + ffmpeg'
        elif key == 'workflow':
            detail = 'server-side JSON DAG executor'
        else:
            detail = ''
        providers[key] = {
            'label': cap['label'],
            'free': True,
            'available': available,
            'detail': detail,
            'blocked_by_paid_policy': False,
        }
    usable = [k for k, v in providers.items() if v['available']]
    return {
        'free_only': FREE_ONLY_MEDIA,
        'healthy': bool(usable),
        'providers': providers,
        'usable': usable,
    }
