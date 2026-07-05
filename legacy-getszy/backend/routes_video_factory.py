"""AI Video Factory v2 — API routes.

- POST   /api/video-factory/project              — create new project from raw prompt (kicks off full chain in bg)
- GET    /api/video-factory/project/{id}         — get full project state
- GET    /api/video-factory/projects             — list user's projects
- POST   /api/video-factory/project/{id}/enhance — regenerate prompt enhancement
- POST   /api/video-factory/project/{id}/research
- POST   /api/video-factory/project/{id}/scripts — regenerate script variants
- POST   /api/video-factory/project/{id}/select-script  {script_id}
- POST   /api/video-factory/project/{id}/storyboard
- POST   /api/video-factory/project/{id}/hooks
- POST   /api/video-factory/project/{id}/visuals
- PATCH  /api/video-factory/project/{id}/scene/{scene_id}  — edit/lock/unlock a scene
- POST   /api/video-factory/project/{id}/scene/{scene_id}/regenerate
- DELETE /api/video-factory/project/{id}
"""
import uuid
import os
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from auth import get_current_user
from db import db
from video_factory.agents import (
    enhance_prompt, research_topic, generate_script_variants, generate_hooks,
    build_storyboard, plan_visuals, run_factory_chain,
)
from video_factory.renderer import generate_all_assets

logger = logging.getLogger('getszy.video_factory')
router = APIRouter(prefix='/video-factory', tags=['video-factory'])


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _project_or_404(project_id: str, user):
    p = await db.video_projects.find_one({'id': project_id, 'user_id': user['id']}, {'_id': 0})
    if not p:
        raise HTTPException(404, 'project not found')
    return p


async def _update(project_id: str, patch: dict):
    patch['updated_at'] = _iso()
    await db.video_projects.update_one({'id': project_id}, {'$set': patch})


# ============================================================
# Create + list + get + delete
# ============================================================
class CreateProjectIn(BaseModel):
    prompt: str = Field(..., min_length=8, max_length=1000)
    language: str = 'hinglish'
    title: Optional[str] = None
    auto_run: bool = True   # if true, kicks off full chain in background


@router.post('/project')
async def create_project(body: CreateProjectIn, background: BackgroundTasks, user=Depends(get_current_user)):
    pid = str(uuid.uuid4())
    doc = {
        'id': pid,
        'user_id': user['id'],
        'title': body.title or body.prompt[:60],
        'prompt_raw': body.prompt.strip(),
        'language': body.language,
        'status': 'created',
        'stages': {},   # enhanced / research / script_variants / hooks / storyboard / visual_plan
        'selected_script_id': None,
        'created_at': _iso(),
        'updated_at': _iso(),
    }
    await db.video_projects.insert_one(doc)
    doc.pop('_id', None)

    if body.auto_run:
        background.add_task(_run_chain_bg, pid, body.prompt.strip(), body.language, user['id'])
        doc['status'] = 'processing'
        await _update(pid, {'status': 'processing'})

    return doc


async def _run_chain_bg(project_id: str, raw_prompt: str, language: str, user_id: str):
    session_id = f'vf-{project_id}'
    await _update(project_id, {'status': 'processing'})
    try:
        result = await run_factory_chain(raw_prompt, language, session_id)
        patch = {
            'stages': result.get('stages', {}),
            'errors': result.get('errors', {}),
            'selected_script_id': result.get('selected_script_id'),
            'status': 'ready' if not result.get('errors') else 'partial',
        }
        await _update(project_id, patch)
    except Exception as e:
        await _update(project_id, {'status': 'error', 'errors': {'chain': str(e)[:300]}})


@router.get('/project/{project_id}')
async def get_project(project_id: str, user=Depends(get_current_user)):
    return await _project_or_404(project_id, user)


@router.get('/projects')
async def list_projects(user=Depends(get_current_user)):
    items = [p async for p in db.video_projects.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(50)]
    return {'items': items}


@router.delete('/project/{project_id}')
async def delete_project(project_id: str, user=Depends(get_current_user)):
    r = await db.video_projects.delete_one({'id': project_id, 'user_id': user['id']})
    if r.deleted_count == 0:
        raise HTTPException(404, 'not found')
    return {'ok': True}


# ============================================================
# Regenerate individual stages
# ============================================================
@router.post('/project/{project_id}/enhance')
async def re_enhance(project_id: str, user=Depends(get_current_user)):
    p = await _project_or_404(project_id, user)
    try:
        enhanced = await enhance_prompt(p['prompt_raw'], f'vf-{project_id}')
    except Exception as e:
        raise HTTPException(500, f'LLM error: {str(e)[:150]}')
    await _update(project_id, {f'stages.enhanced': enhanced})
    return enhanced


