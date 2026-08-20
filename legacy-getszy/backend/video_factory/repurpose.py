"""Long-form -> Shorts repurposing engine.

Turns a long-form video transcript/script into N vertical (9:16) short videos by:
  1. LLM extracts the most engaging, self-contained moments (climax / comedy /
     surprise / magic) as highlight clips.
  2. Each highlight is rendered into a real short: B-roll stock footage (or an AI
     image with Ken Burns), an emotion-matched premium voice-over (ElevenLabs when
     configured), burned-in captions, and vertical framing.

Reuses the existing compose / tts / stock-media pipeline so output quality matches
the main Video Factory - never a fake or placeholder clip.
"""
import asyncio
import os
import uuid
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from db import db
from llm_provider import chat_completion
from video.visuals import fetch_scene_image
from video.tts import synth, pick_voice
from video.compose import build_video
from stock_media import USE_STOCK_VIDEO, search_stock_videos

logger = logging.getLogger('getszy.repurpose')

REPURPOSE_DIR = Path(os.environ.get('MEDIA_DIR', str(Path(__file__).resolve().parent.parent / 'media' / 'repurpose')))
REPURPOSE_DIR.mkdir(parents=True, exist_ok=True)


async def _parse_json_array(s: str) -> Optional[list]:
    try:
        s = s.strip()
        if '```' in s:
            s = s[s.find('['):s.rfind(']') + 1]
        return json.loads(s)
    except Exception:
        return None


async def extract_highlights(text: str, count: int, language: str, session_id: str) -> List[Dict[str, Any]]:
    """Pick the most viral, self-contained moments from a long transcript."""
    system = (
        "You are a senior short-form video editor (YouTube Shorts / Instagram Reels). "
        "Given a long-form video transcript or script, identify the most engaging, "
        "self-contained moments worth turning into separate short videos. Prioritise "
        "climax, comedy, surprise, controversy, or 'magic' beats. Each moment must make "
        "sense on its own without the full video. "
        "Return STRICT JSON array (max `count` items). Each item: "
        '{"title": short caption (<=60 chars), '
        '"narration": the exact spoken script (1-3 sentences, derived ONLY from the source, no new facts), '
        '"visual_prompt": concise B-roll / image prompt, '
        '"emotion": one of excited|funny|dramatic|calm|warm}. '
        "Output ONLY the JSON array. No markdown, no commentary."
    )
    user = f"Transcript:\n{text[:6000]}\n\ncount={count}\nlanguage={language}"
    try:
        out = await chat_completion(system=system, user=user, temperature=0.4, max_tokens=1600,
                                    session_id=session_id or 'repurpose')
        arr = await _parse_json_array(out)
        if isinstance(arr, list) and arr:
            return arr[:count]
    except Exception as e:
        logger.warning('extract_highlights LLM failed: %s', e)
    return _naive_split(text, count)


def _naive_split(text: str, count: int) -> List[Dict[str, Any]]:
    sentences = [s.strip() for s in text.replace('\n', ' ').split('.') if s.strip()]
    if not sentences:
        return []
    chunk = max(1, len(sentences) // max(1, count))
    out = []
    for i in range(0, len(sentences), chunk):
        seg = '. '.join(sentences[i:i + chunk]).strip()
        if seg:
            out.append({'title': seg[:50], 'narration': seg, 'visual_prompt': seg[:120], 'emotion': 'excited'})
        if len(out) >= count:
            break
    return out


async def render_highlight(h: Dict[str, Any], orientation: str, out_dir: Path,
                           language: str = 'hinglish') -> Dict[str, Any]:
    """Render one highlight into a vertical short MP4. Returns {title, path, ...} or {error}."""
    narration = (h.get('narration') or '').strip()
    if not narration:
        return {'error': 'empty narration', 'title': h.get('title')}
    vid_prompt = h.get('visual_prompt') or narration[:120]
    emotion = h.get('emotion') or 'excited'

    # 1. Visual: real stock B-roll footage first (documentary feel), else AI image.
    video_path = None
    if USE_STOCK_VIDEO:
        try:
            vids = await search_stock_videos(vid_prompt, n=1)
            if vids:
                video_path = vids[0]
        except Exception as e:
            logger.warning('stock video fetch failed: %s', e)

    img_path = None
    if not video_path:
        try:
            img = await fetch_scene_image(vid_prompt, orientation=orientation, seed=hash(vid_prompt) % 100000)
            if isinstance(img, str):
                if img.startswith('http'):
                    import httpx
                    async with httpx.AsyncClient(timeout=90) as c:
                        r = await c.get(img)
                        if r.status_code == 200:
                            p = out_dir / f'img_{uuid.uuid4().hex}.jpg'
                            p.write_bytes(r.content)
                            img_path = str(p)
                else:
                    img_path = img
        except Exception as e:
            logger.warning('image fetch failed: %s', e)

    # 2. Voice-over (premium emotion-aware when configured).
    voice_path = out_dir / f'voice_{uuid.uuid4().hex}.mp3'
    voice = pick_voice(language=language, gender='female')
    try:
        await synth(narration[:4000], str(voice_path), voice=voice, emotion=emotion)
    except Exception as e:
        logger.warning('voice synth failed: %s', e)

    # 3. Compose a single vertical scene (stock video gives real motion; else Ken Burns).
    secs = max(15, min(45, int(len(narration.split()) / 2.3)))
    scenes = [{
        'image_path': img_path,
        'video_path': video_path if (video_path and os.path.exists(video_path)) else None,
        'seconds': secs,
        'narration_chunk': narration,
        'motion': 'ken-burns-in',
    }]
    final = out_dir / f'final_{uuid.uuid4().hex}.mp4'
    try:
        if final.exists():
            final.unlink()
    except Exception:
        pass
    try:
        res = await build_video(scenes, str(voice_path), str(final), orientation=orientation)
    except Exception:
        logger.exception('compose failed for highlight')
        return {'error': 'compose failed', 'title': h.get('title')}
    if isinstance(res, dict) and res.get('error'):
        return {'error': res['error'], 'title': h.get('title')}
    if not final.exists() or final.stat().st_size < 30_000:
        return {'error': 'short too small / failed', 'title': h.get('title')}
    return {'title': h.get('title'), 'path': str(final), 'secs': secs, 'emotion': emotion}
