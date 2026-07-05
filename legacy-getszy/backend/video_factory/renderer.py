"""Phase 22B — Asset Generation & Video Assembly bridge.

Ties video_factory's storyboard + visual_plan into the existing video/ pipeline:
- Per-scene image generation (Pollinations)
- Voice-over synthesis (edge-tts)
- Final video assembly (ffmpeg)

Outputs are stored as:
- /app/backend/media/video_factory/{project_id}/scene_{N}.jpg
- /app/backend/media/video_factory/{project_id}/voice.mp3
- /app/backend/media/video_factory/{project_id}/final.mp4
"""
import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from db import db
from video.visuals import fetch_scene_image
from video.tts import synth, pick_voice
from video.compose import build_video

logger = logging.getLogger('getszy.vf.renderer')

MEDIA_DIR = Path(os.environ.get('MEDIA_DIR', str(Path(__file__).resolve().parent.parent / 'media' / 'video_factory')))
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


def _iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


async def _update(project_id: str, patch: dict):
    patch['updated_at'] = _iso()
    await db.video_projects.update_one({'id': project_id}, {'$set': patch})


async def _refund_assets(project_id: str, user_id: Optional[str], reason: str):
    if not user_id:
        return
    from credits import refund
    await refund(user_id, 'video_factory_assets', reason=reason)


