"""Free stock media search — real images & videos, zero paid APIs.

Primary path is keyless (Openverse for images, Wikimedia Commons for video) so
it works out-of-the-box at no cost. If free API keys are present (PEXELS_KEY /
PIXABAY_KEY — both free to obtain, never paid) we prefer them for true 4K.

Results are downloaded to a local cache and returned as file paths. AI image
generation (Pollinations/FLUX) is only a fallback when stock is empty, so every
video saves credits and renders faster with real, licence-clear footage.
"""
import asyncio
import hashlib
import os
import re
import httpx
import logging

from safety_filter import contains_unsafe, safe_query_guard, safe_item

logger = logging.getLogger('getszy.stock')

CACHE = os.path.join(os.path.dirname(__file__), '..', 'media_cache', 'stock')
os.makedirs(CACHE, exist_ok=True)

PEXELS_KEY = os.environ.get('PEXELS_KEY', '').strip()
PIXABAY_KEY = os.environ.get('PIXABAY_KEY', '').strip()
USE_STOCK = os.environ.get('VF_USE_STOCK', '1').strip().lower() not in ('0', 'false', 'no')
USE_STOCK_VIDEO = os.environ.get('VF_USE_STOCK_VIDEO', '1').strip().lower() not in ('0', 'false', 'no')

_HEADERS = {'User-Agent': 'Getszy/1.0 (free stock media; contact: ops@getszy.in)'}


def _cached_path(url: str, ext: str) -> str:
    h = hashlib.sha1(url.encode(), usedforsecurity=False).hexdigest()[:16]
    return os.path.join(CACHE, f'{h}.{ext}')


async def _download(url: str, path: str, timeout: float = 60.0) -> bool:
    if os.path.exists(path) and os.path.getsize(path) > 2000:
        return True
    try:
        async with httpx.AsyncClient(timeout=timeout, headers=_HEADERS, follow_redirects=True) as c:
            r = await c.get(url)
            if r.status_code == 200 and len(r.content) > 2000:
                with open(path, 'wb') as f:
                    f.write(r.content)
                return True
    except Exception as e:
        logger.warning('stock download failed %s: %s', url[:80], e)
    return False


# ───────────────────────── IMAGES ─────────────────────────
async def _openverse_images(query: str, n: int):
    out = []
    try:
        async with httpx.AsyncClient(timeout=20.0, headers=_HEADERS, follow_redirects=True) as c:
            r = await c.get('https://api.openverse.org/v1/images/',
                            params={'q': query, 'page_size': n * 3, 'license_type': 'all'})
            if r.status_code == 200:
                for it in r.json().get('results', []):
                    if it.get('mature'):
                        continue
                    url = it.get('url')
                    if url and safe_item(it.get('title', ''), url):
                        w = int(it.get('width') or 0)
                        out.append((url, w, 'jpg'))
    except Exception as e:
        logger.warning('openverse images failed: %s', e)
    return out


async def _pexels_images(query: str, n: int):
    if not PEXELS_KEY:
        return []
    out = []
    try:
        async with httpx.AsyncClient(timeout=20.0, headers={'Authorization': PEXELS_KEY}, follow_redirects=True) as c:
            r = await c.get('https://api.pexels.com/v1/search',
                            params={'query': query, 'per_page': n * 2, 'orientation': 'portrait'})
            if r.status_code == 200:
                for p in r.json().get('photos', []):
                    src = p.get('src', {})
                    url = src.get('original') or src.get('large2x')
                    w = int(src.get('large2x', '0').split('x')[0] if src.get('large2x') else 0)
                    if url and safe_item(p.get('alt', ''), url):
                        out.append((url, w, 'jpg'))
    except Exception as e:
        logger.warning('pexels images failed: %s', e)
    return out


async def _pixabay_images(query: str, n: int):
    if not PIXABAY_KEY:
        return []
    out = []
    try:
        async with httpx.AsyncClient(timeout=20.0, headers=_HEADERS, follow_redirects=True) as c:
            r = await c.get('https://pixabay.com/api/',
                            params={'key': PIXABAY_KEY, 'q': query, 'per_page': n * 2,
                                    'image_type': 'photo', 'safesearch': 'true'})
            if r.status_code == 200:
                for h in r.json().get('hits', []):
                    if not safe_item(h.get('tags', ''), h.get('pageURL', '')):
                        continue
                    url = h.get('fullHDURL') or h.get('largeImageURL') or h.get('webformatURL')
                    if url:
                        out.append((url, int(h.get('imageWidth') or 0), 'jpg'))
    except Exception as e:
        logger.warning('pixabay images failed: %s', e)
    return out


async def search_stock_images(query: str, n: int = 4, min_width: int = 1280) -> list:
    """Return up to `n` local image paths (preferring widest/4K). Empty if none."""
    if not USE_STOCK or not query or safe_query_guard(query):
        return []
    candidates = []
    for fn in (_pexels_images, _pixabay_images, _openverse_images):
        try:
            candidates += await fn(query, n)
        except Exception:
            pass
    candidates = [c for c in candidates if c[1] >= min_width or c[1] == 0]
    candidates.sort(key=lambda x: x[1], reverse=True)
    paths = []
    for url, _, ext in candidates[:n]:
        path = _cached_path(url, ext)
        if await _download(url, path):
            paths.append(path)
        if len(paths) >= n:
            break
    return paths


