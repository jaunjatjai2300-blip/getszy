"""FLUX image generation via HuggingFace Inference + Pollinations fallback."""
import os
import httpx
import logging

logger = logging.getLogger('getszy.image_gen')

HF_TOKEN = os.environ.get('HF_TOKEN', '').strip()
POLLINATIONS_URL = 'https://image.pollinations.ai/prompt/{prompt}'


async def generate_image_hf(prompt: str, width: int = 1024, height: int = 1024) -> dict:
    if not HF_TOKEN:
        return {'error': 'HF_TOKEN not set'}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                'https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell',
                headers={'Authorization': f'Bearer {HF_TOKEN}'},
                json={'inputs': prompt, 'parameters': {'width': width, 'height': height}}
            )
            if resp.status_code == 200 and 'image' in resp.headers.get('content-type', ''):
                import base64
                img_b64 = base64.b64encode(resp.content).decode()
                return {'image': img_b64, 'provider': 'huggingface', 'model': 'FLUX.1-schnell'}
            return {'error': f'HF API returned {resp.status_code}', 'detail': resp.text[:200]}
    except Exception as e:
        return {'error': str(e)}


async def generate_image_pollinations(prompt: str, width: int = 1024, height: int = 1024) -> dict:
    url = POLLINATIONS_URL.format(prompt=prompt.replace(' ', '+'))
    url += f'?width={width}&height={height}&nologo=true'
    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200 and len(resp.content) > 1000:
                import base64
                img_b64 = base64.b64encode(resp.content).decode()
                return {'image': img_b64, 'provider': 'pollinations'}
            return {'error': f'Pollinations returned {resp.status_code}'}
    except Exception as e:
        return {'error': str(e)}


async def generate_image(prompt: str, width: int = 1024, height: int = 1024) -> dict:
    result = await generate_image_hf(prompt, width, height)
    if 'image' in result:
        return result
    logger.warning('HF image gen failed, falling back to Pollinations')
    return await generate_image_pollinations(prompt, width, height)
