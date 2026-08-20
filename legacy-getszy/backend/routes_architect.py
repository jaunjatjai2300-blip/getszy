"""Prompt Architect API — single natural-language entry point.

Customers type whatever they're thinking; the architect structures it and we
dispatch to the best generator: landing/website -> full HTML site, video ->
fast factory render, copy/social -> professional copy. One call, best-in-class
output, no wasted credits on vague prompts.
"""
import uuid
import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from db import db
from prompt_architect import architect, detect_intent
from brand_kit import get_brand, save_brand
from stock_media import (search_stock_image_urls, search_stock_video_urls,
                        search_stock_images, search_stock_videos)

logger = logging.getLogger('getszy.architect.api')
router = APIRouter(prefix='/architect', tags=['architect'])


class ArchitectIn(BaseModel):
    text: str
    intent: Optional[str] = None
    language: str = 'english'
    fast: bool = True  # video: target a ~60s express render
    product_id: Optional[str] = None       # exact catalog product id/slug
    product_query: Optional[str] = None    # fuzzy name match in catalog


class BrandKitIn(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    tagline: Optional[str] = None
    usp: Optional[str] = None
    audience: Optional[str] = None
    tone: Optional[str] = None
    colors: Optional[list] = None
    fonts: Optional[str] = None
    logo_url: Optional[str] = None
    social: Optional[str] = None
    forbidden: Optional[str] = None


class StockIn(BaseModel):
    query: str
    type: str = 'image'   # 'image' | 'video'
    n: int = 6


def _iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


async def _lookup_product(product_id: Optional[str] = None, product_query: Optional[str] = None):
    import re
    if product_id:
        return await db.products.find_one(
            {'$or': [{'id': product_id}, {'slug': product_id}]}, {'_id': 0, 'cost_price': 0})
    if product_query:
        items = await db.products.find(
            {'name': {'$regex': re.escape(product_query), '$options': 'i'}, 'is_active': True},
            {'_id': 0, 'cost_price': 0}).limit(3).to_list(3)
        return items[0] if items else None
    return None


@router.post('/generate')
async def generate(body: ArchitectIn, user=Depends(get_current_user)):
    return await _generate(body, user)


async def _generate(body: ArchitectIn, user):
    brand = await get_brand(user['id'])
    product = await _lookup_product(body.product_id, body.product_query)
    brief = await architect(body.text, body.intent, brand=brand, product=product)
    intent = brief.get('intent') or detect_intent(body.text)
    brief['intent'] = intent

    # ── Landing page / Website → full HTML site ──
    if intent in ('landing', 'website'):
        from builder_agents import build_site
        html = await build_site(brief['structured_prompt'], session_id=f'arch-{user["id"]}')
        pid = str(uuid.uuid4())
        await db.builder_projects.insert_one({
            'id': pid, 'user_id': user['id'], 'name': brief.get('name') or 'Untitled',
            'prompt': brief['structured_prompt'], 'html_content': html, 'history': [],
            'created_at': _iso(), 'updated_at': _iso(), 'source': 'architect',
        })
        return {
            'intent': intent,
            'brief': brief,
            'project_id': pid,
            'preview_url': f'/api/builder/projects/{pid}/preview',
            'download_url': f'/api/builder/projects/{pid}/download',
            'size_bytes': len(html),
        }

    # ── Video → fast factory render ──
    if intent == 'video':
        from credits import deduct
        from routes_video_factory import _run_chain_bg
        ok, msg, _ = await deduct(user['id'], 'video_factory_chain')
        if not ok:
            raise HTTPException(status_code=402, detail=msg)
        pid = str(uuid.uuid4())
        await db.video_projects.insert_one({
            'id': pid, 'user_id': user['id'],
            'title': brief.get('name') or body.text[:60],
            'prompt_raw': body.text, 'prompt': brief['structured_prompt'],
            'brief': brief, 'language': body.language, 'fast': body.fast,
            'status': 'created', 'stages': {}, 'selected_script_id': None,
            'created_at': _iso(), 'updated_at': _iso(),
        })
        asyncio.create_task(_run_chain_bg(pid, brief['structured_prompt'], body.language, user['id'], body.fast, brief))
        await db.video_projects.update_one({'id': pid}, {'$set': {'status': 'processing'}})
        return {
            'intent': 'video',
            'brief': brief,
            'project_id': pid,
            'status': 'processing',
            'poll_url': f'/api/video-factory/project/{pid}',
        }

    # ── Copy / Social → professional copy text ──
    if intent in ('copy', 'social'):
        from llm_provider import chat_completion
        system = (
            "You are a world-class conversion copywriter. Using the provided brief, "
            "write polished, specific, brand-grade copy. Use clear markdown structure "
            "(headings, bullets). No generic filler. Match the brief's tone, audience, "
            "language and CTA."
        )
        user_msg = (
            f"Brief:\n{brief.get('structured_prompt')}\n\n"
            f"Deliver {('a social media post' if intent=='social' else 'complete marketing copy')} "
            f"with hook, body and CTA."
        )
        try:
            content = await chat_completion(system=system, user=user_msg, temperature=0.6, max_tokens=2000)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f'generation failed: {e}')
        return {'intent': intent, 'brief': brief, 'content': content.strip()}

    # ── Logo / Image → structured brief + guidance ──
    return {
        'intent': intent,
        'brief': brief,
        'note': (
            'Use the dedicated Logo or Image tool with this structured brief for best results.'
            if intent == 'logo' else
            'Use the Image tool, or call /media/image with this brief.'
        ),
        'suggested_prompt': brief.get('visual_style') or brief['structured_prompt'],
    }


