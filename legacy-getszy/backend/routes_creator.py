"""Creator OS REST routes - scripts, trends, hooks, viral scoring, repurpose, providers."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user, get_current_admin
from db import db
from creator.scripts import generate as gen_script, score_hook, viral_score, FORMATS
from creator.trends import predict as predict_trends, competitor_gap
from creator.providers import readiness, active_provider
from credits import deduct, refund

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
