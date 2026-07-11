"""Per-scene visual fetcher.

Providers:
  pollinations  — free, no key, good quality  (default)
  flux_hd       — HuggingFace FLUX.1-schnell, requires HF_TOKEN (best quality)
Fallback chain: flux_hd -> pollinations -> pexels -> solid color
"""
import asyncio
import hashlib
import json
import os
import urllib.parse
import httpx

MEDIA_DIR = os.path.join(os.path.dirname(__file__), '..', 'media_cache', 'video_scenes')
os.makedirs(MEDIA_DIR, exist_ok=True)
PEXELS_KEY = os.environ.get('PEXELS_KEY', '').strip()
HF_TOKEN   = os.environ.get('HF_TOKEN', '').strip()

DIMS = {
    '9:16': (1080, 1920),
    '16:9': (1920, 1080),
    '1:1':  (1080, 1080),
}

# HF FLUX supports max 1024px per side
HF_DIMS = {
    '9:16': (768, 1024),
    '16:9': (1024, 576),
    '1:1':  (1024, 1024),
}

HF_MODEL = 'black-forest-labs/FLUX.1-schnell'


async def _fetch_pollinations(prompt: str, orientation: str, seed: int, path: str) -> bool:
    w, h = DIMS.get(orientation, (1080, 1920))
    safe = urllib.parse.quote(prompt[:380])
    for attempt in range(2):
        s = (seed or 42) + (attempt * 777)
        url = f'https://image.pollinations.ai/prompt/{safe}?width={w}&height={h}&nologo=true&enhance=true&seed={s}&model=flux'
        try:
            async with httpx.AsyncClient(timeout=50.0) as c:
                r = await c.get(url)
                if r.status_code == 200 and len(r.content) > 2000:
                    with open(path, 'wb') as f:
                        f.write(r.content)
                    return True
        except Exception as e:
            print(f'[visuals] pollinations attempt {attempt + 1} failed: {e}')
        await asyncio.sleep(1.5)
    return False


async def _fetch_hf_flux(prompt: str, orientation: str, seed: int, path: str) -> bool:
    if not HF_TOKEN:
        return False
    w, h = HF_DIMS.get(orientation, (768, 1024))
    payload = json.dumps({
        'inputs': prompt[:400],
        'parameters': {'width': w, 'height': h, 'num_inference_steps': 4, 'seed': seed or 42}
    })
    headers = {'Authorization': f'Bearer {HF_TOKEN}', 'Content-Type': 'application/json'}
    try:
        async with httpx.AsyncClient(timeout=120.0) as c:
            r = await c.post(
                f'https://api-inference.huggingface.co/models/{HF_MODEL}',
                content=payload, headers=headers
            )
            if r.status_code == 200 and r.headers.get('content-type', '').startswith('image'):
                with open(path, 'wb') as f:
                    f.write(r.content)
                return True
            # Model loading — wait and retry once
            if r.status_code == 503:
                await asyncio.sleep(20)
                r2 = await c.post(
                    f'https://api-inference.huggingface.co/models/{HF_MODEL}',
                    content=payload, headers=headers
                )
                if r2.status_code == 200 and r2.headers.get('content-type', '').startswith('image'):
                    with open(path, 'wb') as f:
                        f.write(r2.content)
                    return True
    except Exception as e:
        print(f'[visuals] flux_hd failed: {e}')
    return False


async def _fetch_pexels(prompt: str, orientation: str, path: str) -> bool:
    if not PEXELS_KEY:
        return False
    orient = 'portrait' if orientation == '9:16' else 'landscape'
    try:
        async with httpx.AsyncClient(timeout=20.0, headers={'Authorization': PEXELS_KEY}) as c:
            r = await c.get('https://api.pexels.com/v1/search',
                            params={'query': prompt[:80], 'orientation': orient, 'per_page': 1})
            if r.status_code == 200:
                photos = r.json().get('photos', [])
                if photos:
                    rr = await c.get(photos[0]['src']['large2x'], headers={})
                    if rr.status_code == 200:
                        with open(path, 'wb') as f:
                            f.write(rr.content)
                        return True
    except Exception as e:
        print(f'[visuals] pexels failed: {e}')
    return False


async def fetch_scene_image(prompt: str, orientation: str = '9:16', seed: int = 0,
                            provider: str = 'pollinations') -> str:
    w, h = DIMS.get(orientation, (1080, 1920))
    cache_key = hashlib.sha1(f'{provider}|{prompt}|{orientation}|{seed}'.encode()).hexdigest()[:16]
    path = os.path.join(MEDIA_DIR, f'{cache_key}.jpg')
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        return path

    if provider == 'flux_hd':
        if await _fetch_hf_flux(prompt, orientation, seed, path):
            return path
        print('[visuals] flux_hd unavailable, falling back to pollinations')
        if await _fetch_pollinations(prompt, orientation, seed, path):
            return path
    else:
        if await _fetch_pollinations(prompt, orientation, seed, path):
            return path

    if await _fetch_pexels(prompt, orientation, path):
        return path

    # Final fallback: solid colour
    try:
        from PIL import Image
        Image.new('RGB', (w, h), color=(20, 20, 30)).save(path, 'JPEG', quality=80)
    except Exception:
        pass
    return path