@router.get('/brand')
async def read_brand(user=Depends(get_current_user)):
    return await get_brand(user['id']) or {}


@router.post('/brand')
async def upsert_brand(body: BrandKitIn, user=Depends(get_current_user)):
    saved = await save_brand(user['id'], body.dict(exclude_unset=False))
    return {'ok': True, 'brand': saved}


@router.post('/stock')
async def stock_search(body: StockIn, user=Depends(get_current_user)):
    from safety_filter import safe_query_guard
    reason = safe_query_guard(body.query)
    if reason:
        raise HTTPException(status_code=400, detail=f'Request blocked: {reason}. We only provide decent, authentic, brand-safe media.')
    if body.type == 'video':
        items = await search_stock_video_urls(body.query, body.n)
    else:
        items = await search_stock_image_urls(body.query, body.n)
    return {'items': items}


@router.get('/trends')
async def trends(user=Depends(get_current_user)):
    """Trend-jacking: suggest high-engagement angles. Uses a live source when
    TRENDS_SOURCE env is configured, otherwise returns honest curated angles."""
    import httpx
    import os
    src = os.getenv('TRENDS_SOURCE')
    if src:
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(src)
                if r.status_code == 200:
                    data = r.json()
                    items = data.get('items') or data.get('trends') or []
                    if items:
                        return {'curated': False, 'items': items[:12]}
        except Exception:
            logger.warning('trends live source failed, using curated')
    # Honest curated "suggested angles" (evergreen, high-engagement creator topics)
    return {'curated': True, 'items': [
        {'topic': 'AI Robots 2026', 'angle': 'funny hinglish short on robots taking over homes'},
        {'topic': 'Budget Smartphone', 'angle': 'unboxing + honest review reel'},
        {'topic': 'Desi Street Food', 'angle': 'mouth-watering documentary-style food short'},
        {'topic': 'Side Hustle Ideas', 'angle': 'educational tutorial on making money online'},
        {'topic': 'Stock Market for Beginners', 'angle': 'simple explainer in hinglish'},
        {'topic': 'Weight Loss Without Gym', 'angle': 'motivational transformation short'},
        {'topic': 'Cricket World Cup Moments', 'angle': 'top 5 epic moments recap'},
        {'topic': 'Movie Review Hindi', 'angle': 'spicy funny review short'},
        {'topic': 'Python in 10 Minutes', 'angle': 'beginner coding tutorial'},
        {'topic': 'Parenting Hacks', 'angle': 'relatable funny parenting reel'},
    ]}
