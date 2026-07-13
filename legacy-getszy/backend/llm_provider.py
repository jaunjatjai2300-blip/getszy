"""LLM Provider — Cost Guard with Multi-Provider Fallback

Priority chain (Ollama first = zero cost):
  1. Ollama     — local, free, unlimited (3 models on VPS)
  2. Groq       — free tier, 11K req/day
  3. Gemini     — free tier, 1500 req/day
  4. OpenRouter — paid (your credits, many models available)
"""
import os
import httpx
import uuid
import logging
from datetime import datetime, timezone

logger = logging.getLogger('getszy.llm')

# ── Config ────────────────────────────────────────────────────────────────────
FREE_ONLY        = os.environ.get('FREE_ONLY', 'true').lower() != 'false'
GROQ_API_KEY     = os.environ.get('GROQ_API_KEY', '').strip()
GEMINI_API_KEY   = os.environ.get('GEMINI_API_KEY', '').strip()
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '').strip()
OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'qwen/qwen-2.5-72b-instruct').strip()
OLLAMA_BASE_URL  = os.environ.get('OLLAMA_BASE_URL', 'http://host.docker.internal:11434')
OLLAMA_SECRET    = os.environ.get('OLLAMA_SECRET', '')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
EMERGENT_MODEL   = os.environ.get('EMERGENT_MODEL', 'gpt-4o-mini')

# Ollama model chain — try primary, then fallbacks
OLLAMA_MODELS = []
_primary = os.environ.get('OLLAMA_MODEL', 'qwen2.5:7b').strip()
_second  = os.environ.get('OLLAMA_MODEL_2', 'qwen2.5-coder:14b').strip()
_third   = os.environ.get('OLLAMA_MODEL_3', 'llama3.2:3b').strip()
if _primary:
    OLLAMA_MODELS.append(_primary)
if _second:
    OLLAMA_MODELS.append(_second)
if _third and _third != _primary:
    OLLAMA_MODELS.append(_third)
if not OLLAMA_MODELS:
    OLLAMA_MODELS = ['qwen2.5:7b']

# Daily free limits (safe = 80% of actual limit)
GROQ_DAILY_LIMIT   = int(os.environ.get('GROQ_DAILY_LIMIT', '11000'))
GEMINI_DAILY_LIMIT = int(os.environ.get('GEMINI_DAILY_LIMIT', '1200'))

# ── In-memory daily counters (reset at midnight UTC) ─────────────────────────
_counters: dict = {}

def _today() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')

def _count(provider: str) -> int:
    key = f'{provider}:{_today()}'
    return _counters.get(key, 0)

def _increment(provider: str):
    key = f'{provider}:{_today()}'
    _counters[key] = _counters.get(key, 0) + 1
    today = _today()
    for k in list(_counters.keys()):
        if not k.endswith(today):
            del _counters[k]

def _under_limit(provider: str) -> bool:
    limits = {'groq': GROQ_DAILY_LIMIT, 'gemini': GEMINI_DAILY_LIMIT}
    return _count(provider) < limits.get(provider, 999999)

# ── Provider implementations ──────────────────────────────────────────────────

async def _groq(system: str, user: str, temperature: float) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers={'Authorization': f'Bearer {GROQ_API_KEY}'},
            json={
                'model': 'llama-3.1-8b-instant',
                'messages': [
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user},
                ],
                'temperature': temperature,
                'max_tokens': 2048,
            },
        )
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content']


async def _gemini(system: str, user: str, temperature: float) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}',
            json={
                'system_instruction': {'parts': [{'text': system}]},
                'contents': [{'parts': [{'text': user}]}],
                'generationConfig': {'temperature': temperature, 'maxOutputTokens': 2048},
            },
        )
        r.raise_for_status()
        return r.json()['candidates'][0]['content']['parts'][0]['text']


async def _ollama_single(model: str, system: str, user: str, temperature: float) -> str:
    headers = {}
    if OLLAMA_SECRET:
        headers['Authorization'] = f'Bearer {OLLAMA_SECRET}'
    async with httpx.AsyncClient(timeout=300.0) as client:
        r = await client.post(
            f'{OLLAMA_BASE_URL}/api/chat',
            headers=headers,
            json={
                'model': model,
                'messages': [
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user},
                ],
                'stream': False,
                'options': {'temperature': temperature},
            },
        )
        r.raise_for_status()
        return r.json().get('message', {}).get('content', '')


