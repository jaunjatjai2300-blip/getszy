"""LLM Provider — Cost Guard with Multi-Provider Fallback

Priority chain (local free providers first):
  1. Ollama     — local, free, unlimited (3 models on VPS)
  2. LM Studio  — local, free, OpenAI-compatible (longcat2.0, etc.)
  3. Groq       — free tier, 11K req/day
  4. Gemini     — free tier, 1500 req/day
  5. OpenRouter — paid (your credits, many models available)
"""
import os
import json
import asyncio
import httpx
import uuid
import logging
import time
from datetime import datetime, timezone
from tools import get_schemas, execute_tool

logger = logging.getLogger('getszy.llm')

# ── Config ────────────────────────────────────────────────────────────────────
FREE_ONLY        = os.environ.get('FREE_ONLY', 'true').lower() != 'false'
GROQ_API_KEY     = os.environ.get('GROQ_API_KEY', '').strip()
# Default to a strong *free* Groq model. The 8B instant model produces weak,
# "basic" landing pages/scripts; llama-3.3-70b is far higher quality and still
# free on Groq's tier. The RPM/TPM pacer in this module keeps it within limits.
GROQ_MODEL       = os.environ.get('GROQ_MODEL', 'llama-3.3-70b-versatile').strip()
GEMINI_API_KEY   = os.environ.get('GEMINI_API_KEY', '').strip()
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '').strip()
OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'qwen/qwen-2.5-72b-instruct').strip()
OLLAMA_BASE_URL  = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_SECRET    = os.environ.get('OLLAMA_SECRET', '')
LMSTUDIO_BASE_URL = os.environ.get('LMSTUDIO_BASE_URL', 'http://localhost:1234/v1')
LMSTUDIO_MODEL   = os.environ.get('LMSTUDIO_MODEL', 'longcat2.0')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
EMERGENT_MODEL   = os.environ.get('EMERGENT_MODEL', 'gpt-4o-mini')

# Ollama model chain — try primary, then fallbacks
OLLAMA_MODELS = []
_primary = os.environ.get('OLLAMA_MODEL', 'qwen2.5:7b').strip()
_second  = os.environ.get('OLLAMA_MODEL_2', 'qwen2.5-coder:7b').strip()
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


def _is_rate_limited(e: Exception) -> bool:
    """True if the provider rejected us with HTTP 429 (rate limit)."""
    try:
        return isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429
    except Exception:
        return False


def _retry_after(e: Exception, base: float) -> float:
    """Seconds to wait before retrying a rate-limited request (honors Retry-After)."""
    try:
        ra = e.response.headers.get('retry-after')
        if ra:
            return float(ra)
    except Exception:
        pass
    return base


# ── Groq rate limiting (RPM + TPM pacer with adaptive backoff) ──────────────
# Groq's free tier enforces BOTH a requests/min limit AND a tokens/min (TPM)
# limit. The 429s in practice come from the TPM budget (large system+user
# prompts add up fast), not just RPM. So we pace on both axes:
#   * a minimum spacing between call starts (RPM headroom), and
#   * a rolling 60s token budget (TPM headroom).
# We also adapt: a 429 doubles the effective spacing (up to a cap) and honors
# the provider's Retry-After header as a hard cooldown; a success relaxes the
# spacing back toward the baseline so we recover throughput once the limit
# clears. A single lock serializes the whole Groq call (pace + HTTP) so
# concurrency stays at 1 (Groq free tier concurrency is also limited).
GROQ_MAX_RPM = int(os.environ.get('GROQ_MAX_RPM', '15'))
GROQ_MAX_TPM = int(os.environ.get('GROQ_MAX_TPM', '10000'))  # published ~14400; run under it
_groq_min_interval = 60.0 / GROQ_MAX_RPM
_groq_eff_interval = _groq_min_interval   # adaptive: grows on 429, shrinks on success
_groq_last_call = 0.0
_groq_429_until = 0.0                     # monotonic time until which Groq is hard-blocked
_groq_rl_lock = asyncio.Lock()
_groq_tpm_window: list = []               # [(monotonic_ts, est_tokens)] within last 60s


def _est_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token) so we can budget TPM cheaply."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _groq_record_429(e: Exception):
    """On a Groq 429: honor Retry-After and adaptively slow the pacer."""
    global _groq_eff_interval, _groq_429_until
    try:
        ra = float(getattr(e, 'response', None).headers.get('retry-after', 0) or 0)
    except Exception:
        ra = 0.0
    if ra > 0:
        _groq_429_until = max(_groq_429_until, time.monotonic() + ra)
    _groq_eff_interval = min(_groq_eff_interval * 2.0, 30.0)


