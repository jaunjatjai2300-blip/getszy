"""LLM Provider — Free-First Cost Guard

Priority chain (zero paid cost):
  1. Groq       — free forever, 14,400 req/day (Llama 3.1 8B)
  2. Gemini     — free forever, 1,500 req/day (Gemini 1.5 Flash)
  3. Ollama     — local, free, unlimited
  4. Emergent   — paid fallback (only if FREE_ONLY=false)

Set env vars to unlock providers:
  GROQ_API_KEY   — get free at console.groq.com
  GEMINI_API_KEY — get free at aistudio.google.com
  FREE_ONLY=true — hard block all paid APIs (default: true)
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
OLLAMA_BASE_URL  = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_SECRET    = os.environ.get('OLLAMA_SECRET', '')
OLLAMA_MODEL     = os.environ.get('OLLAMA_MODEL', 'llama3.2:3b')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
EMERGENT_MODEL   = os.environ.get('EMERGENT_MODEL', 'gpt-4o-mini')

# Daily free limits (safe = 80% of actual limit)
GROQ_DAILY_LIMIT   = int(os.environ.get('GROQ_DAILY_LIMIT', '11000'))   # actual: 14400
GEMINI_DAILY_LIMIT = int(os.environ.get('GEMINI_DAILY_LIMIT', '1200'))  # actual: 1500

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
    # Clean old keys
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


async def _ollama(system: str, user: str, temperature: float) -> str:
    headers = {}
    if OLLAMA_SECRET:
        headers['Authorization'] = f'Bearer {OLLAMA_SECRET}'
    async with httpx.AsyncClient(timeout=300.0) as client:
        r = await client.post(
            f'{OLLAMA_BASE_URL}/api/chat',
            headers=headers,
            json={
                'model': OLLAMA_MODEL,
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


# ── Main entry point ──────────────────────────────────────────────────────────

async def chat_completion(
    system: str,
    user: str,
    session_id: str | None = None,
    temperature: float = 0.4,
) -> str:
    session_id = session_id or str(uuid.uuid4())

    # 1. Groq — free, fast, best quality
    if GROQ_API_KEY and _under_limit('groq'):
        try:
            result = await _groq(system, user, temperature)
            _increment('groq')
            logger.info(f'LLM: groq ({_count("groq")}/{GROQ_DAILY_LIMIT} today)')
            return result
        except Exception as e:
            logger.warning(f'LLM groq failed: {e}')

    # 2. Gemini — free, Google, good quality
    if GEMINI_API_KEY and _under_limit('gemini'):
        try:
            result = await _gemini(system, user, temperature)
            _increment('gemini')
            logger.info(f'LLM: gemini ({_count("gemini")}/{GEMINI_DAILY_LIMIT} today)')
            return result
        except Exception as e:
            logger.warning(f'LLM gemini failed: {e}')

    # 3. Ollama — local, free, unlimited
    try:
        result = await _ollama(system, user, temperature)
        logger.info('LLM: ollama (local)')
        return result
    except Exception as e:
        logger.warning(f'LLM ollama failed: {e}')

    # 4. Emergent (paid) — only if FREE_ONLY=false
    if EMERGENT_LLM_KEY and not FREE_ONLY:
        try:
            result = await _emergent(system, user, session_id)
            logger.info('LLM: emergent (paid)')
            return result
        except Exception as e:
            logger.warning(f'LLM emergent failed: {e}')

    raise RuntimeError(
        'All LLM providers failed or at limit. '
        'Add GROQ_API_KEY or GEMINI_API_KEY env var (both free).'
    )


def provider_info() -> dict:
    groq_used   = _count('groq')
    gemini_used = _count('gemini')
    return {
        'free_only': FREE_ONLY,
        'providers': {
            'groq':    {'available': bool(GROQ_API_KEY),   'used_today': groq_used,   'limit': GROQ_DAILY_LIMIT,   'remaining': max(0, GROQ_DAILY_LIMIT - groq_used)},
            'gemini':  {'available': bool(GEMINI_API_KEY), 'used_today': gemini_used, 'limit': GEMINI_DAILY_LIMIT, 'remaining': max(0, GEMINI_DAILY_LIMIT - gemini_used)},
            'ollama':  {'available': bool(OLLAMA_BASE_URL), 'model': OLLAMA_MODEL},
            'emergent':{'available': bool(EMERGENT_LLM_KEY) and not FREE_ONLY, 'blocked_by_free_only': FREE_ONLY},
        },
        'active_chain': (
            'groq' if GROQ_API_KEY and _under_limit('groq') else
            'gemini' if GEMINI_API_KEY and _under_limit('gemini') else
            'ollama'
        ),
    }
