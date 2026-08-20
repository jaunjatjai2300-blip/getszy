"""Prompt Architect — turns a customer's casual natural-language request into a
precise, structured creative brief + an optimized generation prompt.

Why this exists:
  Customers type messy things like "make a reel about my protein powder for
  gym girls under ₹999". Feeding that raw to a generator yields weak, vague,
  retry-prone output (and wasted credits). The architect extracts intent +
  entities and emits ONE clean, detailed prompt the downstream generators
  consume directly — so the customer gets best-in-class output on the first try.
"""
import json
import logging
import re
from typing import Dict, Any, Optional

from llm_provider import chat_completion

logger = logging.getLogger('getszy.architect')

INTENTS = ['video', 'landing', 'website', 'copy', 'logo', 'social', 'image']

_INTENT_KEYWORDS = {
    'landing': ['landing', 'landing page', 'sales page', 'squeeze page', 'lead page'],
    'website': ['website', 'web page', 'web app', 'webapp', 'portfolio site', 'company site', 'site'],
    'video':   ['video', 'reel', 'shorts', 'youtube', 'tiktok', 'film', 'clip', 'explainer', 'animated'],
    'logo':    ['logo', 'logomark', 'brand mark', 'brand logo'],
    'social':  ['instagram post', 'linkedin post', 'tweet', 'social post', 'facebook post', 'caption for'],
    'image':   ['image', 'poster', 'thumbnail', 'banner', 'flyer', 'creative'],
    'copy':    ['copy', 'caption', 'ad copy', 'tagline', 'headline', 'product description', 'description for'],
}


def detect_intent(raw: str) -> str:
    t = f' {raw.lower()} '
    for intent in ['landing', 'website', 'video', 'logo', 'social', 'image', 'copy']:
        for kw in _INTENT_KEYWORDS[intent]:
            if kw in t:
                return intent
    return 'copy'


_SYSTEM = """You are Getszy's Prompt Architect. A customer types a casual, messy natural-language request. Convert it into a precise creative brief AND a single optimized generation prompt.

Return STRICT JSON only:
{
  "intent": "video|landing|website|copy|logo|social|image",
  "name": "brand/product name if identifiable, else null",
  "category": "product/service category",
  "audience": "specific target audience",
  "tone": "tone (e.g. bold, friendly, premium, playful)",
  "style": "visual/content style",
  "language": "english|hindi|hinglish|etc",
  "goal": "what the customer wants to achieve",
  "key_points": ["3-5 concrete selling points or angles"],
  "cta": "desired call-to-action",
  "visual_style": "description of desired look for video/image",
  "structured_prompt": "ONE detailed, self-contained prompt a generator can use directly to produce best-in-class output. Include brand, audience, tone, goal, key points, CTA, and style. No questions, no commentary."
}
If something is unknown, infer a sensible default. Be specific and concrete — never generic placeholders."""


def _parse_json(raw: str) -> Optional[dict]:
    if not raw:
        return None
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    s, e = raw.find('{'), raw.rfind('}')
    if s == -1 or e <= s:
        return None
    try:
        return json.loads(raw[s:e + 1])
    except Exception:
        return None


def _rule_based(raw: str, intent: str) -> dict:
    """Heuristic fallback so we ALWAYS return a usable brief (never waste a call)."""
    name = None
    m = re.search(r'\b(for|about|my|our)\s+([A-Z][\w&.\-]+(?:\s+[A-Z][\w&.\-]+){0,3})', raw)
    if m:
        name = m.group(2).strip()
    return {
        'intent': intent,
        'name': name,
        'category': '',
        'audience': 'general audience',
        'tone': 'professional',
        'style': 'modern',
        'language': 'hindi' if 'hindi' in raw.lower() else 'english',
        'goal': 'engage and convert the audience',
        'key_points': [raw.strip()],
        'cta': 'Learn more',
        'visual_style': 'clean, modern, premium',
        'structured_prompt': raw.strip(),
    }


def product_block(product: Optional[dict]) -> str:
    if not product:
        return ''
    name = product.get('name') or product.get('title')
    if not name:
        return ''
    price = product.get('sale_price') if product.get('sale_price') is not None else product.get('price')
    cur = product.get('currency') or 'INR'
    parts = [f"Product name: {name}"]
    if price is not None:
        parts.append(f"Price: {cur} {price}")
    if product.get('category'):
        parts.append(f"Category: {product['category']}")
    if product.get('description'):
        parts.append('Description: ' + str(product['description'])[:600])
    imgs = product.get('images') or []
    if imgs:
        parts.append('Real product image URLs (use these, do not invent): ' + ', '.join(imgs[:4]))
    return "REAL PRODUCT DATA (use EXACTLY as given, never fabricate price/details):\n- " + "\n- ".join(parts)


def build(raw: str, brief: dict, brand: Optional[dict] = None, product: Optional[dict] = None) -> str:
    """Compose the final generation prompt from brief + brand + product context."""
    sp = (brief.get('structured_prompt') or raw).strip()
    bb = brand_block(brand)
    pb = product_block(product)
    if bb:
        sp = bb + "\n\n" + sp
    if pb:
        sp = sp + "\n\n" + pb
    return sp


async def architect(raw: str, intent: Optional[str] = None, brand: Optional[dict] = None,
                    product: Optional[dict] = None) -> dict:
    """Convert casual text into a structured brief. Always returns a usable dict."""
    intent = intent or detect_intent(raw)
    try:
        out = await chat_completion(
            system=_SYSTEM,
            user=f"Customer request: {raw}\nPre-detected intent (override if wrong): {intent}\n\nReturn the brief JSON.",
            temperature=0.3, max_tokens=1500, session_id='architect',
        )
        brief = _parse_json(out)
        if not brief:
            brief = _rule_based(raw, intent)
    except Exception as e:
        logger.warning('architect LLM failed, rule-based fallback: %s', e)
        brief = _rule_based(raw, intent)
    brief['intent'] = brief.get('intent') or intent
    brief['structured_prompt'] = build(raw, brief, brand, product)
    if not brief['structured_prompt']:
        brief['structured_prompt'] = raw
    if product:
        brief['product'] = product.get('name') or product.get('title')
    if brand:
        brief['brand_name'] = brand.get('name')
    return brief
