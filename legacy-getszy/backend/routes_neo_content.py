"""Universal AI content engine — Neo Studio (Tier 3, "universal").

Generate and translate any commerce content (product copy, ads, emails,
SMS, social, SEO) in any language. LLM-backed with graceful template
fallbacks so it always returns usable output.
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import get_current_admin
from llm_provider import chat_completion

router = APIRouter(prefix='/admin/neo-content', tags=['neo-content'])

CONTENT_TYPES = [
    'product_description', 'ad_copy', 'email', 'sms',
    'social_post', 'blog_idea', 'seo_meta',
]
LANGUAGES = ['en', 'hi', 'hinglish', 'ta', 'te', 'bn', 'gu', 'mr', 'es', 'fr', 'ar', 'zh']


class GenerateIn(BaseModel):
    type: str = 'product_description'
    context: dict = {}
    language: str = 'en'
    tone: str = 'professional'
    max_words: int = 120


class TranslateIn(BaseModel):
    text: str
    to: str = 'hi'
    source: str = 'auto'


SYSTEM = (
    "You are Neo, Getszy's elite universal commerce copywriter. Produce "
    "professional, high-converting, brand-grade content tailored to the "
    "requested type, language, and tone. Structure it properly for the format "
    "(e.g. scannable sections, a compelling hook, benefit-driven body, and a "
    "clear call-to-action). Use persuasive, specific language — never generic "
    "placeholder filler. Respect the requested language, tone and word limit. "
    "Return ONLY the final content — no preamble, no commentary."
)


def _fallback_generate(body: GenerateIn) -> str:
    c = body.context or {}
    name = c.get('name') or 'your product'
    category = c.get('category') or 'this category'
    features = c.get('features') or []
    feat_line = (' Features: ' + ', '.join(features) + '.') if features else ''
    aud = c.get('audience') or 'your customers'
    base = (
        f"Introducing {name} — a standout in {category}. "
        f"Built for {aud}.{feat_line} "
        f"Quality you can trust, priced for Bharat."
    )
    if body.type == 'ad_copy':
        return f"{name}: {base} Shop now on Getszy! #MadeInIndia"
    if body.type == 'sms':
        return f"{name} is here! {base} Order today."
    if body.type == 'email':
        return f"Subject: {name} is here\n\nHi,\n\n{base}\n\n– Team Getszy"
    if body.type == 'social_post':
        return f"🚀 {base} #Getszy #MadeInIndia #NewLaunch"
    if body.type == 'seo_meta':
        return f"{name} | {category} | Getszy — {base}"
    return base


def _fallback_translate(text: str, to: str) -> str:
    # Honest: return the original; never label untranslated text as a translation.
    return text


@router.post('/generate')
async def generate(body: GenerateIn, _=Depends(get_current_admin)):
    if body.type not in CONTENT_TYPES:
        body.type = 'product_description'
    if body.language not in LANGUAGES:
        body.language = 'en'
    user = (
        f"Type: {body.type}\nLanguage: {body.language}\nTone: {body.tone}\n"
        f"Max words: {body.max_words}\nContext (JSON):\n{str(body.context)}"
    )
    try:
        out = await chat_completion(
            SYSTEM, user, session_id='neo-content', temperature=0.7, max_tokens=2000,
        )
        if out and out.strip():
            return {'ok': True, 'type': body.type, 'language': body.language, 'content': out.strip(), 'source': 'ai'}
    except Exception:
        pass
    return {'ok': True, 'type': body.type, 'language': body.language, 'content': _fallback_generate(body), 'source': 'template'}


@router.post('/translate')
async def translate(body: TranslateIn, _=Depends(get_current_admin)):
    if body.to not in LANGUAGES:
        body.to = 'hi'
    user = f"Translate the following text into {body.to} (source: {body.source}). Return only the translation:\n\n{body.text}"
    try:
        out = chat_completion(SYSTEM, user, session_id='neo-translate', temperature=0.3)
        if out and out.strip():
            return {'ok': True, 'to': body.to, 'translated': out.strip(), 'source': 'ai'}
    except Exception:
        pass
    # Honest failure: return original text with an explicit error — do NOT pretend
    # the untranslated text is a translation.
    return {'ok': False, 'to': body.to, 'translated': body.text, 'source': 'none',
            'error': 'Translation service is unavailable right now. Showing the original text.'}


@router.get('/types')
async def types(_=Depends(get_current_admin)):
    return {'content_types': CONTENT_TYPES, 'languages': LANGUAGES}
