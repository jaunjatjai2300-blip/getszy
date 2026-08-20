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
from video_factory.renderer import generate_all_assets, _cleanup_project_files
from credits import deduct, refund

logger = logging.getLogger('getszy.video_factory')
router = APIRouter(prefix='/video-factory', tags=['video-factory'])

# Bounds a single factory chain run so a misbehaving/unreachable AI provider can
# never leave a project stuck at "processing" forever. Must be >= the sum of the
# per-provider httpx timeouts in llm_provider.py, but small enough to fail fast.
CHAIN_TIMEOUT = int(os.environ.get('VF_CHAIN_TIMEOUT', '900'))
CHAIN_HEARTBEAT_SECS = int(os.environ.get('VF_CHAIN_HEARTBEAT_SECS', '30'))
# A chain with no heartbeat newer than this is considered dead (worker crash /
# restart) and is reset by recover_stuck_video_jobs on startup.
CHAIN_STALE_SECS = int(os.environ.get('VF_CHAIN_STALE_SECS', str(CHAIN_TIMEOUT)))


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
    # Insert the project FIRST, then deduct. This prevents a lost-credit bug:
    # if the deduction fails (insufficient balance) we roll back the orphan
    # project; if the insert fails, nothing was deducted.
    if body.auto_run:
        ok, msg, _ = await deduct(user['id'], 'video_factory_chain')
        if not ok:
            raise HTTPException(status_code=402, detail=msg)

    await db.video_projects.insert_one(doc)
    doc.pop('_id', None)

    if body.auto_run:
        background.add_task(_run_chain_bg, pid, body.prompt.strip(), body.language, user['id'])
        doc['status'] = 'processing'
        await _update(pid, {'status': 'processing'})

    return doc


async def _chain_heartbeat_loop(project_id: str, stop: asyncio.Event):
    """Stamp chain_heartbeat every CHAIN_HEARTBEAT_SECS while the chain runs, so a
    crashed/restarted worker is detectable by recover_stuck_video_jobs (cross-process
    liveness — the missing piece that let projects sit at 'processing' forever)."""
    try:
        while not stop.is_set():
            await _update(project_id, {'chain_heartbeat': _iso()})
            try:
                await asyncio.wait_for(stop.wait(), CHAIN_HEARTBEAT_SECS)
            except asyncio.TimeoutError:
                continue
    except Exception:
        pass


async def _run_chain_bg(project_id: str, raw_prompt: str, language: str, user_id: str):
    session_id = f'vf-{project_id}'
    await _update(project_id, {'status': 'processing', 'chain_started_at': _iso(), 'chain_heartbeat': _iso()})
    stop = asyncio.Event()
    hb = asyncio.create_task(_chain_heartbeat_loop(project_id, stop))
    try:
        try:
            result = await asyncio.wait_for(
                run_factory_chain(raw_prompt, language, session_id), timeout=CHAIN_TIMEOUT)
        except asyncio.TimeoutError:
            raise RuntimeError(f'factory chain exceeded {CHAIN_TIMEOUT}s')
        patch = {
            'stages': result.get('stages', {}),
            'errors': result.get('errors', {}),
            'selected_script_id': result.get('selected_script_id'),
            'status': 'ready' if not result.get('errors') else 'partial',
            'chain_heartbeat': _iso(),
        }
        await _update(project_id, patch)
    except Exception as e:
        await _update(project_id, {
            'status': 'error',
            'errors': {'chain': str(e)[:300]},
            'chain_heartbeat': _iso(),
            'refunded': True,
        })
        try:
            await refund(user_id, 'video_factory_chain', reason='chain_failed', ref_id=f'vf-chain-{project_id}')
        except Exception:
            logger.warning('chain failure refund failed for %s: %s', project_id, e)
    finally:
        stop.set()
        hb.cancel()


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
        raise HTTPException(503, 'AI service temporarily unavailable. Please try again shortly.')
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
        raise HTTPException(503, 'AI service temporarily unavailable. Please try again shortly.')
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
        raise HTTPException(503, 'AI service temporarily unavailable. Please try again shortly.')
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
        raise HTTPException(503, 'AI service temporarily unavailable. Please try again shortly.')
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
        raise HTTPException(503, 'AI service temporarily unavailable. Please try again shortly.')
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
        raise HTTPException(503, 'AI service temporarily unavailable. Please try again shortly.')
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
        raise HTTPException(503, 'AI service temporarily unavailable. Please try again shortly.')
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


