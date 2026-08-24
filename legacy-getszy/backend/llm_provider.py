"""Managed LLM provider policy for Getszy customer workflows.

Customer-facing quality ladder:
  1. Groq       — primary managed model
  2. Gemini     — verified cloud quality fallback
  3. OpenRouter — explicitly enabled fixed-model fallback only
  4. Ollama/LM Studio — local resilience fallback

Hugging Face belongs to media generation and is intentionally not in this
text/website-composition ladder. Optional OpenAI and Tavily integrations remain
isolated to their dedicated workflows and are never auto-selected here.
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
# Race mode fires every configured provider concurrently and returns the first
# valid success. This is the "instant output" guarantee for free/open models:
# whichever model answers first wins, and a single working provider is enough.
LLM_RACE         = os.environ.get('LLM_RACE', 'true').lower() != 'false'
GROQ_API_KEY     = os.environ.get('GROQ_API_KEY', '').strip()
# Live model availability varies by Groq account. The former Llama 3.3 70B
# default was not available to Getszy's account and caused HTTP 404. Qwen 3.6
# 27B is confirmed by the account model list and supports long-context, JSON and
# reasoning workflows used by the professional builder.
GROQ_MODEL       = os.environ.get('GROQ_MODEL', 'qwen/qwen3.6-27b').strip()
GEMINI_API_KEY   = os.environ.get('GEMINI_API_KEY', '').strip()
# Gemini 1.5 Flash is no longer available to this configured key. Keep the model
# configurable, but default to the confirmed stable 2.5 Flash identifier.
GEMINI_MODEL     = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash').strip()
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '').strip()
# Customer output MUST stay free. OpenRouter is only allowed when the chosen model
# carries the explicit `:free` suffix (enforced in _openrouter_customer_allowed).
# Default to a reliable free model and enable it in the race by default.
OPENROUTER_MODEL = os.environ.get('OPENROUTER_MODEL', 'meta-llama/llama-3.1-8b-instruct:free').strip()
# Optional extra free OpenRouter models (comma-separated); each MUST end with :free.
OPENROUTER_FREE_MODELS = [
    m.strip() for m in os.environ.get('OPENROUTER_FREE_MODELS', '').split(',') if m.strip()
]
OPENROUTER_CUSTOMER_FALLBACK = os.environ.get(
    'OPENROUTER_CUSTOMER_FALLBACK', 'true'
).strip().lower() in ('1', 'true', 'yes')
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

# ── Free-tier token/quota guard (compulsory) ─────────────────────────────────
# Every external request is capped comfortably UNDER each provider's published
# free ceiling so we can never trip a 429 / over-quota rejection. Local models
# (Ollama/LM Studio) are exempt — they have no external quota. PAID providers
# (Emergent/gpt-4o-mini) are forbidden by policy regardless of FREE_ONLY.
PER_PROVIDER_MAX_TOKENS = {
    'groq': int(os.environ.get('GROQ_MAX_TOKENS', '4096')),
    'gemini': int(os.environ.get('GEMINI_MAX_TOKENS', '8192')),
    'openrouter': int(os.environ.get('OPENROUTER_MAX_TOKENS', '4096')),
}
TOKEN_BUDGETS = {
    'groq':      {'tpm': int(os.environ.get('GROQ_TPM_LIMIT', '12000')),
                  'daily': int(os.environ.get('GROQ_DAILY_TOKENS', '450000'))},
    'gemini':    {'tpm': int(os.environ.get('GEMINI_TPM_LIMIT', '150000')),
                  'daily': int(os.environ.get('GEMINI_DAILY_TOKENS', '800000'))},
    'openrouter':{'tpm': int(os.environ.get('OPENROUTER_TPM_LIMIT', '12000')),
                  'daily': int(os.environ.get('OPENROUTER_DAILY_TOKENS', '450000'))},
}
# Paid providers are forbidden by policy. Emergent (gpt-4o-mini) is paid.
ALLOW_PAID_PROVIDERS = os.environ.get('ALLOW_PAID_PROVIDERS', 'false').strip().lower() in ('1', 'true', 'yes')
PAID_PROVIDERS = {'emergent'}

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


class _BudgetExceeded(Exception):
    """Provider would exceed its free-tier token budget; treated as a skip."""


# Token usage tracking (estimated) for the free-tier guard.
_TOK_MIN: dict = {}   # provider -> list[(mono_ts, tokens)] within last 60s
_TOK_DAY: dict = {}   # "provider:YYYY-MM-DD" -> tokens


def _within_token_budget(provider: str, est: int) -> bool:
    """True if `est` estimated tokens fit the provider's rolling 60s + daily free budget."""
    if provider in ('ollama', 'lmstudio'):
        return True  # local, no external quota
    cfg = TOKEN_BUDGETS.get(provider)
    if not cfg:
        return True
    now = time.monotonic()
    win = _TOK_MIN.setdefault(provider, [])
    while win and win[0][0] < now - 60.0:
        win.pop(0)
    used_min = sum(n for _, n in win)
    if used_min + est > cfg['tpm']:
        return False
    day_key = f'{provider}:{_today()}'
    if _TOK_DAY.get(day_key, 0) + est > cfg['daily']:
        return False
    return True