def _groq_relax():
    """After a successful Groq call, gently recover throughput."""
    global _groq_eff_interval
    _groq_eff_interval = max(_groq_min_interval, _groq_eff_interval * 0.9)


async def _groq_wait_tpm(est_tokens: int):
    """Block until the rolling 60s token budget has room for est_tokens.

    Caller must hold _groq_rl_lock (so the window mutation is race-free).
    """
    global _groq_tpm_window
    now = time.monotonic()
    cutoff = now - 60.0
    _groq_tpm_window = [(t, n) for (t, n) in _groq_tpm_window if t > cutoff]
    used = sum(n for (_, n) in _groq_tpm_window)
    if used + est_tokens > GROQ_MAX_TPM:
        # Wait until the oldest contribution expires, then re-check the budget.
        oldest = _groq_tpm_window[0][0] if _groq_tpm_window else now
        wait = 60.0 - (oldest - cutoff)
        if wait > 0:
            await asyncio.sleep(wait)
            now = time.monotonic()
            _groq_tpm_window = [(t, n) for (t, n) in _groq_tpm_window if t > now - 60.0]
    _groq_tpm_window.append((time.monotonic(), est_tokens))


async def _groq_pace(est_tokens: int = 4096):
    """Enforce RPM spacing + TPM budget + 429 cooldown. Caller holds _groq_rl_lock."""
    global _groq_last_call
    now = time.monotonic()
    # Hard cooldown carried over from a previous Retry-After header.
    if now < _groq_429_until:
        await asyncio.sleep(_groq_429_until - now)
    # Minimum spacing between call starts.
    wait = _groq_eff_interval - (now - _groq_last_call)
    if wait > 0:
        await asyncio.sleep(wait)
    _groq_last_call = time.monotonic()
    # Token budget check (lock held -> no race on the rolling window).
    await _groq_wait_tpm(est_tokens)

# ── Provider implementations ──────────────────────────────────────────────────


# --- Prompt truncation to avoid 413 Payload Too Large ---
# Groq llama-3.3-70b: 128k ctx, but TPM caps request size. Keep safe budget.
_MAX_CHARS_PER_MSG = 48000   # ~12k tokens per message, ~24k total, well under limits

def _truncate(text: str, limit: int = _MAX_CHARS_PER_MSG) -> str:
    if not text or len(text) <= limit:
        return text
    head = int(limit * 0.7)
    tail = limit - head - 40
    return text[:head] + "\n\n...[truncated for token limit]...\n\n" + text[-tail:]

async def _groq(system: str, user: str, temperature: float, max_tokens: int | None = None) -> str:
    system = _truncate(system)
    user = _truncate(user)
    est = _est_tokens(system) + _est_tokens(user) + (max_tokens or 4096)
    async with _groq_rl_lock:
        await _groq_pace(est)
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                r = await client.post(
                    'https://api.groq.com/openai/v1/chat/completions',
                    headers={'Authorization': f'Bearer {GROQ_API_KEY}'},
                    json={
                        'model': GROQ_MODEL,
                        'messages': [
                            {'role': 'system', 'content': system},
                            {'role': 'user', 'content': user},
                        ],
                        'temperature': temperature,
                        'max_tokens': max_tokens or 4096,
                    },
                )
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    _groq_record_429(e)
                raise
            return r.json()['choices'][0]['message']['content']


async def _gemini(system: str, user: str, temperature: float, max_tokens: int | None = None) -> str:
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}',
            json={
                'system_instruction': {'parts': [{'text': system}]},
                'contents': [{'parts': [{'text': user}]}],
                'generationConfig': {'temperature': temperature, 'maxOutputTokens': max_tokens or 8192},
            },
        )
        r.raise_for_status()
        return r.json()['candidates'][0]['content']['parts'][0]['text']


async def _ollama_single(model: str, system: str, user: str, temperature: float, max_tokens: int | None = None) -> str:
    headers = {}
    if OLLAMA_SECRET:
        headers['Authorization'] = f'Bearer {OLLAMA_SECRET}'
    options = {'temperature': temperature}
    if max_tokens:
        options['num_predict'] = max_tokens
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
                'options': options,
            },
        )
        r.raise_for_status()
        return r.json().get('message', {}).get('content', '')