async def _run_render_pipeline(project_id: str, orientation: str, user_id: str):
    """Background job: ensure the storyboard exists (re-run the pipeline if it
    was interrupted by a restart), then render the video. Runs entirely off the
    request path so a slow LLM/Image step can never time out the user's click."""
    try:
        p = await db.video_projects.find_one({'id': project_id}, {'_id': 0})
        if not p:
            return
        stages = p.get('stages') or {}
        if not stages.get('storyboard') or not stages.get('visual_plan'):
            if p.get('status') in ('processing', 'created', 'error', 'partial'):
                try:
                    result = await asyncio.wait_for(run_factory_chain(
                        p.get('prompt_raw', ''), p.get('language', 'hinglish'), f'vf-{project_id}'),
                        timeout=CHAIN_TIMEOUT)
                    await _update(project_id, {
                        'stages': result.get('stages', {}),
                        'selected_script_id': result.get('selected_script_id'),
                        'status': 'ready' if not result.get('errors') else 'partial',
                    })
                    p = await db.video_projects.find_one({'id': project_id}, {'_id': 0})
                    stages = (p or {}).get('stages') or {}
                except Exception as e:
                    logger.exception('render pipeline chain re-run failed')
                    await _update(project_id, {'render_status': 'error',
                                               'render_error': f'pipeline re-run failed: {str(e)[:200]}'})
                    try:
                        await refund(user_id, 'video_factory_assets', reason='chain_rerun_failed',
                                     ref_id=f'vf-assets-{project_id}')
                        await _update(project_id, {'refunded': True})
                    except Exception:
                        pass
                    return
        await generate_all_assets(project_id, orientation)
    except Exception as e:
        logger.exception('render pipeline crashed')
        try:
            await _update(project_id, {'render_status': 'error',
                                       'render_error': f'pipeline crashed: {str(e)[:200]}'})
        except Exception:
            pass


@router.post('/project/{project_id}/generate-assets')
async def generate_assets(project_id: str, body: GenerateAssetsIn, background: BackgroundTasks, user=Depends(get_current_user)):
    """Kick off image+voice+assembly in background. Poll project for status."""
    p = await _project_or_404(project_id, user)

    # A dead/orphaned job (server restart, hung image call) leaves render_status
    # stuck in an "active" state, which would block ALL retries and leave the
    # user stuck at "generating" with no credit ever deducted. Only treat it as
    # live if it started recently; otherwise reset it and start a fresh render
    # (refunding the prior dead run's asset credit once, so no double charge).
    # A dead/orphaned job (server restart, hung image call) leaves render_status
    # stuck in an "active" state, which would block ALL retries and leave the
    # user stuck at "generating" with no credit ever deducted. We detect a live
    # job via its heartbeat; if no heartbeat recently, the job is dead -> reset
    # it and start a fresh render (refunding the prior dead run's asset credit
    # once, so no double charge).
    STALE_SECS = int(os.environ.get('VF_RENDER_STALE_SECS', '150'))
    active = p.get('render_status') in ('generating_images', 'generating_voice', 'assembling')
    if active:
        hb = p.get('render_heartbeat') or p.get('render_started_at')
        if hb is None:
            # No heartbeat recorded — we can't prove it's dead, so treat it as a
            # live job. (This also matches the unit-test contract and lets the
            # startup recovery job reset legacy orphans instead of here.)
            return {'ok': True, 'already_running': True, 'render_status': p.get('render_status')}
        alive = False
        try:
            dt = datetime.fromisoformat(hb)
            now = datetime.now(timezone.utc)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            alive = (now - dt).total_seconds() <= STALE_SECS
        except Exception:
            alive = True  # on parse error, never kill a possibly-live job
        if alive:
            return {'ok': True, 'already_running': True, 'render_status': p.get('render_status')}
        if not p.get('refunded'):
            try:
                await refund(user['id'], 'video_factory_assets', reason='dead_render_rerun',
                             ref_id=f'vf-assets-{project_id}')
            except Exception as e:
                logger.warning('dead_render_rerun refund failed: %s', e)
            await _update(project_id, {'refunded': True})

    ok, msg, _ = await deduct(user['id'], 'video_factory_assets')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    await _update(project_id, {'render_status': 'queued', 'render_progress': 0, 'render_error': None,
                               'cancel_requested': False, 'refunded': False, 'render_started_at': _iso()})
    background.add_task(_run_render_pipeline, project_id, body.orientation, user['id'])
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
    # Reject files that aren't real MP4 containers (corrupt-but-large).
    try:
        with open(path, 'rb') as fh:
            head = fh.read(32)
        if b'ftyp' not in head:
            raise HTTPException(422, 'Rendered video is corrupt (missing MP4 header). Please re-generate.')
    except HTTPException:
        raise
    except Exception:
        pass
    return FileResponse(path, media_type='video/mp4', filename=f'{p.get("title","video")[:40]}.mp4')


