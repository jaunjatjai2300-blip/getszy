"""SamurAIGPT / Open-Generative-AI media suite - REST surface (FREE only).

Endpoints added here are strictly additive: they never modify the existing
``routes_video`` / ``routes_images`` / ``routes_voice`` flows, so there is zero
regression risk for the features already in production.

Surfaces:
- ``GET  /media-suite/providers``   - live free-media status (monitoring + badge)
- ``GET  /media-suite/models``      - integrated free models (+ Fal.ai only if FAL_KEY set)
- ``GET  /media-suite/skills``      - CLI-agent skill catalog (Claude Code/Codex/Gemini)
- ``GET  /media-suite/design/formats`` - platform format dimensions
- ``POST /media-suite/design``      - Open-AI-Design-Agent: background image only
- ``POST /media-suite/design/compose`` - full composition (bg + title/CTA/logo/brand)
- ``GET  /media-suite/design/{asset_id}`` - owned asset (404 cross-user)
- ``POST /media-suite/workflow/run``  - Vibe-Workflow JSON-DAG executor
- ``POST /media-suite/shorts``        - Shorts/Reel generator (upload + YouTube URL)
"""
import base64
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel

from auth import get_current_user
from db import db
from media_providers import media_provider_info, FREE_ONLY_MEDIA
from media_models import generate_image_model, list_free_models
from media_workflow import run_graph, KNOWN_NODE_TYPES
from media_shorts import run_shorts
from media_design import compose_design, DESIGN_FORMATS

router = APIRouter(prefix='/media-suite', tags=['media-suite'])

# Catalog of media tools exposed as terminal CLI-agent skills. Each entry tells
# an agent (Claude Code / Codex / Gemini CLI) what it can call and how.
SKILLS = [
    {
        'name': 'generate_image',
        'description': 'Generate an image from a text prompt using free FLUX/Pollinations (or Fal.ai if configured).',
        'endpoint': '/media-suite/design',
        'method': 'POST',
        'params': {'prompt': 'string', 'kind': 'poster|banner|social|thumbnail', 'aspect': '1:1|16:9|9:16|4:5'},
    },
    {
        'name': 'compose_design',
        'description': 'Compose a professional platform graphic (IG post/story, Reel cover, YT thumbnail, poster, banner) from a background + title/CTA/logo/brand color.',
        'endpoint': '/media-suite/design/compose',
        'method': 'POST',
        'params': {'fmt': 'ig_post|ig_story|reel_cover|yt_thumb|yt_shorts_cover|poster|banner', 'title': 'string', 'subtitle': 'string', 'cta': 'string'},
    },
    {
        'name': 'text_to_speech',
        'description': 'Convert text to speech using free Edge-TTS.',
        'endpoint': '/ai/voice/tts',
        'method': 'POST',
    },
    {
        'name': 'transcribe',
        'description': 'Transcribe an audio/video file to text using free Whisper.',
        'endpoint': '/ai/voice/stt',
        'method': 'POST',
    },
    {
        'name': 'generate_video',
        'description': 'Generate a faceless video from a topic using free providers.',
        'endpoint': '/video/generate',
        'method': 'POST',
    },
    {
        'name': 'create_shorts',
        'description': 'Convert a long video (upload or YouTube URL) into vertical shorts with captions.',
        'endpoint': '/media-suite/shorts',
        'method': 'POST',
    },
    {
        'name': 'run_workflow',
        'description': 'Execute a Vibe-Workflow JSON DAG of media nodes.',
        'endpoint': '/media-suite/workflow',
        'method': 'POST',
    },
]


class DesignIn(BaseModel):
    prompt: str
    kind: str = 'poster'          # poster | banner | social | thumbnail
    aspect: str = '1:1'           # 1:1 | 16:9 | 9:16 | 4:5
    model_id: Optional[str] = None  # free model id from /media-suite/models


_ASPECT_SIZE = {
    '1:1': (1024, 1024),
    '16:9': (1280, 720),
    '9:16': (720, 1280),
    '4:5': (1024, 1280),
}


@router.get('/providers')
async def providers():
    """Cheap, public-by-design health surface for the media suite."""
    return media_provider_info()


@router.get('/models')
async def models():
    """List the integrated FREE models (HF free tier + Pollinations + Edge-TTS)."""
    return {'free_only': FREE_ONLY_MEDIA, 'models': list_free_models()}


@router.get('/skills')
async def skills():
    """Catalog of media tools for terminal CLI agents."""
    return {'free_only': FREE_ONLY_MEDIA, 'skills': SKILLS}


