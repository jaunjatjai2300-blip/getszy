"""Image generation using HuggingFace FLUX — free inference API."""
import os
import httpx
import base64
import logging
from typing import Optional

logger = logging.getLogger('getszy.images')

HF_API_KEY = os.environ.get('HF_API_KEY', '')
HF_MODEL = os.environ.get('HF_IMAGE_MODEL', 'black-forest-labs/FLUX.1-schnell')
POLLINATIONS_URL = 'https://image.pollinations.ai/prompt/'


async def generate_image(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
    model: str = None,
    negative_prompt: str = '',
) -> dict:
    """Generate image from text prompt. Returns {url, base64}."""
    model = model or HF_MODEL

    # Try HF FLUX first
    if HF_API_KEY:
        try:
            return await _hf_flux(prompt, model, width, height, negative_prompt)
        except Exception as e:
            logger.warning(f'HF FLUX failed: {e}, falling back to Pollinations')

    # Fallback to Pollinations (free, no API key)
    try:
        return await _pollinations(prompt, width, height)
    except Exception as e:
        logger.error(f'All image providers failed: {e}')
        return {'url': '', 'base64': '', 'error': str(e)}


async def _hf_flux(prompt: str, model: str, width: int, height: int, negative_prompt: str) -> dict:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f'https://api-inference.huggingface.co/models/{model}',
            headers={'Authorization': f'Bearer {HF_API_KEY}'},
            json={
                'inputs': prompt,
                'parameters': {
                    'width': width,
                    'height': height,
                    'negative_prompt': negative_prompt,
                },
            },
        )
        resp.raise_for_status()
        content_type = resp.headers.get('content-type', '')
        if 'image' in content_type:
            b64 = base64.b64encode(resp.content).decode()
            return {'url': '', 'base64': f'data:image/png;base64,{b64}'}
        else:
            data = resp.json()
            if 'error' in data:
                raise RuntimeError(data['error'])
            return {'url': str(data), 'base64': ''}


async def _pollinations(prompt: str, width: int, height: int) -> dict:
    url = f'{POLLINATIONS_URL}{prompt}?width={width}&height={height}&nologo=true'
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        b64 = base64.b64encode(resp.content).decode()
        return {'url': url, 'base64': f'data:image/jpeg;base64,{b64}'}


async def generate_thumbnail(title: str, style: str = 'modern') -> dict:
    """Generate a course/product thumbnail."""
    prompt = f'Professional {style} thumbnail for "{title}", clean design, vibrant colors, 16:9 aspect ratio, high quality'
    return await generate_image(prompt, width=1280, height=720)


async def generate_product_image(product_name: str, category: str = '') -> dict:
    """Generate a product image."""
    prompt = f'Professional product photo of {product_name}, {"in " + category + " category, " if category else ""}white background, studio lighting, e-commerce style'
    return await generate_image(prompt, width=800, height=800)


async def generate_logo(text: str, style: str = 'minimal') -> dict:
    """Generate a logo."""
    prompt = f'{style} logo design for "{text}", clean, professional, vector style, white background'
    return await generate_image(prompt, width=512, height=512)


async def generate_social_post(topic: str, platform: str = 'instagram') -> dict:
    """Generate social media post image."""
    sizes = {
        'instagram': (1080, 1080),
        'youtube': (1280, 720),
        'twitter': (1200, 675),
        'linkedin': (1200, 627),
    }
    w, h = sizes.get(platform, (1080, 1080))
    prompt = f'Professional {platform} post about "{topic}", eye-catching design, modern, vibrant'
    return await generate_image(prompt, width=w, height=h)