async def _ollama_chain(system: str, user: str, temperature: float) -> str:
    """Try each Ollama model in order until one works."""
    last_error = None
    for model in OLLAMA_MODELS:
        try:
            result = await _ollama_single(model, system, user, temperature)
            logger.info(f'LLM: ollama ({model})')
            return result
        except Exception as e:
            logger.warning(f'LLM ollama {model} failed: {e}')
            last_error = e
    raise last_error or RuntimeError('All Ollama models failed')


async def _emergent(system: str, user: str, session_id: str) -> str:
    if FREE_ONLY:
        raise RuntimeError('FREE_ONLY mode: paid LLM blocked. Set FREE_ONLY=false to enable.')
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system,
    ).with_model('openai', EMERGENT_MODEL)
    return await chat.send_message(UserMessage(text=user))


async def _openrouter(system: str, user: str, temperature: float) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'HTTP-Referer': 'https://getszy.com',
                'X-Title': 'Getszy',
            },
            json={
                'model': OPENROUTER_MODEL,
                'messages': [
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user},
                ],
                'temperature': temperature,
                'max_tokens': 4096,
            },
        )
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content']


# ── Main entry point ──────────────────────────────────────────────────────────

async def chat_completion(
    system: str,
    user: str,
    session_id: str | None = None,
    temperature: float = 0.4,
) -> str:
    session_id = session_id or str(uuid.uuid4())

    # 1. Ollama — local, free, unlimited (PRIMARY)
    if OLLAMA_MODELS:
        try:
            return await _ollama_chain(system, user, temperature)
        except Exception as e:
            logger.warning(f'LLM ollama chain failed: {e}')

    # 2. Groq — free, fast
    if GROQ_API_KEY and _under_limit('groq'):
        try:
            result = await _groq(system, user, temperature)
            _increment('groq')
            logger.info(f'LLM: groq ({_count("groq")}/{GROQ_DAILY_LIMIT} today)')
            return result
        except Exception as e:
            logger.warning(f'LLM groq failed: {e}')

    # 3. Gemini — free, Google
    if GEMINI_API_KEY and _under_limit('gemini'):
        try:
            result = await _gemini(system, user, temperature)
            _increment('gemini')
            logger.info(f'LLM: gemini ({_count("gemini")}/{GEMINI_DAILY_LIMIT} today)')
            return result
        except Exception as e:
            logger.warning(f'LLM gemini failed: {e}')

    # 4. OpenRouter — paid (your credits, many models)
    if OPENROUTER_API_KEY:
        try:
            result = await _openrouter(system, user, temperature)
            logger.info('LLM: openrouter')
            return result
        except Exception as e:
            logger.warning(f'LLM openrouter failed: {e}')

    # 5. Emergent (paid) — last resort
    if EMERGENT_LLM_KEY and not FREE_ONLY:
        try:
            result = await _emergent(system, user, session_id)
            logger.info('LLM: emergent (paid)')
            return result
        except Exception as e:
            logger.warning(f'LLM emergent failed: {e}')

    raise RuntimeError(
        'All LLM providers failed. '
        'Check Ollama is running, or add GROQ_API_KEY/GEMINI_API_KEY/OPENROUTER_API_KEY.'
    )


def provider_info() -> dict:
    groq_used   = _count('groq')
    gemini_used = _count('gemini')
    return {
        'free_only': FREE_ONLY,
        'providers': {
            'groq':    {'available': bool(GROQ_API_KEY),   'used_today': groq_used,   'limit': GROQ_DAILY_LIMIT,   'remaining': max(0, GROQ_DAILY_LIMIT - groq_used)},
            'gemini':  {'available': bool(GEMINI_API_KEY), 'used_today': gemini_used, 'limit': GEMINI_DAILY_LIMIT, 'remaining': max(0, GEMINI_DAILY_LIMIT - gemini_used)},
            'ollama':  {'available': True, 'models': OLLAMA_MODELS, 'active_model': OLLAMA_MODELS[0] if OLLAMA_MODELS else None, 'description': '100% free, runs on VPS'},
            'emergent':{'available': bool(EMERGENT_LLM_KEY) and not FREE_ONLY, 'blocked_by_free_only': FREE_ONLY},
        },
        'active_chain': (
            f'ollama ({OLLAMA_MODELS[0]})' if OLLAMA_MODELS else
            'groq' if GROQ_API_KEY and _under_limit('groq') else
            'gemini' if GEMINI_API_KEY and _under_limit('gemini') else
            'none'
        ),
    }
