"""SamurAIGPT / Open-Generative-AI media suite - REST surface (FREE only).

Endpoints added here are strictly additive: they never modify the existing
``routes_video`` / ``routes_images`` / ``routes_voice`` flows, so there is zero
regression risk for the features already in production.

Scope of this first slice:
- ``GET  /media-suite/providers``  - live free-media status (monitoring + badge)
- ``POST /media-suite/design``     - Open-AI-Design-Agent: banner / poster / social
- ``GET  /media-suite/skills``     - CLI-agent skill catalog (Claude Code/Codex/Gemini)

Shorts generation and the Vibe-Workflow executor arrive in follow-up PRs that
extend this same router.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from db import db
from media_providers import media_provider_info, FREE_ONLY_MEDIA
from image_gen import generate_image

router = APIRouter(prefix='/media-suite', tags=['media-suite'])

# Catalog of media tools exposed as terminal CLI-agent skills. Each entry tells
# an agent (Claude Code / Codex / Gemini CLI) what it can call and how.
SKILLS = [
    {
        'name': 'generate_image',
        'description': 'Generate an image from a text prompt using free FLUX/Pollinations.',
        'endpoint': '/media-suite/design',
        'method': 'POST',
        'params': {'prompt': 'string', 'kind': 'poster|banner|social|thumbnail', 'aspect': '1:1|16:9|9:16|4:5'},
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


@router.get('/skills')
async def skills():
    """Catalog of media tools for terminal CLI agents."""
    return {'free_only': FREE_ONLY_MEDIA, 'skills': SKILLS}


@router.post('/design')
async def design(payload: DesignIn, user=Depends(get_current_user)):
    if not FREE_ONLY_MEDIA:
        raise HTTPException(status_code=403, detail='Media suite is free-only')
    if len(payload.prompt.strip()) < 3:
        raise HTTPException(status_code=400, detail='Prompt too short')
    width, height = _ASPECT_SIZE.get(payload.aspect, (1024, 1024))
    # Reuses the existing free image pipeline (HF FLUX + Pollinations fallback).
    result = await generate_image(payload.prompt, width, height)
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
