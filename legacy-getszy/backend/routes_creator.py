"""Creator OS REST routes - scripts, trends, hooks, viral scoring, repurpose, providers."""
import json
import os
import io
import re
import uuid
import logging
import functools
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from PIL import Image, ImageDraw, ImageFont

from auth import get_current_user, get_current_admin
from db import db
from creator.scripts import generate as gen_script, score_hook, viral_score, FORMATS
from creator.trends import predict as predict_trends, competitor_gap
from creator.providers import readiness, active_provider
from credits import deduct, refund
from llm_provider import chat_completion, LLMServiceUnavailable
from routes_media import AUDIO_CACHE_DIR

logger = logging.getLogger('getszy.creator')
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


# ============================================================
#  Thumbnail Generator + CTR Predictor
# ============================================================
class ThumbnailIn(BaseModel):
    topic: str = Field(..., min_length=4, max_length=300)
    count: int = Field(5, ge=1, le=8)


def _creator_cache():
    from pathlib import Path as _P
    import os as _os
    d = _P(_os.environ.get('MEDIA_CACHE_DIR', str(_P(__file__).resolve().parent / 'media_cache')))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _render_thumbnail(bg_path: str, headline: str, subtext: str, accent: str = '#FF2D55') -> Optional[str]:
    """Composite a bold YouTube-style thumbnail (headline + subtext + arrow)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import os
        base = Image.open(bg_path).convert('RGB').resize((1280, 720))
        base = base.convert('RGBA')
        overlay = Image.new('RGBA', base.size, (0, 0, 0, 120))
        base = Image.alpha_composite(base, overlay).convert('RGB')
        draw = ImageDraw.Draw(base)
        font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
        fbig = ImageFont.truetype(font_path, 86) if os.path.exists(font_path) else ImageFont.load_default()
        fsmall = ImageFont.truetype(font_path, 40) if os.path.exists(font_path) else ImageFont.load_default()

        def _outline(txt, xy, font, fill, stroke):
            draw.text((xy[0] - 2, xy[1]), txt, font=font, fill=stroke)
            draw.text((xy[0] + 2, xy[1]), txt, font=font, fill=stroke)
            draw.text((xy[0], xy[1] - 2), txt, font=font, fill=stroke)
            draw.text((xy[0], xy[1] + 2), txt, font=font, fill=stroke)
            draw.text(xy, txt, font=font, fill=fill)

        # Headline (wrapped to 2 lines)
        words = headline.split()
        lines, cur = [], ''
        for w in words:
            if len(cur + ' ' + w) > 18:
                lines.append(cur); cur = w
            else:
                cur = (cur + ' ' + w).strip()
        if cur:
            lines.append(cur)
        y = 120
        for ln in lines[:2]:
            _outline(ln, (80, y), fbig, 'white', 'black')
            y += 96
        if subtext:
            _outline(subtext, (80, y + 10), fsmall, accent, 'black')
        # Red arrow (bottom-right)
        draw.polygon([(1080, 600), (1180, 600), (1130, 680)], fill=accent, outline='white')
        out_id = str(uuid.uuid4())
        out_p = _creator_cache() / f'{out_id}.jpg'
        base.save(out_p, 'JPEG', quality=90)
        return f'/api/media/file/{out_id}.jpg'
    except Exception as e:
        logger.warning('thumbnail render failed: %s', e)
        return None


@router.post('/thumbnail')
async def thumbnail(payload: ThumbnailIn, user=Depends(get_current_user)):
    ok, msg, _ = await deduct(user['id'], 'creator_thumbnail')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    try:
        system = (
            "You are a YouTube thumbnail strategist. Given a video topic, design "
            f"{payload.count} distinct, high-CTR thumbnail concepts. Each must grab "
            "attention in <1 second. Return STRICT JSON array. Each item: "
            '{"headline": bold short text (<=8 words, with a curiosity/gap), '
            '"subtext": tiny supporting line (<=5 words), '
            '"accent": hex color for emphasis (e.g. #FF2D55), '
            '"ctr_score": integer 0-100 predicted click-through, '
            '"reason": one line why it wins}. No markdown.'
        )
        raw = await chat_completion(system=system, user=f"Topic: {payload.topic}", temperature=0.7, max_tokens=1200)
        variants = _extract_json_array(raw)
        if not isinstance(variants, list) or not variants:
            raise ValueError('bad llm output')
    except Exception as e:
        await refund(user['id'], 'creator_thumbnail', reason='generation_failed')
        raise HTTPException(status_code=502, detail=f'thumbnail planning failed: {e}')

    results = []
    for v in variants[:payload.count]:
        headline = (v.get('headline') or payload.topic)[:60]
        subtext = (v.get('subtext') or '')[:40]
        accent = v.get('accent') or '#FF2D55'
        img_url = None
        try:
            from stock_media import search_stock_images
            from video.visuals import fetch_scene_image
            imgs = await search_stock_images(f"{payload.topic} {headline}", 1)
            bg = imgs[0] if imgs else await fetch_scene_image(headline, orientation='16:9')
            bg_path = None
            if isinstance(bg, str):
                if bg.startswith('http'):
                    import httpx
                    async with httpx.AsyncClient(timeout=45) as c:
                        r = await c.get(bg)
                        if r.status_code == 200:
                            p = _creator_cache() / f'bg_{uuid.uuid4().hex}.jpg'
                            p.write_bytes(r.content); bg_path = str(p)
                elif os.path.exists(bg):
                    bg_path = bg
            if bg_path:
                img_url = _render_thumbnail(bg_path, headline, subtext, accent)
        except Exception as e:
            logger.warning('thumb bg failed: %s', e)
        results.append({
            'headline': headline, 'subtext': subtext, 'accent': accent,
            'ctr_score': int(v.get('ctr_score', 50)), 'reason': v.get('reason', ''),
            'image_url': img_url,
        })
    asset = {
        'id': str(uuid.uuid4()), 'user_id': user['id'], 'kind': 'thumbnail',
        'topic': payload.topic, 'variants': results,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.creator_assets.insert_one(asset)
    asset.pop('_id', None)
    return asset


# ============================================================
#  Sponsorship Placement Finder
# ============================================================
class SponsorIn(BaseModel):
    script: str = Field(..., min_length=20, max_length=6000)
    brand: str = Field(..., min_length=1, max_length=100)
    product: str = Field('', max_length=200)


@router.post('/sponsorship')
async def sponsorship(payload: SponsorIn, user=Depends(get_current_user)):
    ok, msg, _ = await deduct(user['id'], 'creator_sponsor')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    system = (
        "You are a brand-deal editor. Given a video script and a sponsoring brand/product, "
        "find the single most NATURAL place to weave in the sponsorship so it feels like part "
        "of the story (a joke, a demo, or a lesson) rather than an ad break. "
        "Return STRICT JSON: {\"insertion_point\": short description of where, "
        "\"integrated_script\": the FULL revised script with the sponsorship woven in naturally, "
        "\"cta\": the call-to-action line, \"rationale\": why this spot converts.}"
    )
    user_msg = f"Brand: {payload.brand}\nProduct: {payload.product}\n\nScript:\n{payload.script}"
    try:
        raw = await chat_completion(system=system, user=user_msg, temperature=0.5, max_tokens=2500)
        data = _extract_json_object(raw)
        if not isinstance(data, dict):
            raise ValueError('bad json')
    except Exception as e:
        await refund(user['id'], 'creator_sponsor', reason='generation_failed')
        raise HTTPException(status_code=502, detail=f'sponsorship planning failed: {e}')
    data['brand'] = payload.brand
    data['product'] = payload.product
    asset = {'id': str(uuid.uuid4()), 'user_id': user['id'], 'kind': 'sponsorship',
             'brand': payload.brand, 'product': payload.product, 'data': data,
             'created_at': datetime.now(timezone.utc).isoformat()}
    await db.creator_assets.insert_one(asset)
    asset.pop('_id', None)
    return asset


# ============================================================
#  Multi-language Auto-Dubbing
# ============================================================
DUB_VOICES = {
    'tamil': 'ta-IN-PallaviNeural', 'telugu': 'te-IN-ShrutiNeural', 'marathi': 'mr-IN-AarohiNeural',
    'bengali': 'bn-IN-TanishaaNeural', 'hindi': 'hi-IN-SwaraNeural', 'english': 'en-IN-NeerjaNeural',
    'gujarati': 'gu-IN-DhwaniNeural', 'kannada': 'kn-IN-SapnaNeural', 'malayalam': 'ml-IN-SobhanaNeural',
    'punjabi': 'pa-IN-VaaniNeural',
}


class DubIn(BaseModel):
    text: str = Field(..., min_length=10, max_length=6000)
    languages: List[str] = ['tamil', 'telugu', 'marathi', 'bengali']


@router.post('/dub')
async def dub(payload: DubIn, user=Depends(get_current_user)):
    ok, msg, _ = await deduct(user['id'], 'creator_dub')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    from video.tts import synth
    out = []
    for lang in payload.languages:
        voice = DUB_VOICES.get(lang.lower(), 'hi-IN-SwaraNeural')
        try:
            translated = await chat_completion(
                system=f"Translate the following script to {lang} (natural, spoken style, keep meaning). Return ONLY the translated text.",
                user=payload.text, temperature=0.3, max_tokens=3000)
            translated = (translated or '').strip()
            if not translated:
                continue
            aid = str(uuid.uuid4())
            apath = AUDIO_CACHE_DIR / f'{aid}.mp3'
            await synth(translated[:4000], str(apath), voice=voice)
            out.append({'language': lang, 'voice': voice, 'text': translated,
                        'audio_url': f'/api/media/audio/{aid}.mp3'})
        except Exception as e:
            logger.warning('dub %s failed: %s', lang, e)
    if not out:
        await refund(user['id'], 'creator_dub', reason='generation_failed')
        raise HTTPException(status_code=502, detail='dubbing failed for all languages')
    asset = {'id': str(uuid.uuid4()), 'user_id': user['id'], 'kind': 'dub', 'tracks': out,
             'created_at': datetime.now(timezone.utc).isoformat()}
    await db.creator_assets.insert_one(asset)
    asset.pop('_id', None)
    return asset


# ============================================================
#  Comment -> Content Idea
# ============================================================
class CommentIdeaIn(BaseModel):
    comments: str = Field(..., min_length=10, max_length=6000)
    topic: str = Field('', max_length=200)


@router.post('/comment-ideas')
async def comment_ideas(payload: CommentIdeaIn, user=Depends(get_current_user)):
    ok, msg, _ = await deduct(user['id'], 'creator_idea')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    system = (
        "You are a YouTube strategist. Given a creator's top comments, find the most "
        "engaging follow-up video idea that answers the audience's burning question or "
        "curiosity. Return STRICT JSON: {\"idea\": one-line concept, \"title\": clickable "
        "title, \"angle\": why it will perform, \"script_outline\": 4-6 bullet points}."
    )
    user_msg = f"Topic context: {payload.topic}\n\nComments:\n{payload.comments}"
    try:
        raw = await chat_completion(system=system, user=user_msg, temperature=0.6, max_tokens=1500)
        data = _extract_json_object(raw)
        if not isinstance(data, dict):
            raise ValueError('bad json')
    except Exception as e:
        await refund(user['id'], 'creator_idea', reason='generation_failed')
        raise HTTPException(status_code=502, detail=f'idea generation failed: {e}')
    asset = {'id': str(uuid.uuid4()), 'user_id': user['id'], 'kind': 'comment_idea',
             'topic': payload.topic, 'data': data,
             'created_at': datetime.now(timezone.utc).isoformat()}
    await db.creator_assets.insert_one(asset)
    asset.pop('_id', None)
    return asset


# ============================================================
#  Content Funnel (one topic -> many formats)
# ============================================================
class FunnelIn(BaseModel):
    topic: str = Field(..., min_length=4, max_length=300)
    languages: List[str] = ['hinglish']


@router.post('/funnel')
async def funnel(payload: FunnelIn, user=Depends(get_current_user)):
    ok, msg, _ = await deduct(user['id'], 'creator_funnel')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    system = (
        "You are a multi-platform content strategist. Given ONE topic, produce a full "
        "content funnel. Return STRICT JSON: {\"youtube\": long-form documentary script "
        "(markdown, ~800 words), \"reels\": array of 5 vertical short ideas (each with hook + caption), "
        "\"thread\": array of ~12 tweet texts, \"linkedin\": a 300-word professional article}. "
        "Make each platform-appropriate."
    )
    try:
        raw = await chat_completion(system=system, user=f"Topic: {payload.topic}", temperature=0.6, max_tokens=3500)
        data = _extract_json_object(raw)
        if not isinstance(data, dict):
            raise ValueError('bad json')
    except Exception as e:
        await refund(user['id'], 'creator_funnel', reason='generation_failed')
        raise HTTPException(status_code=502, detail=f'funnel generation failed: {e}')
    asset = {'id': str(uuid.uuid4()), 'user_id': user['id'], 'kind': 'funnel',
             'topic': payload.topic, 'data': data,
             'created_at': datetime.now(timezone.utc).isoformat()}
    await db.creator_assets.insert_one(asset)
    asset.pop('_id', None)
    return asset


def _extract_json_object(s):
    try:
        s = s.strip()
        if '```' in s:
            s = s[s.find('{') if '{' in s else s.find('['):]
            end = s.rfind('}') if '}' in s else s.rfind(']')
            s = s[:end + 1]
        return json.loads(s)
    except Exception:
        return None


class MentorIn(BaseModel):
    goal: str = Field(..., min_length=4, max_length=400)
    niche: str = Field(default='', max_length=120)
    current_subs: int = 0
    current_views: int = 0
    time_per_week: str = '5-10 hours'


@router.post('/mentor')
async def mentor(payload: MentorIn, user=Depends(get_current_user)):
    ok, msg, _ = await deduct(user['id'], 'creator_mentor')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    system = (
        "You are an elite YouTube growth mentor (think MrBeast's strategist). Given a "
        "creator's situation, give brutally honest, actionable advice. Return STRICT JSON: "
        "{\"audit\": one-paragraph honest assessment, \"top3_mistakes\": array of 3 strings, "
        "\"plan_30d\": array of ~10 day-by-day actions (string), \"first_3_videos\": array of 3 "
        "video concepts (each: title + why_it_wins), \"monetization\": today-you-can-do steps}. "
        "Be specific, India/mobile-creator aware, no fluff."
    )
    user_prompt = (
        f"Goal: {payload.goal}\nNiche: {payload.niche or 'general'}\n"
        f"Current subs: {payload.current_subs}\nCurrent avg views: {payload.current_views}\n"
        f"Time/week: {payload.time_per_week}"
    )
    try:
        raw = await chat_completion(system=system, user=user_prompt, temperature=0.5, max_tokens=3000)
        data = _extract_json_object(raw)
        if not isinstance(data, dict):
            raise ValueError('bad json')
    except Exception as e:
        await refund(user['id'], 'creator_mentor', reason='generation_failed')
        raise HTTPException(status_code=502, detail=f'mentor generation failed: {e}')
    asset = {'id': str(uuid.uuid4()), 'user_id': user['id'], 'kind': 'mentor',
             'data': data, 'created_at': datetime.now(timezone.utc).isoformat()}
    await db.creator_assets.insert_one(asset)
    asset.pop('_id', None)
    return asset


class InteractiveIn(BaseModel):
    topic: str = Field(..., min_length=4, max_length=300)
    age_group: str = '13+'
    genre: str = 'thriller'
    episodes: int = 3


@router.post('/interactive')
async def interactive(payload: InteractiveIn, user=Depends(get_current_user)):
    ok, msg, _ = await deduct(user['id'], 'creator_interactive')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    system = (
        "You are a narrative game designer. Build an interactive choose-your-own-path story. "
        "Return STRICT JSON: {\"premise\": one paragraph, \"episode_plan\": array of N episode "
        "titles, \"scene_1\": {\"narrative\": text, \"choices\": [{\"label\": string, \"outcome\": "
        "text, \"next\": \"scene_2\" or \"END\"}]}}. Provide scene_1 fully and outline scene_2 as "
        "{\"narrative_outline\": text, \"choices\": [...]}. Make it binge-worthy."
    )
    user_prompt = (
        f"Topic: {payload.topic}\nAge group: {payload.age_group}\nGenre: {payload.genre}\n"
        f"Episodes: {payload.episodes}"
    )
    try:
        raw = await chat_completion(system=system, user=user_prompt, temperature=0.8, max_tokens=3000)
        data = _extract_json_object(raw)
        if not isinstance(data, dict):
            raise ValueError('bad json')
    except Exception as e:
        await refund(user['id'], 'creator_interactive', reason='generation_failed')
        raise HTTPException(status_code=502, detail=f'interactive generation failed: {e}')
    asset = {'id': str(uuid.uuid4()), 'user_id': user['id'], 'kind': 'interactive',
             'data': data, 'created_at': datetime.now(timezone.utc).isoformat()}
    await db.creator_assets.insert_one(asset)
    asset.pop('_id', None)
    return asset


class DigitalTwinIn(BaseModel):
    samples: List[str] = Field(..., min_length=1, max_length=8)
    topic: str = Field(..., min_length=4, max_length=300)
    platform: str = 'youtube'


@router.post('/digital-twin')
async def digital_twin(payload: DigitalTwinIn, user=Depends(get_current_user)):
    ok, msg, _ = await deduct(user['id'], 'creator_twin')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    cleaned = [s.strip()[:4000] for s in payload.samples if s.strip()]
    if not cleaned:
        raise HTTPException(status_code=400, detail='Provide at least one non-empty sample')
    samples_block = "\n\n---\n\n".join(f"SAMPLE {i+1}:\n{s}" for i, s in enumerate(cleaned))
    profile_system = (
        "You are a creator-style analyst. From the provided past content, extract the "
        "creator's 'style DNA'. Return STRICT JSON: {\"voice\": short description, "
        "\"hooks\": 3 typical opening patterns, \"pacing\": how fast/slow, \"vocabulary\": "
        "typical words/phrases, \"structure\": how videos are organized, \"do_and_dont\": "
        "2-3 rules this creator always follows}. Be specific and evidence-based."
    )
    gen_system = (
        "You are this creator's writing twin. Using the style DNA, write a NEW, original "
        "script for the given topic that sounds exactly like them. Return STRICT JSON: "
        "{\"title\": string, \"hook\": one opening line, \"script\": full script (markdown, "
        "with [VISUAL] cues), \"cta\": sign-off line}. Match their voice precisely."
    )
    try:
        raw_profile = await chat_completion(system=profile_system, user=samples_block, temperature=0.3, max_tokens=1500)
        profile = _extract_json_object(raw_profile)
        if not isinstance(profile, dict):
            raise ValueError('bad profile json')
        raw_script = await chat_completion(
            system=gen_system,
            user=f"STYLE DNA:\n{json.dumps(profile, ensure_ascii=False)}\n\nTOPIC: {payload.topic}\nPLATFORM: {payload.platform}",
            temperature=0.7, max_tokens=2500)
        script_data = _extract_json_object(raw_script)
        if not isinstance(script_data, dict):
            raise ValueError('bad script json')
    except Exception as e:
        await refund(user['id'], 'creator_twin', reason='generation_failed')
        raise HTTPException(status_code=502, detail=f'digital twin failed: {e}')
    out = {'style_profile': profile, 'generated': script_data,
           'topic': payload.topic, 'platform': payload.platform}
    asset = {'id': str(uuid.uuid4()), 'user_id': user['id'], 'kind': 'digital_twin',
             'data': out, 'created_at': datetime.now(timezone.utc).isoformat()}
    await db.creator_assets.insert_one(asset)
    asset.pop('_id', None)
    return asset


class CalendarIn(BaseModel):
    niche: str = Field(..., min_length=3, max_length=120)
    goal: str = Field(default='grow audience', max_length=200)
    frequency: int = Field(default=3, ge=1, le=14)
    days: int = Field(default=30, ge=7, le=90)


@router.post('/calendar')
async def calendar(payload: CalendarIn, user=Depends(get_current_user)):
    ok, msg, _ = await deduct(user['id'], 'creator_calendar')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    count = payload.frequency * (payload.days // 7)
    system = (
        "You are a YouTube content strategist. Build a realistic posting calendar. "
        'Return STRICT JSON: {"theme": overall content pillar, "entries": [array of '
        + str(count) + ' items]}. Each entry: {"day": int, "date": "Day N", '
        '"platform": one of youtube/reels/linkedin/thread, "title": string, '
        '"format": e.g. tutorial/reaction/list, "hook": one line, '
        '"best_time": "Fri 6pm IST", "ctr_tip": one optimization tip}. '
        "Spread formats, keep it sustainable."
    )
    user_prompt = f"Niche: {payload.niche}\nGoal: {payload.goal}\nFrequency: {payload.frequency}/week\nDuration: {payload.days} days"
    try:
        raw = await chat_completion(system=system, user=user_prompt, temperature=0.6, max_tokens=3500)
        data = _extract_json_object(raw)
        if not isinstance(data, dict) or not data.get('entries'):
            raise ValueError('bad json')
    except Exception as e:
        await refund(user['id'], 'creator_calendar', reason='generation_failed')
        raise HTTPException(status_code=502, detail=f'calendar generation failed: {e}')
    asset = {'id': str(uuid.uuid4()), 'user_id': user['id'], 'kind': 'calendar',
             'data': data, 'created_at': datetime.now(timezone.utc).isoformat()}
    await db.creator_assets.insert_one(asset)
    asset.pop('_id', None)
    return asset