def _spend_tokens(provider: str, est: int):
    if provider in ('ollama', 'lmstudio'):
        return
    now = time.monotonic()
    _TOK_MIN.setdefault(provider, []).append((now, est))
    day_key = f'{provider}:{_today()}'
    _TOK_DAY[day_key] = _TOK_DAY.get(day_key, 0) + est


def _budget_wrap(provider: str, fn, est: int):
    """Wrap a provider call so it is skipped (not hard-failed) when its free-tier
    token budget is exhausted, and records estimated usage on success."""
    async def wrapped():
        if not _within_token_budget(provider, est):
            logger.info(f'LLM {provider} skipped: free-tier token budget reached')
            raise _BudgetExceeded(provider)
        result = await fn()
        _spend_tokens(provider, est)
        return result
    return wrapped


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


def _default_validate(text: str | None) -> bool:
    """A provider "succeeded" only if it returned non-empty content.

    We never accept an empty 200 as success — that would surface a blank page
    to the customer. Callers may pass a stricter validator (e.g. HTML shape).
    """
    return bool(text and str(text).strip())


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
            f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent',
            headers={'x-goog-api-key': GEMINI_API_KEY},
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


async def _openrouter(system: str, user: str, temperature: float, max_tokens: int | None = None, model: str | None = None) -> str:
    model = model or OPENROUTER_MODEL
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'HTTP-Referer': 'https://getszy.com',
                'X-Title': 'Getszy',
            },
            json={
                'model': model,
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


def _openrouter_customer_allowed() -> bool:
    """Allow only an explicitly enabled, prepaid-safe OpenRouter fallback.

    Under FREE_ONLY, an operator must deliberately select an OpenRouter model
    with the explicit `:free` suffix. This prevents a model-name change from
    silently spending provider credits on a customer request.
    """
    if not (OPENROUTER_API_KEY and OPENROUTER_CUSTOMER_FALLBACK and OPENROUTER_MODEL):
        return False
    return not FREE_ONLY or OPENROUTER_MODEL.endswith(':free')


# ── Provider ordering ─────────────────────────────────────────────────────────
# Managed cloud providers lead normal customer work. LLM_PROVIDER is retained as
# an operational setting but cannot move a local model ahead of Groq/Gemini.
LLM_PROVIDER = os.environ.get('LLM_PROVIDER', 'groq').strip().lower()


def _build_chain(system, user, temperature, session_id, max_tokens: int | None = None) -> list:
    """Deterministic managed customer provider ladder — FREE-TIER ONLY.

    Order: Groq -> Gemini -> OpenRouter(:free) -> Ollama -> LM Studio.
    Every external call is wrapped with the token-budget guard and capped to a
    safe per-provider max_tokens so we never approach a free quota. Paid
    providers (Emergent/gpt-4o-mini) are hard-blocked by policy.
    """
    chain = []
    cap = PER_PROVIDER_MAX_TOKENS
    mt_groq = min(max_tokens or 10**9, cap['groq'])
    mt_gemini = min(max_tokens or 10**9, cap['gemini'])
    mt_or = min(max_tokens or 10**9, cap['openrouter'])

    if GROQ_API_KEY and _under_limit('groq'):
        est = _est_tokens(system) + _est_tokens(user) + mt_groq
        chain.append(('groq', _budget_wrap('groq', lambda: _groq(system, user, temperature, mt_groq), est)))
    if GEMINI_API_KEY and _under_limit('gemini'):
        est = _est_tokens(system) + _est_tokens(user) + mt_gemini
        chain.append(('gemini', _budget_wrap('gemini', lambda: _gemini(system, user, temperature, mt_gemini), est)))
    if _openrouter_customer_allowed():
        est = _est_tokens(system) + _est_tokens(user) + mt_or
        chain.append(('openrouter', _budget_wrap('openrouter', lambda: _openrouter(system, user, temperature, mt_or), est)))
        for m in OPENROUTER_FREE_MODELS:
            if m.endswith(':free'):
                chain.append((f'openrouter:{m}', _budget_wrap('openrouter', lambda m=m: _openrouter(system, user, temperature, mt_or, model=m), est)))
    if OLLAMA_MODELS:
        est = _est_tokens(system) + _est_tokens(user)
        chain.append(('ollama', _budget_wrap('ollama', lambda: _ollama_chain(system, user, temperature, None), est)))
    if LMSTUDIO_BASE_URL:
        est = _est_tokens(system) + _est_tokens(user)
        chain.append(('lmstudio', _budget_wrap('lmstudio', lambda: _lmstudio(system, user, temperature, None), est)))

    # Paid providers (Emergent) are intentionally never added to the customer chain.
    return chain


# ── Main entry point ──────────────────────────────────────────────────────────

class LLMServiceUnavailable(Exception):
    """Raised when every configured LLM provider in the fallback chain fails.
    FastAPI converts this to a clean 503 (see server.py) so users never see a raw 500."""


def _record_success(name: str):
    """Bookkeeping shared by both the race and sequential paths."""
    if name == 'groq':
        _increment('groq')
        _groq_relax()
        logger.info(f'LLM: groq ({_count("groq")}/{GROQ_DAILY_LIMIT} today)')
    elif name == 'gemini':
        _increment('gemini')
        logger.info(f'LLM: gemini ({_count("gemini")}/{GEMINI_DAILY_LIMIT} today)')
    else:
        logger.info(f'LLM: {name}')


async def _run_provider_race(chain: list, *, session_id: str, validate) -> str:
    """Fire every provider at once; return the first valid success.

    This is what makes free/open models feel instant: we don't wait for Groq to
    fail before trying Gemini — whichever answers first (and passes `validate`)
    wins. A provider returning garbage (empty/invalid 200) is treated as a
    failure so the race continues to a real answer.
    """
    last_error = None

    async def run_one(name, fn):
        try:
            result = await fn()
            if not validate(result):
                logger.warning(f'LLM {name} returned invalid content')
                return (name, None, RuntimeError(f'{name} returned invalid content'))
            return (name, result, None)
        except Exception as e:  # noqa: BLE001 - any provider error is a race loss
            logger.warning(f'LLM {name} failed: {e}')
            return (name, None, e)

    tasks = [asyncio.create_task(run_one(n, f)) for n, f in chain]
    pending = set(tasks)
    try:
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for t in done:
                name, result, err = t.result()
                if err is not None:
                    last_error = err
                    continue
                # First valid success wins — cancel the rest to save quota.
                for p in list(pending):
                    p.cancel()
                _record_success(name)
                logger.info(f'LLM (race winner): {name}')
                return result
        # Every provider failed.
        _report_chain_failure(chain, session_id, last_error)
        raise LLMServiceUnavailable(
            'All LLM providers failed. '
            'Set LLM_PROVIDER appropriately and ensure at least one of '
            'GROQ_API_KEY/GEMINI_API_KEY/OPENROUTER_API_KEY is configured.'
        )
    finally:
        for t in pending:
            t.cancel()


def _report_chain_failure(chain, session_id, last_error):
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


async def _run_provider_chain(chain: list, *, session_id: str, validate=_default_validate) -> str:
    """Run a prepared provider chain with the shared rate-limit/retry discipline.

    With LLM_RACE enabled (default), providers are fired concurrently and the
    first valid answer wins. Otherwise they are tried in order with a single
    429 retry, which keeps deterministic behaviour for callers/tests that pin a
    provider.
    """
    if not chain:
        raise LLMServiceUnavailable('No LLM providers are configured.')

    if LLM_RACE and len(chain) > 1:
        return await _run_provider_race(chain, session_id=session_id, validate=validate)

    last_error = None
    for name, fn in chain:
        # Retry one 429 before dropping to the next provider. The provider-specific
        # pacer controls normal concurrency; this is only a transient recovery path.
        for _attempt in range(4):
            try:
                result = await fn()
                if not validate(result):
                    logger.warning(f'LLM {name} returned invalid content; trying next provider')
                    last_error = RuntimeError(f'{name} returned invalid content')
                    break
                _record_success(name)
                return result
            except Exception as e:
                if _is_rate_limited(e) and _attempt == 0:
                    wait = _retry_after(e, 2.0)
                    logger.warning(f'LLM {name} rate-limited (429); one retry in {wait:.1f}s')
                    await asyncio.sleep(wait)
                    last_error = e
                    continue
                logger.warning(f'LLM {name} failed: {e}')
                last_error = e
                break

    _report_chain_failure(chain, session_id, last_error)
    raise LLMServiceUnavailable(
        'All LLM providers failed. '
        'Set LLM_PROVIDER appropriately and ensure at least one of '
        'GROQ_API_KEY/GEMINI_API_KEY/OPENROUTER_API_KEY is configured.'
    )


async def chat_completion(
    system: str,
    user: str,
    session_id: str | None = None,
    temperature: float = 0.4,
    max_tokens: int | None = None,
    validate=None,
) -> str:
    session_id = session_id or str(uuid.uuid4())

    # Truncate once here so EVERY provider in the chain receives bounded input.
    # Prevents 413 / token-limit errors from oversized or malicious prompts on
    # any backend (previously only Groq was truncated inside _groq).
    system = _truncate(system)
    user = _truncate(user)

    chain = _build_chain(system, user, temperature, session_id, max_tokens)
    return await _run_provider_chain(chain, session_id=session_id, validate=validate or _default_validate)


async def professional_builder_completion(
    system: str,
    user: str,
    session_id: str | None = None,
    temperature: float = 0.4,
    max_tokens: int | None = None,
    validate=None,
) -> str:
    """Quality-first customer builder ladder: Groq 70B -> Gemini -> Qwen/Ollama.

    This intentionally ignores the generic app-wide LLM_PROVIDER pin. Paid
    customer-facing refinements must use the strongest managed quality path, and
    only fall back when its predecessor is unavailable or rate-limited.
    """
    session_id = session_id or str(uuid.uuid4())
    system = _truncate(system)
    user = _truncate(user)
    available = _build_chain(system, user, temperature, session_id, max_tokens)
    rank = {'groq': 0, 'gemini': 1, 'openrouter': 2, 'ollama': 3, 'lmstudio': 4, 'emergent': 5}
    chain = sorted(available, key=lambda item: rank.get(item[0], 99))
    logger.info('LLM professional builder ladder: %s', [name for name, _ in chain])
    return await _run_provider_chain(chain, session_id=session_id, validate=validate or _default_validate)


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
    if _openrouter_customer_allowed():
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
            'groq':    {'available': bool(GROQ_API_KEY), 'model': GROQ_MODEL, 'used_today': groq_used, 'limit': GROQ_DAILY_LIMIT, 'remaining': max(0, GROQ_DAILY_LIMIT - groq_used)},
            'gemini':  {'available': bool(GEMINI_API_KEY), 'model': GEMINI_MODEL, 'used_today': gemini_used, 'limit': GEMINI_DAILY_LIMIT, 'remaining': max(0, GEMINI_DAILY_LIMIT - gemini_used)},
            'ollama':  {'available': True, 'models': OLLAMA_MODELS, 'active_model': OLLAMA_MODELS[0] if OLLAMA_MODELS else None, 'description': '100% free, runs on VPS'},
            'lmstudio':{'available': True, 'model': LMSTUDIO_MODEL, 'base_url': LMSTUDIO_BASE_URL, 'description': '100% free, local OpenAI-compatible'},
            'openrouter': {
                'available': _openrouter_customer_allowed(),
                'model': OPENROUTER_MODEL,
                'customer_fallback_enabled': OPENROUTER_CUSTOMER_FALLBACK,
                'blocked_by_free_only': bool(OPENROUTER_API_KEY) and OPENROUTER_CUSTOMER_FALLBACK and not _openrouter_customer_allowed(),
            },
            'emergent':{'available': bool(EMERGENT_LLM_KEY) and ALLOW_PAID_PROVIDERS, 'blocked_by_paid_policy': True, 'blocked_by_free_only': FREE_ONLY},
        },
        'active_chain': ' -> '.join(
            name for name, _ in _build_chain('', '', 0.0, 'provider-info')
        ) or 'none',
    }
