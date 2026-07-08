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
        return _fallback_shotlist(narration, language, target_seconds, topic)
    try:
        data = json.loads(raw[start:end + 1])
        if not isinstance(data.get('scenes'), list) or not data['scenes']:
            return _fallback_shotlist(narration, language, target_seconds, topic)
        return data
    except Exception:
        return _fallback_shotlist(narration, language, target_seconds, topic)


MOTION_CYCLE = ['ken-burns-in', 'pan-left', 'ken-burns-out', 'pan-right', 'tilt-up', 'tilt-down']


def _fallback_shotlist(narration: str, language: str, target_seconds: int, topic: str = '') -> Dict[str, Any]:
    """Split narration into ~5s chunks if LLM fails.
    If narration is empty, generate topic-based scenes so the video always has multiple images.
    """
    wps = WORDS_PER_SECOND.get(language, 2.5)
    words = re.findall(r'\S+', narration)
    chunk_size = max(8, int(wps * 5))
    scenes: List[Dict[str, Any]] = []
    for i, wi in enumerate(range(0, len(words), chunk_size)):
        text = ' '.join(words[wi:wi + chunk_size])
        scenes.append({
            'narration_chunk': text,
            'visual_prompt': f'cinematic vertical shot illustrating: {text[:120]}, Indian setting, vivid colors',
            'seconds': max(3, int(len(text.split()) / wps)),
            'motion': MOTION_CYCLE[i % len(MOTION_CYCLE)],
        })

    # If narration was empty or too short — generate topic-based scenes (never give just 1 image)
    if len(scenes) < 3:
        t = topic or narration[:60] or 'interesting topic'
        lang = language.lower()
        if lang == 'hindi':
            template = [
                (f'{t} के बारे में आज कुछ नया जानते हैं', f'cinematic Indian setting about {t}, vibrant'),
                (f'{t} का सबसे ज़रूरी पहलू जो लोग भूल जाते हैं', f'close-up detail shot of {t}, professional'),
                (f'{t} से आपकी ज़िंदगी में यह बदलाव आएगा', f'inspiring lifestyle shot related to {t}, warm light'),
                (f'विशेषज्ञ भी {t} के लिए यही तकनीक अपनाते हैं', f'expert sharing knowledge about {t}, clean background'),
                (f'आज से ही {t} को अपनी दिनचर्या में शामिल करें', f'motivational action shot for {t}, sunrise India'),
            ]
        elif lang == 'english':
            template = [
                (f'Let us explore {t} together today', f'cinematic shot about {t}, vibrant colors'),
                (f'The most important aspect of {t} people ignore', f'close-up professional shot of {t}'),
                (f'How {t} can change your life completely', f'inspiring lifestyle shot related to {t}, golden hour'),
                (f'Experts use this technique for {t}', f'expert explaining {t}, minimal clean background'),
                (f'Start applying {t} in your life from today', f'motivational sunrise shot representing {t}'),
            ]
        else:  # hinglish
            template = [
                (f'Aaj {t} ke baare mein kuch naya seekhte hain', f'cinematic Indian setting about {t}, vibrant colors'),
                (f'Yeh hai {t} ka sabse important pahlu jo log bhool jaate hain', f'close-up detail of {t}, professional photography'),
                (f'{t} se aapki life mein yeh changes aayenge', f'inspiring lifestyle shot related to {t}, warm lighting'),
                (f'Expert bhi {t} ke liye yahi technique use karte hain', f'expert explaining {t}, clean minimal background'),
                (f'Aaj se hi {t} ko apni life mein apply karo', f'motivational action shot for {t}, Indian sunrise'),
            ]
        scenes = [
            {'narration_chunk': txt, 'visual_prompt': prompt,
             'seconds': 5, 'motion': MOTION_CYCLE[i % len(MOTION_CYCLE)]}
            for i, (txt, prompt) in enumerate(template)
        ]

    return {
        'scenes': scenes,
        'duration_estimate': sum(s['seconds'] for s in scenes),
        'music_mood': 'upbeat',
        'subtitle_style': 'bold-bottom',
        '_fallback': True,
    }
