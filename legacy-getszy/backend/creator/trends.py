"""Creator OS - trend prediction for Indian creators.

Uses a curated niche heat-map (refreshed by AI) + Google Trends-style ranking.
When GPU/paid providers are configured we can plug in real-time scrapers.
"""
import json
import random
from datetime import datetime, timezone
from typing import List, Dict, Any

from llm_provider import chat_completion


INDIAN_NICHES = [
    'AI tools for Indian women', 'home cooking shortcuts', 'budget travel India',
    'startup stories Hindi', 'personal finance India', 'study with me',
    'productivity hacks', 'fitness for moms', 'ethnic fashion DIY', 'tech reviews',
    'parenting Indian style', 'meditation for entrepreneurs', 'side hustle ideas',
    'crypto/stocks India', 'GenZ career guidance', 'desi recipes vegetarian',
    'spirituality + science', 'AI for solopreneurs', 'language learning Hindi',
]


async def predict(niche: str = '', count: int = 8, region: str = 'IN') -> Dict[str, Any]:
    base = niche.strip() or random.choice(INDIAN_NICHES)
    system = (
        'You are a trend forecaster for Indian YouTube and Instagram creators. '
        'Predict 8 trending content topics for the next 14 days in the given niche. '
        'Reply ONLY in JSON: {niche, region, generated_at, predictions: [{topic, trend_score (0-100), search_demand (low/med/high), competition (low/med/high), why, hook_idea, format_recommendation}]}. '
        'Be specific (no generic topics).'
    )
    user = f'Niche: {base}\nRegion: {region}\nCount: {count}'
    raw = await chat_completion(system, user, temperature=0.65)
    start = (raw or '').find('{')
    end = (raw or '').rfind('}')
    if start == -1:
        return {'niche': base, 'predictions': [], 'error': 'LLM unavailable'}
    try:
        data = json.loads(raw[start:end + 1])
        data.setdefault('generated_at', datetime.now(timezone.utc).isoformat())
        return data
    except Exception as e:
        return {'niche': base, 'predictions': [], 'error': str(e), 'raw': raw[:300]}


async def competitor_gap(channel_hint: str) -> Dict[str, Any]:
    """AI-driven content-gap suggestion vs a perceived competitor."""
    system = (
        'You are a YouTube/Instagram channel auditor. Given a competitor channel description, '
        'suggest 5 content gaps the user can exploit to win. Output JSON: '
        '{competitor, gaps: [{topic, why_underserved, target_audience, angle}]}.'
    )
    raw = await chat_completion(system, f'Competitor: {channel_hint}', temperature=0.6)
    start = (raw or '').find('{')
    end = (raw or '').rfind('}')
    if start == -1:
        return {'competitor': channel_hint, 'gaps': []}
    try:
        return json.loads(raw[start:end + 1])
    except Exception:
        return {'competitor': channel_hint, 'gaps': [], 'raw': raw[:200] if raw else ''}
