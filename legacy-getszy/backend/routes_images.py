"""Image generation routes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from auth import get_current_user, get_current_admin
from image_gen import generate_image, generate_thumbnail, generate_product_image, generate_logo, generate_social_post
from audit_log import log_action, ACTION_AI_REQUEST

router = APIRouter(prefix='/ai/images', tags=['images'])


class ImageGenIn(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    width: int = Field(1024, ge=256, le=2048)
    height: int = Field(1024, ge=256, le=2048)
    negative_prompt: Optional[str] = ''
    model: Optional[str] = None


class ThumbnailIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    style: str = 'modern'


class ProductImageIn(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=200)
    category: Optional[str] = ''


class LogoIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=100)
    style: str = 'minimal'


class SocialPostIn(BaseModel):
    topic: str = Field(..., min_length=1, max_length=500)
    platform: str = 'instagram'


@router.post('/generate')
async def gen_image(body: ImageGenIn, user=Depends(get_current_user)):
    result = await generate_image(body.prompt, body.width, body.height, body.model, body.negative_prompt)
    await log_action(ACTION_AI_REQUEST, user_id=user['id'], user_email=user.get('email'),
                     details={'type': 'image', 'prompt': body.prompt[:100]})
    return result


@router.post('/thumbnail')
async def gen_thumbnail(body: ThumbnailIn, user=Depends(get_current_user)):
    return await generate_thumbnail(body.title, body.style)


@router.post('/product')
async def gen_product_image(body: ProductImageIn, user=Depends(get_current_user)):
    return await generate_product_image(body.product_name, body.category)


@router.post('/logo')
async def gen_logo(body: LogoIn, user=Depends(get_current_user)):
    return await generate_logo(body.text, body.style)


@router.post('/social')
async def gen_social(body: SocialPostIn, user=Depends(get_current_user)):
    return await generate_social_post(body.topic, body.platform)