async def generate_all_assets(project_id: str, orientation: str = '16:9') -> Dict[str, Any]:
    """End-to-end: fetch storyboard + visual_plan from DB, generate images + voice + assemble video."""
    p = await db.video_projects.find_one({'id': project_id}, {'_id': 0})
    if not p:
        return {'error': 'project not found'}

    owner_id = p.get('user_id')
    stages = p.get('stages') or {}
    scenes = stages.get('storyboard') or []
    visual_plan = stages.get('visual_plan') or []
    variants = stages.get('script_variants') or []
    selected_id = p.get('selected_script_id')
    script = next((v for v in variants if v.get('id') == selected_id), variants[0] if variants else None)

    if not scenes or not script:
        return {'error': 'storyboard or script missing — run pipeline first'}

    project_dir = MEDIA_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    await _update(project_id, {'render_status': 'generating_images', 'render_progress': 0})

    # ============ 1. Generate one image per scene ============
    scene_images = []
    total = len(scenes)
    for i, scene in enumerate(scenes):
        vp = next((v for v in visual_plan if v.get('scene_index') == scene.get('index')), None)
        prompt = (vp or {}).get('generation_prompt') or scene.get('visual_intent') or scene.get('narration_chunk', '')[:200]
        # Skip if scene has cached image
        cached = scene.get('image_path')
        if cached and os.path.exists(cached):
            scene_images.append({'index': scene['index'], 'path': cached, 'prompt': prompt})
            continue

        try:
            img_url_or_path = await fetch_scene_image(prompt, orientation=orientation, seed=hash(prompt) % 100000)
            # fetch_scene_image returns URL or local path — normalize to local
            if img_url_or_path.startswith('http'):
                import httpx
                async with httpx.AsyncClient(timeout=60) as client:
                    r = await client.get(img_url_or_path)
                    if r.status_code == 200:
                        img_path = project_dir / f'scene_{scene["index"]}.jpg'
                        img_path.write_bytes(r.content)
                        scene_images.append({'index': scene['index'], 'path': str(img_path), 'prompt': prompt})
                    else:
                        scene_images.append({'index': scene['index'], 'path': None, 'error': f'download {r.status_code}'})
            else:
                scene_images.append({'index': scene['index'], 'path': img_url_or_path, 'prompt': prompt})
        except Exception as e:
            logger.exception('image fail')
            scene_images.append({'index': scene['index'], 'path': None, 'error': str(e)[:200]})

        pct = int(((i + 1) / total) * 40)
        await _update(project_id, {'render_progress': pct})

    # Persist image paths back to storyboard
    for scene in scenes:
        match = next((si for si in scene_images if si['index'] == scene['index']), None)
        if match and match.get('path'):
            scene['image_path'] = match['path']
    await _update(project_id, {'stages.storyboard': scenes, 'render_status': 'generating_voice', 'render_progress': 45})

    # ============ 2. Generate voice-over ============
    voice_path = project_dir / 'voice.mp3'
    voice = pick_voice(language=p.get('language', 'hinglish'), gender='female')
    try:
        # Concatenate narration from each scene (respecting narration_chunk)
        full_narration = ' '.join(s.get('narration_chunk', '') for s in scenes if s.get('narration_chunk'))
        if not full_narration.strip():
            full_narration = script.get('narration', '')[:3000]
        await synth(full_narration[:4000], str(voice_path), voice=voice)
    except Exception as e:
        logger.exception('voice fail')
        await _update(project_id, {'render_status': 'error', 'render_error': f'voice: {str(e)[:200]}'})
        await _refund_assets(project_id, owner_id, 'voice_generation_failed')
        return {'error': f'voice generation failed: {e}'}

    await _update(project_id, {'render_status': 'assembling', 'render_progress': 70,
                                'voice_path': str(voice_path), 'voice_used': voice})

    # ============ 3. Assemble final video ============
    final_path = project_dir / 'final.mp4'
    # CRITICAL: Remove any stale final.mp4 from previous failed runs so user never downloads garbage
    try:
        if final_path.exists():
            final_path.unlink()
    except Exception as _e:
        logger.warning(f'could not remove stale final.mp4: {_e}')

    # Build compose scenes with keys expected by video/compose.py: {image_path, seconds, narration_chunk, motion}
    compose_scenes = []
    for scene in scenes:
        img = scene.get('image_path')
        if not img or not os.path.exists(img):
            logger.warning(f"scene {scene.get('index')} skipped — image missing: {img}")
            continue
        compose_scenes.append({
            'image_path': img,
            'seconds': max(3, int(scene.get('duration_s', 5))),
            'narration_chunk': scene.get('narration_chunk', '')[:120],
            'motion': scene.get('motion', 'static'),
        })

    logger.info(f'assembly: {len(compose_scenes)}/{len(scenes)} scenes have valid images')

    if not compose_scenes:
        await _update(project_id, {'render_status': 'error',
                                   'render_error': f'no valid scene images — all {len(scenes)} scene image fetches failed. Check Pollinations reachability from server.'})
        await _refund_assets(project_id, owner_id, 'no_scene_images')
        return {'error': 'no scene images generated successfully — check server network / Pollinations access'}

    try:
        compose_result = await build_video(compose_scenes, str(voice_path), str(final_path), orientation=orientation)
    except Exception as e:
        logger.exception('assembly fail')
        await _update(project_id, {'render_status': 'error', 'render_error': f'assembly exception: {str(e)[:300]}'})
        await _refund_assets(project_id, owner_id, 'assembly_exception')
        return {'error': f'assembly failed: {e}'}

    # CRITICAL FIX: build_video returns dict — MUST check for 'error' key (it does NOT raise)
    if isinstance(compose_result, dict) and compose_result.get('error'):
        err = compose_result['error']
        logger.error(f'compose returned error: {err}')
        await _update(project_id, {'render_status': 'error', 'render_error': f'ffmpeg: {str(err)[:300]}'})
        await _refund_assets(project_id, owner_id, 'ffmpeg_error')
        return {'error': f'ffmpeg composition failed: {err}'}

    size_bytes = final_path.stat().st_size if final_path.exists() else 0
    
    # CRITICAL: Verify video file was actually created with valid size
    # A valid MP4 with even 1 scene + audio should be >100KB. 0.2MB audio-only file bug fix.
    MIN_VALID_SIZE = 30_000  # 30KB min — real short videos are 50KB+, audio-only 0.2MB bug had ~200KB but that was JSON error response
    if not final_path.exists() or size_bytes < MIN_VALID_SIZE:
        error_msg = f'Video file missing or too small ({size_bytes} bytes, need >{MIN_VALID_SIZE}) — ffmpeg assembly likely failed silently. Check backend logs for ffmpeg errors.'
        logger.error(error_msg)
        # Remove the tiny garbage file so no one can download it
        try:
            if final_path.exists():
                final_path.unlink()
        except Exception:
            pass
        await _update(project_id, {'render_status': 'error', 'render_error': error_msg, 'final_video_path': None})
        await _refund_assets(project_id, owner_id, 'output_too_small')
        return {'error': error_msg}
    
    result = {
        'ok': True,
        'video_path': str(final_path),
        'video_url': f'/api/video-factory/project/{project_id}/download',
        'size_bytes': size_bytes,
        'scenes_rendered': len(compose_scenes),
        'voice_used': voice,
    }
    await _update(project_id, {
        'render_status': 'complete',
        'render_progress': 100,
        'final_video_path': str(final_path),
        'final_video_size': size_bytes,
        'scenes_rendered': len(compose_scenes),
    })
    return result
