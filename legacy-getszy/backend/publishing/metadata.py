"""Generate platform-specific captions/titles/tags from a video script."""
import json
from typing import Dict, Any
from llm_provider import chat_completion

TEMPLATES = {
    'youtube':   {'max_title': 100, 'max_desc': 5000, 'tags': 'youtube SEO tags',  'style': 'SEO-rich, curiosity hook in title'},
    'instagram': {'max_title': 0,   'max_desc': 2200, 'tags': '5-10 mixed hashtags', 'style': 'punchy first line + CTA + hashtags'},
    'facebook':  {'max_title': 0,   'max_desc': 2000, 'tags': '3-5 hashtags',     'style': 'community-first, ask a question'},
    'x':         {'max_title': 0,   'max_desc': 270,  'tags': '2-3 hashtags',     'style': 'punchy tweet, hook + value + question'},
    'linkedin':  {'max_title': 0,   'max_desc': 1500, 'tags': '3-5 hashtags',     'style': 'professional, story-driven'},
}


async def build_metadata(platform: str, topic: str, script: Dict[str, Any]) -> Dict[str, Any]:
    spec = TEMPLATES.get(platform, TEMPLATES['instagram'])
    system = (
        f'You craft optimized {platform} post metadata for Indian creators. '
        f'Style: {spec["style"]}. Tags rule: {spec["tags"]}. '
        'Reply ONLY JSON: {title (str), caption (str), hashtags (array), call_to_action (str)}.'
    )
    user = f'Topic: {topic}\nScript JSON keys: {list(script.keys())}\nHook: {script.get("hook", "")[:300]}\nCTA hint: {script.get("cta", "")[:160]}'
    raw = await chat_completion(system, user, temperature=0.55)
    start = (raw or '').find('{')
    end = (raw or '').rfind('}')
    if start == -1:
        return {'title': topic[:spec['max_title'] or 100], 'caption': topic, 'hashtags': [], 'call_to_action': ''}
    try:
        data = json.loads(raw[start:end + 1])
    except Exception:
        data = {'title': topic, 'caption': raw[:spec['max_desc']], 'hashtags': [], 'call_to_action': ''}
    # Trim
    if spec['max_title']: data['title'] = (data.get('title') or '')[:spec['max_title']]
    data['caption'] = (data.get('caption') or '')[:spec['max_desc']]
    return data
