"""Creator OS REST routes - scripts, trends, hooks, viral scoring, repurpose, providers."""
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_user, get_current_admin
from db import db
from creator.scripts import generate as gen_script, score_hook, viral_score, FORMATS
from creator.trends import predict as predict_trends, competitor_gap
from creator.providers import readiness, active_provider
from credits import deduct, refund
from llm_provider import chat_completion, LLMServiceUnavailable

router = APIRouter(prefix='/creator', tags=['creator'])


class ScriptIn(BaseModel):
    topic: str
    format: str = 'youtube_short'
    audience: str = 'indian creators'
    tone: str = 'energetic'
    language: str = 'hinglish'


class HookIn(BaseModel):
    hook: str


class ViralIn(BaseModel):
    content: Dict[str, Any]


class TrendsIn(BaseModel):
    niche: Optional[str] = ''
    count: Optional[int] = 8
    region: Optional[str] = 'IN'


class CompetitorIn(BaseModel):
    competitor: str


class RepurposeIn(BaseModel):
    long_script_topic: str
    target_formats: List[str] = ['youtube_short', 'instagram_reel', 'tweet_thread']


# ===== Provider Readiness =====
@router.get('/providers')
async def providers(_=Depends(get_current_user)):
    return readiness()


@router.get('/formats')
async def list_formats(_=Depends(get_current_user)):
    return {'formats': [{'id': k, **v} for k, v in FORMATS.items()]}