# ───────────────────────── VIDEOS ─────────────────────────
async def _pexels_videos(query: str, n: int):
    if not PEXELS_KEY:
        return []
    out = []
    try:
        async with httpx.AsyncClient(timeout=25.0, headers={'Authorization': PEXELS_KEY}, follow_redirects=True) as c:
            r = await c.get('https://api.pexels.com/videos/search',
                            params={'query': query, 'per_page': n * 2})
            if r.status_code == 200:
                for v in r.json().get('videos', []):
                    if not safe_item(v.get('url', '')):
                        continue
                    files = v.get('video_files', [])
                    files.sort(key=lambda f: (f.get('quality') == '4k', f.get('width') or 0), reverse=True)
                    if files and files[0].get('link'):
                        out.append((files[0]['link'], files[0].get('width') or 0, 'mp4'))
    except Exception as e:
        logger.warning('pexels videos failed: %s', e)
    return out


async def _pixabay_videos(query: str, n: int):
    if not PIXABAY_KEY:
        return []
    out = []
    try:
        async with httpx.AsyncClient(timeout=25.0, headers=_HEADERS, follow_redirects=True) as c:
            r = await c.get('https://pixabay.com/api/videos/',
                            params={'key': PIXABAY_KEY, 'q': query, 'per_page': n * 2, 'safesearch': 'true'})
            if r.status_code == 200:
                for h in r.json().get('hits', []):
                    if not safe_item(h.get('tags', ''), h.get('pageURL', '')):
                        continue
                    vids = h.get('videos', {})
                    best = vids.get('4k') or vids.get('hd') or vids.get('sd') or vids.get('fhd')
                    if best and best.get('url'):
                        out.append((best['url'], int(best.get('width') or 0), 'mp4'))
    except Exception as e:
        logger.warning('pixabay videos failed: %s', e)
    return out


async def _wikimedia_videos(query: str, n: int):
    """Keyless fallback: Wikimedia Commons free (CC/PD) video files."""
    out = []
    try:
        async with httpx.AsyncClient(timeout=25.0, headers=_HEADERS, follow_redirects=True) as c:
            r = await c.get('https://commons.wikimedia.org/w/api.php',
                            params={
                                'action': 'query', 'format': 'json', 'generator': 'search',
                                'gsrsearch': f'{query} filetype:video', 'gsrnamespace': 6,
                                'gsrlimit': n * 3, 'prop': 'imageinfo',
                                'iiprop': 'url|size|mime', 'iiurlwidth': 1920,
                            })
            if r.status_code == 200:
                pages = (r.json().get('query', {}) or {}).get('pages', {})
                for p in pages.values():
                    ii = (p.get('imageinfo') or [{}])[0]
                    url = ii.get('url')
                    mime = ii.get('mime', '')
                    if url and ('video' in mime or url.endswith('.webm') or url.endswith('.ogv')) \
                            and safe_item(p.get('title', ''), url):
                        out.append((url, ii.get('width') or 0, 'mp4'))
    except Exception as e:
        logger.warning('wikimedia videos failed: %s', e)
    return out


async def search_stock_videos(query: str, n: int = 2) -> list:
    """Return up to `n` local video clip paths (preferring widest/4K)."""
    if not USE_STOCK_VIDEO or not query or safe_query_guard(query):
        return []
    candidates = []
    for fn in (_pexels_videos, _pixabay_videos, _wikimedia_videos):
        try:
            candidates += await fn(query, n)
        except Exception:
            pass
    candidates.sort(key=lambda x: x[1], reverse=True)
    paths = []
    for url, _, ext in candidates[:n]:
        path = _cached_path(url, 'mp4')
        if await _download(url, path, timeout=90.0):
            paths.append(path)
        if len(paths) >= n:
            break
    return paths


def _dedupe(items):
    seen, out = set(), []
    for url, w, ext in items:
        if url in seen:
            continue
        seen.add(url)
        out.append({'url': url, 'width': w})
    return out


async def search_stock_image_urls(query: str, n: int = 6) -> list:
    """Return remote image URLs (4K preferred) without downloading — for preview UIs."""
    if not USE_STOCK or not query or safe_query_guard(query):
        return []
    cands = []
    for fn in (_pexels_images, _pixabay_images, _openverse_images):
        try:
            cands += await fn(query, n)
        except Exception:
            pass
    cands = [(u, w, e) for (u, w, e) in cands if safe_item(u)]
    cands.sort(key=lambda x: x[1], reverse=True)
    return _dedupe(cands)[:n]


async def search_stock_video_urls(query: str, n: int = 4) -> list:
    """Return remote stock video URLs (4K preferred) without downloading."""
    if not USE_STOCK_VIDEO or not query or safe_query_guard(query):
        return []
    cands = []
    for fn in (_pexels_videos, _pixabay_videos, _wikimedia_videos):
        try:
            cands += await fn(query, n)
        except Exception:
            pass
    cands = [(u, w, e) for (u, w, e) in cands if safe_item(u)]
    cands.sort(key=lambda x: x[1], reverse=True)
    return _dedupe(cands)[:n]
