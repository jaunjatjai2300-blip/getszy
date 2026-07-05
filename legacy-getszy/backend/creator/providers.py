"""Creator OS - GPU-ready provider switcher.

Getszy is designed to seamlessly switch from free CPU providers (Pollinations,
HF Inference free) to dedicated GPU providers (fal.ai, Replicate, self-hosted)
as the user scales from VPS to GPU infrastructure.

Provider tiers:
  free   - Pollinations.ai (image), HF free inference (text/tts)
  paid   - fal.ai (Flux, Kling, Live Portrait), Replicate
  local  - User's own GPU box / Ollama with vision/voice models

The MEDIA_PROVIDER env var picks the active tier.
"""
import os

MEDIA_PROVIDER = os.environ.get('MEDIA_PROVIDER', 'free').lower()
FAL_KEY = os.environ.get('FAL_KEY', '').strip()
REPLICATE_TOKEN = os.environ.get('REPLICATE_TOKEN', '').strip()
HF_TOKEN = os.environ.get('HF_TOKEN', '').strip()
GPU_HOST = os.environ.get('GPU_HOST', '').strip()  # e.g. http://gpu.getszy.com:8000


def active_provider(capability: str) -> dict:
    """Return active provider for a capability with status info.

    capability in {'image', 'video', 'voice', 'mirror', 'music', 'upscale'}
    """
    have = {
        'fal':       bool(FAL_KEY),
        'replicate': bool(REPLICATE_TOKEN),
        'hf':        bool(HF_TOKEN),
        'gpu':       bool(GPU_HOST),
    }
    plan = {
        'image':   ['pollinations', 'fal', 'replicate', 'gpu'],
        'video':   ['hf', 'fal', 'replicate', 'gpu'],
        'voice':   ['hf', 'fal', 'gpu'],
        'mirror':  ['fal', 'replicate', 'gpu'],
        'music':   ['hf', 'replicate'],
        'upscale': ['replicate', 'gpu'],
    }.get(capability, ['pollinations'])
    for p in plan:
        if p == 'pollinations':
            return {'name': 'pollinations', 'status': 'live', 'cost': 'free', 'capability': capability}
        if have.get(p):
            return {'name': p, 'status': 'live', 'cost': 'paid' if p in ('fal', 'replicate') else 'local', 'capability': capability}
    return {'name': 'pending', 'status': 'pending_provider', 'cost': '-', 'capability': capability}


def readiness() -> dict:
    caps = ['image', 'video', 'voice', 'mirror', 'music', 'upscale']
    return {
        'media_provider': MEDIA_PROVIDER,
        'gpu_host': GPU_HOST or None,
        'capabilities': {c: active_provider(c) for c in caps},
    }
