"""Creator-specific Skills (Phase 12)."""
from skills.registry import register
from creator.scripts import generate as gen_script, score_hook, viral_score
from creator.trends import predict as predict_trends
from typing import Dict, Any


@register(
    name='write_script', title='Write Script', category='creator',
    icon='PenTool', badge='free',
    description='Generate a script for YouTube, Reel, Short, Blog, Thread, or LinkedIn.',
    params={'topic': {'type': 'string', 'required': True}, 'format': {'type': 'string', 'default': 'youtube_short'}, 'tone': {'type': 'string', 'default': 'energetic'}},
)
async def write_script_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    return await gen_script(p.get('topic', ''), p.get('format', 'youtube_short'), p.get('audience', 'indian creators'), p.get('tone', 'energetic'), p.get('language', 'hinglish'))


@register(
    name='predict_trends', title='Predict Trending Topics', category='creator',
    icon='TrendingUp', badge='free',
    description='AI-forecast 8 trending content topics in your niche for the next 14 days.',
    params={'niche': {'type': 'string', 'default': ''}, 'count': {'type': 'integer', 'default': 8}},
)
async def predict_trends_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    return await predict_trends(p.get('niche', ''), int(p.get('count', 8)))


@register(
    name='hook_optimizer', title='Hook Optimizer', category='creator',
    icon='Zap', badge='free',
    description='Score and rewrite the first-3-seconds hook of a video.',
    params={'hook': {'type': 'string', 'required': True}},
)
async def hook_optimizer_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    return await score_hook(p.get('hook', ''))


@register(
    name='viral_score', title='Viral Probability Score', category='creator',
    icon='Flame', badge='free',
    description='Pre-publish viral probability check (0-100) with drivers and risks.',
    params={'title': {'type': 'string', 'required': True}, 'hook': {'type': 'string', 'default': ''}, 'format': {'type': 'string', 'default': 'reel'}},
)
async def viral_score_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    return await viral_score({'title': p.get('title', ''), 'hook': p.get('hook', ''), 'format': p.get('format', 'reel'), 'topic': p.get('title', '')})
