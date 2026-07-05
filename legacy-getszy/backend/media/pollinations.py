"""Free image generation via Pollinations.ai - no API key required.

Returns a stable URL that the browser/client can fetch directly.
Server-side we just construct + validate the prompt.
"""
import urllib.parse
import random
import httpx

POLLI_BASE = 'https://image.pollinations.ai/prompt'

STYLE_PRESETS = {
    'photoreal': 'professional photograph, ultra detailed, 8k, soft lighting, photorealistic',
    'product': 'clean product photography, white background, soft shadows, e-commerce listing style, premium',
    'cinematic': 'cinematic shot, film grain, moody lighting, dramatic composition, 8k',
    'illustration': 'flat vector illustration, modern, clean lines, vibrant palette',
    'logo': 'minimal flat logo, vector style, centered, white background, scalable, brand mark',
    'anime': 'anime art style, expressive, studio quality, sharp lineart',
    'portrait': 'professional portrait, sharp focus, studio lighting, bokeh background',
}

NEGATIVE = 'watermark, signature, text overlay, low quality, blurry, distorted, deformed'


def build_url(prompt: str, style: str = 'photoreal', width: int = 1024, height: int = 1024, seed: int | None = None, model: str = 'flux') -> str:
    style_text = STYLE_PRESETS.get(style, STYLE_PRESETS['photoreal'])
    full_prompt = f'{prompt}, {style_text}'
    enc = urllib.parse.quote(full_prompt)
    seed = seed if seed is not None else random.randint(1, 999999)
    # nologo=true removes provider watermark
    return f'{POLLI_BASE}/{enc}?width={width}&height={height}&seed={seed}&model={model}&nologo=true&enhance=true'


async def verify_reachable(url: str, timeout: float = 8.0) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.head(url)
            return r.status_code < 500
    except Exception:
        return False