@router.post('/workflow/run')
async def workflow_run(payload: dict, bg: BackgroundTasks, user=Depends(get_current_user)):
    """Execute a Vibe-Workflow JSON DAG. Returns a job id; poll /workflow/{id}."""
    graph = payload.get('graph') if isinstance(payload, dict) else None
    if not graph or not graph.get('nodes'):
        raise HTTPException(status_code=400, detail='graph with nodes required')
    for node in graph.get('nodes', []):
        if node.get('type') not in KNOWN_NODE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f'unsupported node type: {node.get("type")!r} (supported: {", ".join(KNOWN_NODE_TYPES)})',
            )
    try:
        from media_workflow import topo_sort
        topo_sort(graph.get('nodes', []), graph.get('edges', []))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f'invalid graph: {e}')
    job_id = str(uuid.uuid4())
    await db.media_workflows.insert_one({
        'id': job_id, 'user_id': user['id'], 'graph': graph,
        'status': 'queued', 'percent': 0, 'outputs': {},
        'created_at': datetime.now(timezone.utc).isoformat(),
    })
    bg.add_task(_workflow_worker, job_id, graph)
    return {'job_id': job_id, 'status': 'queued'}


@router.get('/workflow/{job_id}')
async def workflow_status(job_id: str, user=Depends(get_current_user)):
    doc = await db.media_workflows.find_one({'id': job_id, 'user_id': user['id']}, {'_id': 0})
    if not doc:
        raise HTTPException(status_code=404, detail='not found')
    return doc


async def _workflow_worker(job_id: str, graph: dict):
    try:
        outputs = await run_graph(graph)
        await db.media_workflows.update_one(
            {'id': job_id}, {'$set': {'status': 'completed', 'percent': 100, 'outputs': outputs}}
        )
    except Exception as e:  # noqa: BLE001
        await db.media_workflows.update_one(
            {'id': job_id}, {'$set': {'status': 'failed', 'error': str(e)}}
        )


@router.post('/shorts')
async def create_shorts(
    youtube_url: str = Form(None),
    file: UploadFile = File(None),
    orientation: str = '9:16',
    bg: BackgroundTasks = None,
    user=Depends(get_current_user),
):
    """Shorts/Reel generator. Primary = file upload; also accepts a YouTube URL
    (fetched internally via yt-dlp). Returns a job id; poll /shorts/{id}."""
    source = None
    if file is not None:
        data = await file.read()
        if data:
            source = data
    elif youtube_url:
        source = youtube_url
    if source is None:
        raise HTTPException(status_code=400, detail='Provide a video file upload or youtube_url')
    job_id = str(uuid.uuid4())
    await db.media_shorts.insert_one({
        'id': job_id, 'user_id': user['id'], 'orientation': orientation,
        'status': 'queued', 'created_at': datetime.now(timezone.utc).isoformat(),
    })
    if bg is not None:
        bg.add_task(_shorts_worker, job_id, source, {'orientation': orientation})
    else:
        await _shorts_worker(job_id, source, {'orientation': orientation})
    return {'job_id': job_id, 'status': 'queued'}


@router.get('/shorts/{job_id}')
async def shorts_status(job_id: str, user=Depends(get_current_user)):
    doc = await db.media_shorts.find_one({'id': job_id, 'user_id': user['id']}, {'_id': 0})
    if not doc:
        raise HTTPException(status_code=404, detail='not found')
    return doc


async def _shorts_worker(job_id: str, source, params: dict):
    result = await run_shorts(source, params)
    await db.media_shorts.update_one(
        {'id': job_id},
        {'$set': {'status': 'completed' if 'output' in result else 'failed', 'result': result}}
    )


