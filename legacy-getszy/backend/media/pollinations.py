"""Free image generation via Pollinations.ai - no API key required.

Returns a stable URL that the browser/client can fetch directly.
Server-side we just construct + validate the prompt.
"""
import urllib.parse
import random
import httpx

POLLI_BASE = 'https://image.pollinations.ai/prompt'

STYLE_PRESETS = {
    'photoreal': 'professional photograph, shot on Sony A7R IV, 85mm lens, ultra detailed skin/texture, '
                 'natural soft lighting, shallow depth of field, photorealistic, award-winning photography, 8k uhd',
    'product': 'clean product photography, white seamless background, soft studio softbox lighting, subtle '
               'reflection, e-commerce hero shot, premium catalog quality, sharp focus, high dynamic range',
    'cinematic': 'cinematic still, anamorphic lens flare, film grain, moody volumetric lighting, dramatic '
                 'composition, color graded, 8k, shot on ARRI Alexa',
    'illustration': 'flat vector illustration, modern editorial style, clean bold lines, vibrant harmonious '
                    'palette, high resolution vector art',
    'logo': 'minimal flat logo mark, vector style, centered composition, plain white background, scalable '
            'brand identity, professional graphic design, clean negative space',
    'anime': 'anime key visual, expressive character design, studio-quality cel shading, sharp lineart, '
             'vibrant colors, trending on pixiv',
    'portrait': 'professional editorial portrait, sharp focus on eyes, studio Rembrandt lighting, creamy '
                'bokeh background, high-end fashion photography, 8k detail',
}

# Style -> best-fit Pollinations model. flux gives the sharpest general photoreal results today;
# turbo trades a little fidelity for speed on simpler graphic styles.
STYLE_MODEL = {
    'photoreal': 'flux',
    'product': 'flux',
    'cinematic': 'flux',
    'portrait': 'flux',
    'illustration': 'turbo',
    'logo': 'turbo',
    'anime': 'flux',
}

NEGATIVE = ('watermark, signature, text overlay, logo overlay, low quality, blurry, distorted, deformed, '
            'extra limbs, extra fingers, mutated hands, bad anatomy, cropped, out of frame, jpeg artifacts')


def build_url(prompt: str, style: str = 'photoreal', width: int = 1024, height: int = 1024,
              seed: int | None = None, model: str | None = None) -> str:
    style_text = STYLE_PRESETS.get(style, STYLE_PRESETS['photoreal'])
    full_prompt = f'{prompt}, {style_text}'
    enc = urllib.parse.quote(full_prompt)
    neg = urllib.parse.quote(NEGATIVE)
    seed = seed if seed is not None else random.randint(1, 999999)
    resolved_model = model or STYLE_MODEL.get(style, 'flux')
    # nologo=true removes provider watermark; enhance=true runs Pollinations' own prompt upscaler;
    # negative= steers away from common AI-image artifacts (extra fingers, watermarks, etc).
    return (f'{POLLI_BASE}/{enc}?width={width}&height={height}&seed={seed}&model={resolved_model}'
            f'&nologo=true&enhance=true&negative={neg}')


async def verify_reachable(url: str, timeout: float = 8.0) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.head(url)
            return r.status_code < 500
    except Exception:
        return False