async def _lmstudio(system: str, user: str, temperature: float, max_tokens: int | None = None) -> str:
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            f'{LMSTUDIO_BASE_URL}/chat/completions',
            json={
                'model': LMSTUDIO_MODEL,
                'messages': [
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user},
                ],
                'temperature': temperature,
                'max_tokens': max_tokens or 4096,
                'stream': False,
            },
        )
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content']


async def _ollama_chain(system: str, user: str, temperature: float, max_tokens: int | None = None) -> str:
    """Try each Ollama model in order until one works."""
    last_error = None
    for model in OLLAMA_MODELS:
        try:
            result = await _ollama_single(model, system, user, temperature, max_tokens)
            logger.info(f'LLM: ollama ({model})')
            return result
        except Exception as e:
            logger.warning(f'LLM ollama {model} failed: {e}')
            last_error = e
    raise last_error or RuntimeError('All Ollama models failed')


async def _emergent(system: str, user: str, session_id: str) -> str:
    if FREE_ONLY:
        raise RuntimeError('FREE_ONLY mode: paid LLM blocked. Set FREE_ONLY=false to enable.')
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
    except ImportError:
        raise RuntimeError('emergentintegrations package not installed (optional paid provider).')
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system,
    ).with_model('openai', EMERGENT_MODEL)
    return await chat.send_message(UserMessage(text=user))


async def _openrouter(system: str, user: str, temperature: float, max_tokens: int | None = None) -> str:
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
                'max_tokens': max_tokens or 4096,
            },
        )
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content']


# ── Provider ordering ─────────────────────────────────────────────────────────
# LLM_PROVIDER lets ops pin a primary provider (e.g. groq). Local providers are
# still attempted first when available because they are 100% free & unlimited.
LLM_PROVIDER = os.environ.get('LLM_PROVIDER', '').strip().lower()

def _build_chain(system, user, temperature, session_id, max_tokens: int | None = None) -> list:
    """Return an ordered list of (name, coroutine-factory) to try."""
    chain = []

    # Always offer local free providers first when configured
    if OLLAMA_MODELS:
        chain.append(('ollama', lambda: _ollama_chain(system, user, temperature, max_tokens)))
    chain.append(('lmstudio', lambda: _lmstudio(system, user, temperature, max_tokens)))

    # Cloud free providers
    if GROQ_API_KEY and _under_limit('groq'):
        chain.append(('groq', lambda: _groq(system, user, temperature, max_tokens)))
    if GEMINI_API_KEY and _under_limit('gemini'):
        chain.append(('gemini', lambda: _gemini(system, user, temperature, max_tokens)))

    # Paid providers (only when not in FREE_ONLY mode)
    if OPENROUTER_API_KEY and not FREE_ONLY:
        chain.append(('openrouter', lambda: _openrouter(system, user, temperature, max_tokens)))
    if EMERGENT_LLM_KEY and not FREE_ONLY:
        chain.append(('emergent', lambda: _emergent(system, user, session_id)))

    # Honor explicit LLM_PROVIDER pin: move it to the front of the chain
    if LLM_PROVIDER:
        pinned = [c for c in chain if c[0] == LLM_PROVIDER]
        rest = [c for c in chain if c[0] != LLM_PROVIDER]
        chain = pinned + rest

    return chain


# ── Main entry point ──────────────────────────────────────────────────────────

class LLMServiceUnavailable(Exception):
    """Raised when every configured LLM provider in the fallback chain fails.
    FastAPI converts this to a clean 503 (see server.py) so users never see a raw 500."""


