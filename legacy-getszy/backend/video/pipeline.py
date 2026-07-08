"""End-to-end Faceless Video pipeline: topic -> script -> shotlist -> visuals -> tts -> compose -> MP4."""
import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from db import db
from creator.scripts import generate as gen_script
from video.shotlist import build as build_shotlist
from video.tts import synth as tts_synth, pick_voice
from video.visuals import fetch_scene_image
from video.compose import build_video, build_srt, VIDEO_DIR
from credits import refund


async def run_job(job_id: str, params: Dict[str, Any], user_id: Optional[str] = None, credit_qty: int = 1):
    """Background runner; updates job status in mongo as it progresses.

    If the job fails after credits were already deducted by the route handler,
    refund those credits since the user never got a usable video.
    """
    async def step(name: str, percent: int):
        await db.video_jobs.update_one({'id': job_id}, {'$set': {'status': name, 'percent': percent, 'updated_at': datetime.now(timezone.utc).isoformat()}})

    try:
        topic = params['topic']
        orientation = params.get('orientation', '9:16')
        language = params.get('language', 'hinglish')
        gender = params.get('voice_gender', 'female')
        target_seconds = int(params.get('target_seconds', 45))
        fmt = params.get('format', 'youtube_short' if orientation == '9:16' else 'youtube_long')
        burn_subs = bool(params.get('subtitles', True))

        await step('writing_script', 8)
        script = await gen_script(topic, fmt, audience=params.get('audience', 'indian creators'), tone=params.get('tone', 'energetic'), language=language, category=params.get('category', ''))
        # Never crash on script error — fallback script is already returned by gen_script on failure
        narration = _flatten_script(script)
        if not narration.strip():
            # Last resort: use topic as narration seed so shotlist always has content
            narration = topic

        await step('planning_shots', 20)
        shotlist = await build_shotlist(topic, narration, language, orientation, target_seconds)
        scenes = shotlist.get('scenes') or []
        if not scenes:
            raise RuntimeError('empty shotlist')
        # Cap scenes for CPU-only VPS (each clip = ~10-20s ffmpeg render on aarch64 bundled binary)
        MAX_SCENES = 6
        if len(scenes) > MAX_SCENES:
            scenes = scenes[:MAX_SCENES]

        await step('generating_visuals', 35)
        # Parallel image generation (limit concurrency)
        sem = asyncio.Semaphore(3)
        async def _grab(i, sc):
            async with sem:
                img = await fetch_scene_image(sc.get('visual_prompt', topic), orientation, seed=i + 1)
                sc['image_path'] = img
        await asyncio.gather(*[_grab(i, sc) for i, sc in enumerate(scenes)])

        await step('synthesizing_voice', 60)
        narration_text = ' '.join([sc.get('narration_chunk', '') for sc in scenes])[:6000]
        audio_path = os.path.join(VIDEO_DIR, f'{job_id}.mp3')
        voice = pick_voice(language, gender)
        await tts_synth(narration_text, audio_path, voice=voice)

        await step('composing_video', 80)
        out_path = os.path.join(VIDEO_DIR, f'{job_id}.mp4')
        result = await build_video(scenes, audio_path, out_path, orientation=orientation, subtitles=burn_subs)
        if result.get('error'):
            raise RuntimeError(result['error'])
        srt_path = os.path.join(VIDEO_DIR, f'{job_id}.srt')
        with open(srt_path, 'w') as f:
            f.write(build_srt(scenes))

        await db.video_jobs.update_one({'id': job_id}, {'$set': {
            'status': 'done', 'percent': 100,
            'video_url': f'/api/video/files/{job_id}.mp4',
            'srt_url': f'/api/video/files/{job_id}.srt',
            'audio_url': f'/api/video/files/{job_id}.mp3',
            'scenes': scenes, 'script': script, 'shotlist_meta': {k: v for k, v in shotlist.items() if k != 'scenes'},
            'completed_at': datetime.now(timezone.utc).isoformat(),
        }})
    except Exception as e:
        await db.video_jobs.update_one({'id': job_id}, {'$set': {
            'status': 'failed', 'error': str(e)[:500], 'percent': 0,
            'completed_at': datetime.now(timezone.utc).isoformat(),
        }})
        if user_id:
            await refund(user_id, 'faceless_video', qty=credit_qty, reason='generation_failed')


def _flatten_script(script: Dict[str, Any]) -> str:
    parts: List[str] = []
    for k in ('hook', 'intro', 'value', 'punchline', 'cta', 'story', 'lesson'):
        v = script.get(k)
        if isinstance(v, str): parts.append(v)
        elif isinstance(v, list): parts.extend([str(x) for x in v])
    if isinstance(script.get('h2_sections'), list):
        for sec in script['h2_sections']:
            if isinstance(sec, dict):
                parts.append(sec.get('heading', ''))
                parts.append(sec.get('content', ''))
            else:
                parts.append(str(sec))
    return ' '.join(p for p in parts if p)[:4000] or script.get('title', '')