@router.post('/project/{project_id}/cancel')
async def cancel_generation(project_id: str, user=Depends(get_current_user)):
    """Cancel a running generation: stops the pipeline, refunds the asset credit,
    and removes partial on-disk artifacts."""
    p = await _project_or_404(project_id, user)
    status = p.get('render_status')
    if status in ('queued', 'generating_images', 'generating_voice', 'assembling'):
        uid = p.get('user_id')
        if uid and not p.get('refunded'):
            await refund(uid, 'video_factory_assets', reason='user_cancelled', ref_id=f'vf-assets-{project_id}')
        await _update(project_id, {'render_status': 'cancelled', 'render_error': 'cancelled by user',
                                   'cancel_requested': True, 'refunded': True})
        _cleanup_project_files(project_id)
        return {'ok': True, 'status': 'cancelled'}
    if status == 'cancelled':
        return {'ok': True, 'already_cancelled': True}
    return {'ok': True, 'already_done': True, 'render_status': status}


async def recover_stuck_video_jobs():
    """On server (re)start, reset jobs left mid-flight by a crash/restart.

    Pass 1 (render): any job stuck in render_status (queued/generating_*) is reset
    to 'error', refunded once, partial files cleaned.

    Pass 2 (chain): THE FIX for "everything stuck on processing". Previously only
    render_status was recovered, so a factory chain killed by a worker restart /
    OOM / unreachable AI provider was left at status='processing' FOREVER with no
    recovery. Now we reset projects whose chain is stale (no heartbeat newer than
    CHAIN_STALE_SECS) or never started, refunding the chain credit once.
    """
    # --- Pass 1: in-flight renders (existing behavior) ---
    cursor = db.video_projects.find(
        {'render_status': {'$in': ['queued', 'generating_images', 'generating_voice', 'assembling']}},
        {'_id': 0, 'id': 1, 'user_id': 1, 'refunded': 1},
    )
    render_count = 0
    async for p in cursor:
        render_count += 1
        if p.get('user_id') and not p.get('refunded'):
            try:
                await refund(p['user_id'], 'video_factory_assets', reason='server_restart_recovery', ref_id=f'vf-assets-{p["id"]}')
            except Exception as e:
                logger.warning('recover_stuck_video_jobs refund failed: %s', e)
        await db.video_projects.update_one(
            {'id': p['id']},
            {'$set': {'render_status': 'error', 'render_error': 'interrupted by server restart',
                      'refunded': True, 'updated_at': _iso()}},
        )
        _cleanup_project_files(p['id'])

    # --- Pass 2: factory CHAIN stuck at processing/created/partial ---
    cutoff = datetime.now(timezone.utc).timestamp() - CHAIN_STALE_SECS
    chain_cursor = db.video_projects.find(
        {'status': {'$in': ['processing', 'created', 'partial']}},
        {'_id': 0, 'id': 1, 'user_id': 1, 'refunded': 1,
         'chain_heartbeat': 1, 'updated_at': 1, 'stages': 1},
    )
    chain_count = 0
    async for p in chain_cursor:
        # A 'partial' project that already produced stages may be user-editable;
        # only reset ones that never produced any stages (truly stuck at chain).
        if p.get('status') == 'partial' and (p.get('stages') or {}):
            continue
        hb = p.get('chain_heartbeat') or p.get('updated_at')
        stale = True
        if hb:
            try:
                dt = datetime.fromisoformat(hb)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                stale = dt.timestamp() < cutoff
            except Exception:
                stale = True
        if not stale:
            # Heartbeat is fresh — the chain is still legitimately running; leave it.
            continue
        chain_count += 1
        if p.get('user_id') and not p.get('refunded'):
            try:
                await refund(p['user_id'], 'video_factory_chain', reason='chain_recovery', ref_id=f'vf-chain-{p["id"]}')
            except Exception as e:
                logger.warning('recover_stuck_chain refund failed: %s', e)
        await db.video_projects.update_one(
            {'id': p['id']},
            {'$set': {'status': 'error',
                      'errors': {'chain': 'interrupted by server restart / no heartbeat'},
                      'refunded': True, 'updated_at': _iso()}},
        )
        _cleanup_project_files(p['id'])

    if render_count or chain_count:
        logger.warning('recover_stuck_video_jobs: reset %s render + %s chain job(s)', render_count, chain_count)
    return render_count + chain_count


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