# ===== Scripts =====
@router.post('/script')
async def script(payload: ScriptIn, user=Depends(get_current_user)):
    if len(payload.topic.strip()) < 4:
        raise HTTPException(status_code=400, detail='Topic is too short')
    ok, msg, _ = await deduct(user['id'], 'script')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    try:
        data = await gen_script(payload.topic, payload.format, payload.audience, payload.tone, payload.language)
        asset = {
            'id': str(uuid.uuid4()), 'user_id': user['id'], 'kind': 'script',
            'topic': payload.topic, 'format': payload.format, 'data': data,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.creator_assets.insert_one(asset)
        asset.pop('_id', None)
        return asset
    except Exception:
        await refund(user['id'], 'script', reason='generation_failed')
        raise


@router.post('/score-hook')
async def hook_endpoint(payload: HookIn, _=Depends(get_current_user)):
    return await score_hook(payload.hook)


@router.post('/viral-score')
async def viral_endpoint(payload: ViralIn, _=Depends(get_current_user)):
    return await viral_score(payload.content)


# ===== Trends =====
@router.post('/trends')
async def trends_endpoint(payload: TrendsIn, user=Depends(get_current_user)):
    data = await predict_trends(payload.niche or '', payload.count or 8, payload.region or 'IN')
    rec = {
        'id': str(uuid.uuid4()), 'user_id': user['id'], 'niche': payload.niche or 'auto',
        'data': data, 'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.creator_trends.insert_one(rec)
    rec.pop('_id', None)
    return rec


@router.post('/competitor-gap')
async def gap_endpoint(payload: CompetitorIn, _=Depends(get_current_user)):
    return await competitor_gap(payload.competitor)


# ===== Repurpose: one topic -> many formats =====
@router.post('/repurpose')
async def repurpose(payload: RepurposeIn, user=Depends(get_current_user)):
    if not payload.target_formats:
        raise HTTPException(status_code=400, detail='target_formats required')
    ok, msg, _ = await deduct(user['id'], 'repurpose_format', qty=len(payload.target_formats))
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    outputs = {}
    failed_count = 0
    for fmt in payload.target_formats:
        try:
            outputs[fmt] = await gen_script(payload.long_script_topic, fmt)
        except Exception as e:
            outputs[fmt] = {'error': str(e)}
            failed_count += 1
    if failed_count:
        await refund(user['id'], 'repurpose_format', qty=failed_count, reason='generation_failed')
    rec = {
        'id': str(uuid.uuid4()), 'user_id': user['id'], 'kind': 'repurpose',
        'topic': payload.long_script_topic, 'outputs': outputs,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.creator_assets.insert_one(rec)
    rec.pop('_id', None)
    return rec


@router.get('/history')
async def history(limit: int = 30, user=Depends(get_current_user)):
    cur = db.creator_assets.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(limit)
    return {'items': [doc async for doc in cur]}


# ===== Viral Hook Generator (Pillar 1: "The Viral Engine") =====
class ViralHooksIn(BaseModel):
    niche: str = Field(..., min_length=2, max_length=120, description="e.g. 'history facts', 'finance tips'")
    count: int = Field(5, ge=1, le=10)
    language: str = 'hinglish'
    blend_trends: bool = False


def _extract_json_array(text: str):
    """Best-effort parse of a JSON array from an LLM response."""
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
    return None


@router.post('/viral-hooks')
async def viral_hooks(payload: ViralHooksIn, user=Depends(get_current_user)):
    """Generate scroll-stopping hook openers for short-form video."""
    ok, msg, _ = await deduct(user['id'], 'viral_hooks')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    try:
        trend_context = ''
        if payload.blend_trends:
            try:
                trends = await predict_trends(payload.niche, 5, 'IN')
                items = (trends or {}).get('trends') or (trends or {}).get('items') or []
                if items:
                    trend_context = '\nTrending angles right now: ' + ', '.join(
                        str(t.get('topic') or t.get('title') or t) for t in items[:5]
                    )
            except Exception:
                trend_context = ''

        system = (
            "You are a viral short-form content hook specialist for Indian creators "
            "(YouTube Shorts, Instagram Reels, Facebook videos). Write scroll-stopping "
            "opening lines that maximize retention through curiosity, contrast and gap."
        )
        user_prompt = (
            f"Generate {payload.count} distinct viral hook openers for the niche "
            f"'{payload.niche}' in {payload.language}. Each hook must be under 12 words, "
            f"punchy and curiosity-driven. Return a JSON array of strings only, "
            f"no extra commentary.{trend_context}"
        )
        raw = await chat_completion(system, user_prompt, temperature=0.9, max_tokens=400)
        parsed = _extract_json_array(raw)
        hooks = parsed if isinstance(parsed, list) else [h.strip('- ').strip() for h in raw.split('\n') if h.strip()]
        hooks = [str(h).strip() for h in hooks if str(h).strip()][: payload.count] or [raw.strip()]

        asset = {
            'id': str(uuid.uuid4()), 'user_id': user['id'], 'kind': 'viral_hooks',
            'niche': payload.niche, 'language': payload.language, 'hooks': hooks,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.creator_assets.insert_one(asset)
        asset.pop('_id', None)
        return asset
    except LLMServiceUnavailable:
        await refund(user['id'], 'viral_hooks', reason='generation_failed')
        raise HTTPException(status_code=503, detail='AI service temporarily unavailable. Please try again shortly.')
    except Exception:
        await refund(user['id'], 'viral_hooks', reason='generation_failed')
        raise


# ===== Meme & Story Mode (Pillar 1: faceless/story channels) =====
class MemeModeIn(BaseModel):
    source_text: str = Field(..., min_length=10, max_length=4000,
                             description="Reddit story, historical fact, or any long text to adapt")
    style: str = 'story'  # story | meme | documentary
    scenes: int = Field(6, ge=2, le=12)
    language: str = 'hinglish'


@router.post('/meme-mode')
async def meme_mode(payload: MemeModeIn, user=Depends(get_current_user)):
    """Turn a long source text into a vertical video storyboard (visual + caption per scene)."""
    ok, msg, _ = await deduct(user['id'], 'meme_mode')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    try:
        system = (
            "You are a short-form video storyboard writer for faceless entertainment "
            "channels (motivational, history, horror, meme pages). Output structured, "
            "cinematic, retention-optimized scenes."
        )
        user_prompt = (
            f"Turn the source below into a {payload.scenes}-scene vertical video storyboard "
            f"for '{payload.style}' content in {payload.language}. For each scene provide a "
            f"one-line visual description and a short on-screen caption under 8 words. "
            f"Return a JSON array of objects with keys: scene (int), visual (str), caption (str). "
            f"Source:\n{payload.source_text}"
        )
        raw = await chat_completion(system, user_prompt, temperature=0.8, max_tokens=900)
        storyboard = _extract_json_array(raw)
        if not isinstance(storyboard, list):
            storyboard = [{'scene': i + 1, 'visual': line.strip('- ').strip(), 'caption': ''}
                          for i, line in enumerate(raw.split('\n')) if line.strip()][: payload.scenes]

        asset = {
            'id': str(uuid.uuid4()), 'user_id': user['id'], 'kind': 'meme_mode',
            'style': payload.style, 'language': payload.language,
            'source_text': payload.source_text, 'storyboard': storyboard,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.creator_assets.insert_one(asset)
        asset.pop('_id', None)
        return asset
    except LLMServiceUnavailable:
        await refund(user['id'], 'meme_mode', reason='generation_failed')
        raise HTTPException(status_code=503, detail='AI service temporarily unavailable. Please try again shortly.')
    except Exception:
        await refund(user['id'], 'meme_mode', reason='generation_failed')
        raise
