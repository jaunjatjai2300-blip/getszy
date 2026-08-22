from pathlib import Path


BACKEND = Path(__file__).resolve().parents[1]
ROUTED = 'https://router.huggingface.co/hf-inference/models/'
LEGACY = 'https://api-inference.huggingface.co/models/'


def test_ai_provider_uses_routed_huggingface_inference_endpoint():
    source = (BACKEND / 'video' / 'ai_providers.py').read_text()
    assert ROUTED in source
    assert LEGACY not in source


def test_video_visuals_use_routed_huggingface_inference_endpoint():
    source = (BACKEND / 'video' / 'visuals.py').read_text()
    assert ROUTED in source
    assert LEGACY not in source