@router.post('/project/{project_id}/research')
async def re_research(project_id: str, user=Depends(get_current_user)):
    p = await _project_or_404(project_id, user)
    enhanced = (p.get('stages') or {}).get('enhanced')
    if not enhanced:
        raise HTTPException(400, 'Run enhance first')
    try:
        r = await research_topic(enhanced['enhanced_topic'], enhanced['angle'], f'vf-{project_id}')
    except Exception as e:
        raise HTTPException(500, f'LLM error: {str(e)[:150]}')
    await _update(project_id, {'stages.research': r})
    return r


@router.post('/project/{project_id}/scripts')
async def re_scripts(project_id: str, user=Depends(get_current_user)):
    p = await _project_or_404(project_id, user)
    stages = p.get('stages') or {}
    enhanced = stages.get('enhanced')
    research = stages.get('research') or {}
    if not enhanced:
        raise HTTPException(400, 'Run enhance first')
    try:
        variants = await generate_script_variants(
            enhanced['enhanced_topic'], enhanced['angle'],
            enhanced.get('estimated_duration_seconds', 300),
            research, p.get('language', 'hinglish'),
            f'vf-{project_id}'
        )
    except Exception as e:
        raise HTTPException(500, f'LLM error: {str(e)[:150]}')
    await _update(project_id, {'stages.script_variants': variants})
    return {'items': variants}


class SelectScriptIn(BaseModel):
    script_id: str


@router.post('/project/{project_id}/select-script')
async def select_script(project_id: str, body: SelectScriptIn, user=Depends(get_current_user)):
    p = await _project_or_404(project_id, user)
    variants = (p.get('stages') or {}).get('script_variants') or []
    if not any(v.get('id') == body.script_id for v in variants):
        raise HTTPException(404, 'script id not in variants')
    await _update(project_id, {'selected_script_id': body.script_id})
    return {'ok': True, 'selected_script_id': body.script_id}


@router.post('/project/{project_id}/hooks')
async def re_hooks(project_id: str, user=Depends(get_current_user)):
    p = await _project_or_404(project_id, user)
    enhanced = (p.get('stages') or {}).get('enhanced')
    if not enhanced:
        raise HTTPException(400, 'Run enhance first')
    variants = (p.get('stages') or {}).get('script_variants') or []
    style = next((v.get('style_id', 'viral') for v in variants if v.get('id') == p.get('selected_script_id')), 'viral')
    try:
        hooks = await generate_hooks(enhanced['enhanced_topic'], enhanced['angle'], style, f'vf-{project_id}')
    except Exception as e:
        raise HTTPException(500, f'LLM error: {str(e)[:150]}')
    await _update(project_id, {'stages.hooks': hooks})
    return {'items': hooks}


@router.post('/project/{project_id}/storyboard')
async def re_storyboard(project_id: str, user=Depends(get_current_user)):
    p = await _project_or_404(project_id, user)
    variants = (p.get('stages') or {}).get('script_variants') or []
    selected_id = p.get('selected_script_id')
    script = next((v for v in variants if v.get('id') == selected_id), (variants[0] if variants else None))
    if not script:
        raise HTTPException(400, 'No script yet — run /scripts first')
    enhanced = (p.get('stages') or {}).get('enhanced') or {}
    duration = enhanced.get('estimated_duration_seconds', 300)
    try:
        scenes = await build_storyboard(script.get('narration', ''), duration, f'vf-{project_id}')
    except Exception as e:
        raise HTTPException(500, f'LLM error: {str(e)[:150]}')
    await _update(project_id, {'stages.storyboard': scenes})
    return {'items': scenes}


@router.post('/project/{project_id}/visuals')
async def re_visuals(project_id: str, user=Depends(get_current_user)):
    p = await _project_or_404(project_id, user)
    scenes = (p.get('stages') or {}).get('storyboard') or []
    if not scenes:
        raise HTTPException(400, 'No storyboard yet — run /storyboard first')
    variants = (p.get('stages') or {}).get('script_variants') or []
    style = next((v.get('style_id', 'viral') for v in variants if v.get('id') == p.get('selected_script_id')), 'viral')
    try:
        plan = await plan_visuals(scenes, style, f'vf-{project_id}')
    except Exception as e:
        raise HTTPException(500, f'LLM error: {str(e)[:150]}')
    await _update(project_id, {'stages.visual_plan': plan})
    return {'items': plan}


# ============================================================
# Scene edit / lock / regenerate
# ============================================================
class ScenePatch(BaseModel):
    narration_chunk: Optional[str] = None
    visual_intent: Optional[str] = None
    duration_s: Optional[int] = None
    locked: Optional[bool] = None