async def chat_completion(
    system: str,
    user: str,
    session_id: str | None = None,
    temperature: float = 0.4,
    max_tokens: int | None = None,
) -> str:
    session_id = session_id or str(uuid.uuid4())

    # Truncate once here so EVERY provider in the chain receives bounded input.
    # Prevents 413 / token-limit errors from oversized or malicious prompts on
    # any backend (previously only Groq was truncated inside _groq).
    system = _truncate(system)
    user = _truncate(user)

    chain = _build_chain(system, user, temperature, session_id, max_tokens)
    last_error = None
    for name, fn in chain:
        # Retry on rate-limit (429) with backoff BEFORE falling back to the next
        # provider. This keeps us on the fast provider (Groq) instead of dropping
        # to slow local Ollama the moment we hit a transient RPM limit during a
        # burst (e.g. the video-factory script fan-out).
        for _attempt in range(4):
            try:
                result = await fn()
                if name == 'groq':
                    _increment('groq')
                    _groq_relax()
                    logger.info(f'LLM: groq ({_count("groq")}/{GROQ_DAILY_LIMIT} today)')
                elif name == 'gemini':
                    _increment('gemini')
                    logger.info(f'LLM: gemini ({_count("gemini")}/{GEMINI_DAILY_LIMIT} today)')
                else:
                    logger.info(f'LLM: {name}')
                return result
            except Exception as e:
                # A 429 is a *transient rate limit*. The global Groq pacer prevents
                # most of these and honors Retry-After itself, so we only retry ONCE
                # here. Extra retries just burn free-tier quota on calls that will
                # keep failing (the "127 calls, nothing generated" waste). After the
                # single retry we fall through to the next provider / give up.
                if _is_rate_limited(e) and _attempt == 0:
                    wait = _retry_after(e, 2.0)
                    logger.warning(f'LLM {name} rate-limited (429); one retry in {wait:.1f}s')
                    await asyncio.sleep(wait)
                    last_error = e
                    continue
                logger.warning(f'LLM {name} failed: {e}')
                last_error = e
                break

    # Surface total AI outages to Sentry (observability of the fallback chain)
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(
            last_error or RuntimeError('All LLM providers failed'),
            extras={'llm_chain': [c[0] for c in chain], 'session_id': session_id},
        )
    except Exception:
        pass

    try:
        from middleware import inc_ollama_failure
        inc_ollama_failure()
    except Exception:
        pass

    raise LLMServiceUnavailable(
        'All LLM providers failed. '
        'Set LLM_PROVIDER appropriately and ensure at least one of '
        'GROQ_API_KEY/GEMINI_API_KEY/OPENROUTER_API_KEY is configured.'
    )


# ── Tool-calling (agentic) providers ────────────────────────────────────────────
# OpenAI-compatible providers support `tools`/`tool_calls`. Ollama supports a
# native tool format. These let agents actually *execute* actions (search the
# store, query courses, compute) instead of only generating text.

async def _openai_style_with_tools(url, headers, model, messages, tools, temperature):
    async with httpx.AsyncClient(timeout=90.0) as client:
        r = await client.post(
            url, headers=headers,
            json={'model': model, 'messages': messages, 'tools': tools,
                  'temperature': temperature, 'max_tokens': 4096},
        )
        r.raise_for_status()
        return r.json()['choices'][0]['message']


async def _groq_with_tools(messages, tools, temperature):
    est = sum(_est_tokens(m.get('content') or '') for m in messages) + 4096
    async with _groq_rl_lock:
        await _groq_pace(est)
        try:
            return await _openai_style_with_tools(
                'https://api.groq.com/openai/v1/chat/completions',
                {'Authorization': f'Bearer {GROQ_API_KEY}'}, GROQ_MODEL, messages, tools, temperature)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                _groq_record_429(e)
            raise


async def _openrouter_with_tools(messages, tools, temperature):
    return await _openai_style_with_tools(
        'https://openrouter.ai/api/v1/chat/completions',
        {'Authorization': f'Bearer {OPENROUTER_API_KEY}', 'HTTP-Referer': 'https://getszy.com', 'X-Title': 'Getszy'},
        OPENROUTER_MODEL, messages, tools, temperature)


async def _lmstudio_with_tools(messages, tools, temperature):
    return await _openai_style_with_tools(
        f'{LMSTUDIO_BASE_URL}/chat/completions',
        {}, LMSTUDIO_MODEL, messages, tools, temperature)


async def _ollama_with_tools(messages, tools, temperature):
    model = OLLAMA_MODELS[0] if OLLAMA_MODELS else 'qwen2.5:7b'
    headers = {}
    if OLLAMA_SECRET:
        headers['Authorization'] = f'Bearer {OLLAMA_SECRET}'
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            f'{OLLAMA_BASE_URL}/api/chat',
            headers=headers,
            json={'model': model, 'messages': messages, 'tools': tools,
                  'stream': False, 'options': {'temperature': temperature}},
        )
        r.raise_for_status()
        return r.json().get('message', {})


def _tool_args(tc: dict) -> dict:
    raw = tc.get('function', {}).get('arguments', {})
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or '{}')
    except Exception:
        return {}


