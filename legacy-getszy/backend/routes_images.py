"""Image generation routes — FLUX via HuggingFace + Pollinations fallback."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from db import db
from image_gen import generate_image
from credits import deduct

router = APIRouter(prefix='/ai/images', tags=['ai-images'])


class ImageGenIn(BaseModel):
    prompt: str
    width: int = 1024
    height: int = 1024
    style: str = 'photorealistic'


@router.post('/generate')
async def generate(payload: ImageGenIn, user=Depends(get_current_user)):
    result = await generate_image(payload.prompt, payload.width, payload.height)
    if 'error' in result:
        raise HTTPException(status_code=502, detail=result['error'])
    record = {
        'id': str(uuid.uuid4()), 'user_id': user['id'],
        'prompt': payload.prompt, 'width': payload.width,
        'height': payload.height, 'provider': result.get('provider', 'unknown'),
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    await db.images.insert_one(record)
    return {'image': result.get('image'), 'provider': result.get('provider'), 'id': record['id']}


@router.get('/history')
async def history(limit: int = 20, user=Depends(get_current_user)):
    cur = db.images.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'images': [i async for i in cur]}
