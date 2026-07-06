"""Convert a script into an auto-shot list with timing + visual prompts."""
import json
import re
from typing import Dict, Any, List
from llm_provider import chat_completion

WORDS_PER_SECOND = {'hinglish': 2.5, 'hindi': 2.3, 'english': 2.7}


async def build(topic: str, narration: str, language: str = 'hinglish', orientation: str = '9:16',
                target_seconds: int = 45) -> Dict[str, Any]:
    """Return a JSON shot list: scenes with narration_chunk, visual_prompt, seconds."""
    system = (
        'You are a faceless-video director for Indian creators. Convert the given narration into '
        f'a SHOT LIST for a {orientation} video of about {target_seconds}s. Each scene must include: '
        'narration_chunk (1-2 short lines), visual_prompt (rich English prompt for image generator, '
        'cinematic, vertical composition if 9:16), seconds (3-6 per scene), motion (one of: '
        'ken-burns-in, ken-burns-out, pan-left, pan-right, tilt-up, tilt-down — vary the motion across '
        'consecutive scenes, do not repeat the same motion twice in a row, this keeps the video feeling dynamic). '
        'Reply ONLY JSON: {scenes: [...], duration_estimate, music_mood, subtitle_style}.'
    )
    user = f'Topic: {topic}\nLanguage: {language}\nFull narration:\n{narration[:2400]}'
    raw = await chat_completion(system, user, temperature=0.55)
    start = (raw or '').find('{')
    end = (raw or '').rfind('}')
    if start == -1:
        return _fallback_shotlist(narration, language, target_seconds)
    try:
        data = json.loads(raw[start:end + 1])
        if not isinstance(data.get('scenes'), list) or not data['scenes']:
            return _fallback_shotlist(narration, language, target_seconds)
        return data
    except Exception:
        return _fallback_shotlist(narration, language, target_seconds)


MOTION_CYCLE = ['ken-burns-in', 'pan-left', 'ken-burns-out', 'pan-right', 'tilt-up', 'tilt-down']


def _fallback_shotlist(narration: str, language: str, target_seconds: int) -> Dict[str, Any]:
    """Split narration into ~5s chunks if LLM fails."""
    wps = WORDS_PER_SECOND.get(language, 2.5)
    words = re.findall(r'\S+', narration)
    chunk_size = max(8, int(wps * 5))
    scenes = []
    for i, wi in enumerate(range(0, len(words), chunk_size)):
        text = ' '.join(words[wi:wi + chunk_size])
        scenes.append({
            'narration_chunk': text,
            'visual_prompt': f'cinematic vertical shot illustrating: {text[:120]}',
            'seconds': max(3, int(len(text.split()) / wps)),
            'motion': MOTION_CYCLE[i % len(MOTION_CYCLE)],
        })
    return {'scenes': scenes or [{'narration_chunk': narration[:200], 'visual_prompt': narration[:120], 'seconds': 5, 'motion': 'static'}],
            'duration_estimate': sum(s['seconds'] for s in scenes) or target_seconds,
            'music_mood': 'upbeat', 'subtitle_style': 'bold-bottom'}
