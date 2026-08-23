from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
ROUTED = 'https://router.huggingface.co/hf-inference/models/'
LEGACY = 'https://api-inference.huggingface.co/models/'
RETIRED_MODEL = 'black-forest-labs/FLUX.1-schnell'
VERIFIED_MODEL = 'stabilityai/stable-diffusion-3-medium-diffusers'


def test_ai_provider_uses_routed_huggingface_inference_endpoint():
    source = (BACKEND / 'video' / 'ai_providers.py').read_text()
    assert ROUTED in source
    assert LEGACY not in source
    assert VERIFIED_MODEL in source
    assert RETIRED_MODEL not in source


def test_video_visuals_use_routed_huggingface_inference_endpoint():
    source = (BACKEND / 'video' / 'visuals.py').read_text()
    assert ROUTED in source
    assert LEGACY not in source
    assert VERIFIED_MODEL in source
    assert RETIRED_MODEL not in source
