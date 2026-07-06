"""Per-scene visual fetcher.

Default provider: Pollinations.ai (free) for AI images.
Fallback: Pexels API if PEXELS_KEY is configured.
"""
import asyncio
import hashlib
import os
import urllib.parse
import httpx
from typing import Tuple

MEDIA_DIR = os.path.join(os.path.dirname(__file__), '..', 'media_cache', 'video_scenes')
os.makedirs(MEDIA_DIR, exist_ok=True)
PEXELS_KEY = os.environ.get('PEXELS_KEY', '').strip()


DIMS = {
    '9:16': (1080, 1920),
    '16:9': (1920, 1080),
    '1:1':  (1080, 1080),
}


async def fetch_scene_image(prompt: str, orientation: str = '9:16', seed: int = 0) -> str:
    w, h = DIMS.get(orientation, (1080, 1920))
    key = hashlib.sha1(f'{prompt}|{orientation}|{seed}'.encode()).hexdigest()[:16]
    path = os.path.join(MEDIA_DIR, f'{key}.jpg')
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        return path
    # Try Pollinations first (no key). Free tier is occasionally flaky under load, so retry once
    # with a fresh seed before falling through to Pexels/solid-color — this alone fixes most
    # "blank scene" failures users would otherwise see in finished videos.
    safe_prompt = urllib.parse.quote(prompt[:380])
    for attempt in range(2):
        attempt_seed = (seed or 42) + (attempt * 777)
        p_url = f'https://image.pollinations.ai/prompt/{safe_prompt}?width={w}&height={h}&nologo=true&enhance=true&seed={attempt_seed}&model=flux'
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.get(p_url)
                if r.status_code == 200 and len(r.content) > 2000:
                    with open(path, 'wb') as f:
                        f.write(r.content)
                    return path
        except Exception as e:
            print(f'[visuals] pollinations attempt {attempt + 1} failed: {e}')
        await asyncio.sleep(1.5)
    # Fallback: Pexels (if key)
    if PEXELS_KEY:
        try:
            async with httpx.AsyncClient(timeout=20.0, headers={'Authorization': PEXELS_KEY}) as client:
                r = await client.get('https://api.pexels.com/v1/search',
                                     params={'query': prompt[:80], 'orientation': 'portrait' if orientation == '9:16' else 'landscape', 'per_page': 1})
                if r.status_code == 200:
                    photos = r.json().get('photos', [])
                    if photos:
                        img_url = photos[0]['src']['large2x']
                        rr = await client.get(img_url, headers={})
                        if rr.status_code == 200:
                            with open(path, 'wb') as f:
                                f.write(rr.content)
                            return path
        except Exception as e:
            print(f'[visuals] pexels failed: {e}')
    # Final fallback: solid color JPEG via PIL
    try:
        from PIL import Image
        Image.new('RGB', (w, h), color=(20, 20, 30)).save(path, 'JPEG', quality=80)
    except Exception:
        pass
    return path
