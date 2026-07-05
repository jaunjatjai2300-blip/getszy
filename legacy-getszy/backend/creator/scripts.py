"""Creator OS - script generation across formats."""
import json
from typing import Dict, Any, List
from llm_provider import chat_completion

FORMATS = {
    'youtube_long': {'label': 'YouTube long-form', 'duration': '5-15 min', 'sections': ['hook', 'intro', 'value', 'cta']},
    'youtube_short': {'label': 'YouTube Short', 'duration': '<60s', 'sections': ['hook', 'punchline']},
    'instagram_reel': {'label': 'Instagram Reel', 'duration': '15-30s', 'sections': ['hook', 'value', 'cta']},
    'facebook_reel': {'label': 'Facebook Reel', 'duration': '15-60s', 'sections': ['hook', 'value', 'cta']},
    'blog': {'label': 'Blog Article', 'duration': '800-1500 words', 'sections': ['intro', 'h2_sections', 'conclusion']},
    'tweet_thread': {'label': 'Twitter/X Thread', 'duration': '8-12 tweets', 'sections': ['hook_tweet', 'body', 'cta']},
    'linkedin': {'label': 'LinkedIn Post', 'duration': '150-300 words', 'sections': ['hook', 'story', 'lesson']},
}


async def generate(topic: str, fmt: str, audience: str = 'indian creators', tone: str = 'energetic', language: str = 'hinglish') -> Dict[str, Any]:
    if fmt not in FORMATS:
        raise ValueError(f'Unknown format: {fmt}')
    spec = FORMATS[fmt]
    system = (
        f'You are an elite content writer for {audience}. '
        f'Write in {language} ({tone} tone). Output ONLY valid JSON.'
    )
    user = (
        f'Topic: "{topic}"\n'
        f'Format: {spec["label"]} ({spec["duration"]})\n'
        f'Required JSON keys: title (catchy), {", ".join(spec["sections"])}, hashtags (array of 8-12), thumbnail_brief (1 sentence), retention_hooks (3 mid-content hooks).\n'
        'Reply ONLY with the JSON object, no markdown fences.'
    )
    raw = await chat_completion(system, user, temperature=0.75)
    # Extract JSON
    txt = (raw or '').strip().strip('`').replace('json\n', '', 1)
    start = txt.find('{')
    end = txt.rfind('}')
    if start == -1 or end <= start:
        return {'error': 'LLM did not return JSON', 'raw': raw}
    try:
        data = json.loads(txt[start:end + 1])
    except Exception as e:
        return {'error': f'JSON parse failed: {e}', 'raw': raw[:500]}
    data['format'] = fmt
    data['topic'] = topic
    return data


async def score_hook(hook_text: str) -> Dict[str, Any]:
    """Predict how likely a hook is to retain viewers (first 3 seconds)."""
    system = (
        'You are a viral content analyst. Score the given video hook on a 1-100 scale based on '
        'curiosity gap, emotional pull, clarity, specificity, and pattern interrupt. '
        'Output ONLY JSON: {score, rationale, suggested_rewrite}.'
    )
    raw = await chat_completion(system, f'Hook: "{hook_text}"', temperature=0.3)
    start = (raw or '').find('{')
    end = (raw or '').rfind('}')
    if start == -1:
        return {'score': 50, 'rationale': 'LLM unavailable', 'suggested_rewrite': hook_text}
    try:
        return json.loads(raw[start:end + 1])
    except Exception:
        return {'score': 50, 'rationale': raw[:200] if raw else '', 'suggested_rewrite': hook_text}


async def viral_score(content: Dict[str, Any]) -> Dict[str, Any]:
    """Pre-publish viral probability check."""
    summary = json.dumps({k: v for k, v in content.items() if k in ('title', 'hook', 'topic', 'format')}, ensure_ascii=False)[:500]
    system = (
        'You are a viral content predictor for Indian audiences. Rate the given content piece on '
        'a 0-100 viral probability scale considering: hook strength, timing relevance, niche heat, '
        'shareability, emotion. Output ONLY JSON: {viral_score, drivers (array), risks (array), recommendation}.'
    )
    raw = await chat_completion(system, f'Content: {summary}', temperature=0.4)
    start = (raw or '').find('{')
    end = (raw or '').rfind('}')
    if start == -1:
        return {'viral_score': 60, 'drivers': [], 'risks': ['LLM unavailable'], 'recommendation': 'retry'}
    try:
        return json.loads(raw[start:end + 1])
    except Exception:
        return {'viral_score': 60, 'drivers': [], 'risks': [], 'recommendation': raw[:200] if raw else ''}