@router.post('/design')
async def design(payload: DesignIn, user=Depends(get_current_user)):
    if not FREE_ONLY_MEDIA:
        raise HTTPException(status_code=403, detail='Media suite is free-only')
    if len(payload.prompt.strip()) < 3:
        raise HTTPException(status_code=400, detail='Prompt too short')
    width, height = _ASPECT_SIZE.get(payload.aspect, (1024, 1024))
    # Reuses the free image pipeline (specific free model or HF FLUX + Pollinations).
    result = await generate_image_model(payload.prompt, payload.model_id, width, height)
    if 'error' in result:
        raise HTTPException(status_code=502, detail=result['error'])
    record = {
        'id': str(uuid.uuid4()),
        'user_id': user['id'],
        'prompt': payload.prompt,
        'kind': payload.kind,
        'aspect': payload.aspect,
        'provider': result.get('provider'),
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.media_designs.insert_one(record)
    return {
        'image': result.get('image'),
        'provider': result.get('provider'),
        'id': record['id'],
    }


@router.get('/design/formats')
async def design_formats():
    """Platform format dimensions for the Design Agent UI."""
    return {
        'formats': [
            {'id': fid, 'label': DESIGN_FORMATS[fid][2], 'width': DESIGN_FORMATS[fid][0], 'height': DESIGN_FORMATS[fid][1]}
            for fid in DESIGN_FORMATS
        ]
    }


@router.post('/design/compose')
async def design_compose(
    fmt: str = Form('ig_post'),
    title: str = Form(''),
    subtitle: str = Form(''),
    cta: str = Form(''),
    prompt: str = Form(''),
    model_id: Optional[str] = Form(None),
    primary_color: str = Form(''),
    secondary_color: str = Form(''),
    background: UploadFile = File(None),
    logo: UploadFile = File(None),
    user=Depends(get_current_user),
):
    """Open-AI-Design-Agent: compose a professional platform graphic.

    Background is either an uploaded image or, if absent, generated from ``prompt``
    via the free model registry (Fal.ai only when FAL_KEY is set). The composed PNG
    is stored under the caller's user id and served from /design/{asset_id} with
    ownership enforced (cross-user requests get 404).
    """
    if not FREE_ONLY_MEDIA:
        raise HTTPException(status_code=403, detail='Media suite is free-only')

    bg_bytes: Optional[bytes] = None
    provider = 'upload'
    if background is not None:
        data = await background.read()
        if data:
            bg_bytes = data
    if bg_bytes is None:
        if len((prompt or '').strip()) < 3:
            raise HTTPException(status_code=400, detail='Provide a background image or a generation prompt (min 3 chars)')
        w, h = DESIGN_FORMATS.get(fmt, (1080, 1080))[:2]
        gen = await generate_image_model(prompt.strip(), model_id, w, h)
        if 'error' in gen:
            # Safe, customer-facing error — never leak provider stack traces.
            raise HTTPException(status_code=502, detail=f'Background generation failed: {gen["error"]}')
        provider = gen.get('provider', 'huggingface')
        bg_bytes = base64.b64decode(gen['image'])

    logo_bytes: Optional[bytes] = None
    if logo is not None:
        ldata = await logo.read()
        if ldata:
            logo_bytes = ldata

    try:
        png, meta = compose_design(
            bg_bytes,
            title=title,
            subtitle=subtitle,
            cta=cta,
            logo=logo_bytes,
            primary_color=primary_color,
            secondary_color=secondary_color,
            fmt=fmt,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    asset_id = str(uuid.uuid4())
    record = {
        'id': asset_id,
        'user_id': user['id'],
        'fmt': fmt,
        'title': title,
        'subtitle': subtitle,
        'cta': cta,
        'provider': provider,
        'png': base64.b64encode(png).decode(),
        'meta': meta,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.media_designs.insert_one(record)
    data_url = f'data:image/png;base64,{base64.b64encode(png).decode()}'
    return {
        'asset_id': asset_id,
        'format': fmt,
        'width': meta['width'],
        'height': meta['height'],
        'provider': provider,
        'status': 'ok',
        'image': data_url,
    }


@router.get('/design/{asset_id}')
async def design_asset(asset_id: str, user=Depends(get_current_user)):
    """Serve an owned design asset. Ownership is enforced by the user_id filter;
    a different user simply gets 404 (no IDOR / cross-user access)."""
    doc = await db.media_designs.find_one({'id': asset_id, 'user_id': user['id']}, {'_id': 0, 'png': 1})
    if not doc or not doc.get('png'):
        raise HTTPException(status_code=404, detail='not found')
    png = base64.b64decode(doc['png'])
    return Response(content=png, media_type='image/png', headers={'Cache-Control': 'private, max-age=3600'})


@router.get('/shorts/{job_id}/file')
async def shorts_file(job_id: str, user=Depends(get_current_user)):
    """Serve a completed shorts video. Ownership enforced via user_id; a different
    user gets 404 (no cross-user asset access)."""
    doc = await db.media_shorts.find_one({'id': job_id, 'user_id': user['id']}, {'_id': 0, 'result': 1})
    if not doc:
        raise HTTPException(status_code=404, detail='not found')
    out = (doc.get('result') or {}).get('output')
    if not out or not os.path.exists(out):
        raise HTTPException(status_code=404, detail='output not available')
    return FileResponse(out, media_type='video/mp4', filename=f'{job_id}.mp4')