@router.patch('/project/{project_id}/scene/{scene_id}')
async def edit_scene(project_id: str, scene_id: str, body: ScenePatch, user=Depends(get_current_user)):
    p = await _project_or_404(project_id, user)
    scenes = (p.get('stages') or {}).get('storyboard') or []
    idx = next((i for i, s in enumerate(scenes) if s.get('id') == scene_id), None)
    if idx is None:
        raise HTTPException(404, 'scene not found')
    patch = body.dict(exclude_unset=True)
    scenes[idx].update(patch)
    await _update(project_id, {'stages.storyboard': scenes})
    return scenes[idx]


@router.post('/project/{project_id}/scene/{scene_id}/regenerate')
async def regenerate_scene(project_id: str, scene_id: str, user=Depends(get_current_user)):
    """Regenerate visual plan for a single scene (respects locked flag on other scenes)."""
    p = await _project_or_404(project_id, user)
    scenes = (p.get('stages') or {}).get('storyboard') or []
    scene = next((s for s in scenes if s.get('id') == scene_id), None)
    if not scene:
        raise HTTPException(404, 'scene not found')
    if scene.get('locked'):
        raise HTTPException(400, 'Scene is locked — unlock first')
    variants = (p.get('stages') or {}).get('script_variants') or []
    style = next((v.get('style_id', 'viral') for v in variants if v.get('id') == p.get('selected_script_id')), 'viral')
    try:
        new_plan = await plan_visuals([scene], style, f'vf-{project_id}')
    except Exception as e:
        raise HTTPException(500, f'LLM error: {str(e)[:150]}')
    # merge into existing visual_plan
    plan = (p.get('stages') or {}).get('visual_plan') or []
    new_entry = new_plan[0] if new_plan else None
    if new_entry:
        found = False
        for i, e in enumerate(plan):
            if e.get('scene_index') == scene.get('index'):
                plan[i] = new_entry
                found = True
                break
        if not found:
            plan.append(new_entry)
        await _update(project_id, {'stages.visual_plan': plan})
    return {'scene_visual': new_entry}


# ============================================================
# Phase 22B: Asset generation & final video assembly
# ============================================================
class GenerateAssetsIn(BaseModel):
    orientation: str = '16:9'  # '16:9' | '9:16' | '1:1'


@router.post('/project/{project_id}/generate-assets')
async def generate_assets(project_id: str, body: GenerateAssetsIn, background: BackgroundTasks, user=Depends(get_current_user)):
    """Kick off image+voice+assembly in background. Poll project for status."""
    p = await _project_or_404(project_id, user)
    stages = p.get('stages') or {}
    if not stages.get('storyboard') or not stages.get('visual_plan'):
        raise HTTPException(400, 'storyboard + visual_plan required — run pipeline first')
    if p.get('render_status') in ('generating_images', 'generating_voice', 'assembling'):
        return {'ok': True, 'already_running': True, 'render_status': p.get('render_status')}
    await _update(project_id, {'render_status': 'queued', 'render_progress': 0, 'render_error': None})
    background.add_task(generate_all_assets, project_id, body.orientation)
    return {'ok': True, 'status': 'queued', 'poll_url': f'/api/video-factory/project/{project_id}'}


@router.get('/project/{project_id}/download')
async def download_final(project_id: str, user=Depends(get_current_user)):
    """Serve the final rendered video. Guards against tiny/corrupt files."""
    from fastapi.responses import FileResponse
    p = await _project_or_404(project_id, user)
    path = p.get('final_video_path')
    if not path or not os.path.exists(path):
        raise HTTPException(404, 'Video not rendered yet. Wait for render_status=complete before downloading.')
    try:
        size = os.path.getsize(path)
    except Exception:
        size = 0
    if size < 30_000:  # <30KB = corrupt/incomplete
        raise HTTPException(422, f'Rendered video is corrupt or incomplete ({size} bytes). Please re-generate.')
    return FileResponse(path, media_type='video/mp4', filename=f'{p.get("title","video")[:40]}.mp4')


@router.get('/project/{project_id}/scene-image/{scene_index}')
async def scene_image(project_id: str, scene_index: int, user=Depends(get_current_user)):
    """Serve a scene's rendered image for the UI."""
    from fastapi.responses import FileResponse
    p = await _project_or_404(project_id, user)
    scenes = (p.get('stages') or {}).get('storyboard') or []
    scene = next((s for s in scenes if s.get('index') == scene_index), None)
    if not scene or not scene.get('image_path') or not os.path.exists(scene['image_path']):
        raise HTTPException(404, 'image not generated yet')
    return FileResponse(scene['image_path'], media_type='image/jpeg')