async def chat_completion_with_tools(
    system: str,
    user: str,
    tool_names: list,
    history: list = None,
    session_id: str | None = None,
    temperature: float = 0.4,
    max_tool_rounds: int = 5,
) -> str:
    """Run an agentic chat: the model may call real tools, results are fed back,
    and the loop continues until a final answer is produced.

    Falls back to a plain completion if no tool-capable provider is available.
    """
    session_id = session_id or str(uuid.uuid4())

    # Bound input size for every tool-capable provider too (same guard as above).
    system = _truncate(system)
    user = _truncate(user)

    schemas = get_schemas(tool_names) if tool_names else []
    if not schemas:
        return await chat_completion(system, user, session_id, temperature)

    messages = [{'role': 'system', 'content': system}]
    for h in (history or []):
        role = 'user' if h.get('role') == 'user' else 'assistant'
        if h.get('content'):
            messages.append({'role': role, 'content': h['content']})
    messages.append({'role': 'user', 'content': user})

    provider_fns = []
    if GROQ_API_KEY and _under_limit('groq'):
        provider_fns.append(('groq', lambda m: _groq_with_tools(m, schemas, temperature)))
    if OPENROUTER_API_KEY and not FREE_ONLY:
        provider_fns.append(('openrouter', lambda m: _openrouter_with_tools(m, schemas, temperature)))
    provider_fns.append(('lmstudio', lambda m: _lmstudio_with_tools(m, schemas, temperature)))
    if OLLAMA_MODELS:
        provider_fns.append(('ollama', lambda m: _ollama_with_tools(m, schemas, temperature)))

    last_error = None
    for _ in range(max_tool_rounds):
        msg = None
        for name, fn in provider_fns:
            try:
                msg = await fn(messages)
                logger.info(f'tool-LLM: {name}')
                break
            except Exception as e:
                logger.warning(f'tool-LLM {name} failed: {e}')
                last_error = e
        if msg is None:
            break
        # No tool calls -> final answer
        if not msg.get('tool_calls'):
            return msg.get('content', '') or ''
        # Execute tool calls and feed results back
        messages.append({
            'role': 'assistant',
            'content': msg.get('content') or '',
            'tool_calls': msg['tool_calls'],
        })
        for tc in msg['tool_calls']:
            fn_name = tc.get('function', {}).get('name')
            result = await execute_tool(fn_name, _tool_args(tc))
            messages.append({
                'role': 'tool',
                'tool_call_id': tc.get('id'),
                'content': result,
            })

    # Fallback to a plain (no-tool) completion if the tool loop produced nothing
    try:
        return await chat_completion(system, user, session_id, temperature)
    except Exception:
        if last_error:
            raise last_error
        raise LLMServiceUnavailable('Tool agent failed to produce a response.')


def provider_info() -> dict:
    groq_used   = _count('groq')
    gemini_used = _count('gemini')
    return {
        'free_only': FREE_ONLY,
        'providers': {
            'groq':    {'available': bool(GROQ_API_KEY),   'used_today': groq_used,   'limit': GROQ_DAILY_LIMIT,   'remaining': max(0, GROQ_DAILY_LIMIT - groq_used)},
            'gemini':  {'available': bool(GEMINI_API_KEY), 'used_today': gemini_used, 'limit': GEMINI_DAILY_LIMIT, 'remaining': max(0, GEMINI_DAILY_LIMIT - gemini_used)},
            'ollama':  {'available': True, 'models': OLLAMA_MODELS, 'active_model': OLLAMA_MODELS[0] if OLLAMA_MODELS else None, 'description': '100% free, runs on VPS'},
            'lmstudio':{'available': True, 'model': LMSTUDIO_MODEL, 'base_url': LMSTUDIO_BASE_URL, 'description': '100% free, local OpenAI-compatible'},
            'emergent':{'available': bool(EMERGENT_LLM_KEY) and not FREE_ONLY, 'blocked_by_free_only': FREE_ONLY},
        },
        'active_chain': (
            f'ollama ({OLLAMA_MODELS[0]})' if OLLAMA_MODELS else
            f'lmstudio ({LMSTUDIO_MODEL})' if LMSTUDIO_BASE_URL else
            'groq' if GROQ_API_KEY and _under_limit('groq') else
            'gemini' if GEMINI_API_KEY and _under_limit('gemini') else
            'none'
        ),
    }
