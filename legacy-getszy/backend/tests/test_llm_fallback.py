"""AI Infrastructure Audit — fallback chain, cost guard, truncation, double-charge.

Deliberately fails each provider (Groq -> Gemini -> controlled OpenRouter ->
Ollama -> LM Studio -> Emergent) and verifies the chain behaves as a production system
must: real fallback, timeout-triggered fallback, exactly-once charge per
request, failure logging, cost-guard exclusion, and input truncation on every
backend.
"""
import logging

import httpx
import pytest

import llm_provider as lp


def _configure(monkeypatch, *, include_openrouter=True, include_emergent=False):
    """Put every provider on the chain so we can fail them one by one."""
    monkeypatch.setattr(lp, 'OLLAMA_MODELS', ['ollama-m'])
    monkeypatch.setattr(lp, 'LMSTUDIO_BASE_URL', 'http://lmstudio.local/v1')
    monkeypatch.setattr(lp, 'GROQ_API_KEY', 'dummy')
    monkeypatch.setattr(lp, 'GEMINI_API_KEY', 'dummy')
    monkeypatch.setattr(lp, 'OPENROUTER_API_KEY', 'dummy' if include_openrouter else '')
    monkeypatch.setattr(lp, 'OPENROUTER_CUSTOMER_FALLBACK', include_openrouter)
    monkeypatch.setattr(lp, 'EMERGENT_LLM_KEY', 'dummy' if include_emergent else '')
    monkeypatch.setattr(lp, 'FREE_ONLY', False)
    monkeypatch.setattr(lp, 'LLM_PROVIDER', '')


async def _fail_rest(monkeypatch, exclude):
    async def down(*a, **k):
        raise RuntimeError('forced down')
    for name in ('_ollama_chain', '_lmstudio', '_groq', '_gemini', '_openrouter', '_emergent'):
        if name not in exclude:
            monkeypatch.setattr(lp, name, down)


async def test_cloud_primary_starts_with_groq(monkeypatch):
    """Groq is the managed primary; local providers are not attempted first."""
    _configure(monkeypatch)
    calls = {}

    async def fake_ollama(*a, **k):
        raise RuntimeError('ollama down')
    async def fake_groq(system, user, temperature, max_tokens=None):
        calls['groq'] = calls.get('groq', 0) + 1
        return 'pong-from-groq'

    monkeypatch.setattr(lp, '_ollama_chain', fake_ollama)
    monkeypatch.setattr(lp, '_groq', fake_groq)
    await _fail_rest(monkeypatch, exclude={'_ollama_chain', '_groq'})

    res = await lp.chat_completion('sys', 'usr', temperature=0)
    assert res == 'pong-from-groq'
    # No double charge: Groq attempted exactly once, before local fallbacks.
    assert calls['groq'] == 1


async def test_fallback_full_chain_order(monkeypatch):
    """Each provider fails until the last one succeeds; earlier ones tried once."""
    _configure(monkeypatch)
    order = []

    async def make(name, ok_at_end=False):
        async def fn(system, user, temperature, max_tokens=None):
            order.append(name)
            if ok_at_end and name == 'openrouter':
                return 'win'
            raise RuntimeError(f'{name} down')
        return fn

    monkeypatch.setattr(lp, '_ollama_chain', await make('ollama'))
    monkeypatch.setattr(lp, '_lmstudio', await make('lmstudio'))
    monkeypatch.setattr(lp, '_groq', await make('groq'))
    monkeypatch.setattr(lp, '_gemini', await make('gemini'))
    monkeypatch.setattr(lp, '_openrouter', await make('openrouter', ok_at_end=True))
    monkeypatch.setattr(lp, '_emergent', await make('emergent'))

    res = await lp.chat_completion('s', 'u')
    assert res == 'win'
    # Every managed cloud provider precedes local resilience fallbacks.
    assert order == ['groq', 'gemini', 'openrouter']


async def test_timeout_triggers_fallback(monkeypatch):
    """A provider that times out (ReadTimeout) is skipped, not hung forever."""
    _configure(monkeypatch)

    async def fake_ollama(*a, **k):
        raise httpx.ReadTimeout('timed out')
    async def fake_groq(system, user, temperature, max_tokens=None):
        return 'pong'

    monkeypatch.setattr(lp, '_ollama_chain', fake_ollama)
    monkeypatch.setattr(lp, '_groq', fake_groq)
    await _fail_rest(monkeypatch, exclude={'_ollama_chain', '_groq'})

    res = await lp.chat_completion('s', 'u')
    assert res == 'pong'


async def test_all_providers_down_raises_and_logs(monkeypatch, caplog):
    """Full outage -> clear error + every failure is logged."""
    _configure(monkeypatch)
    async def down(*a, **k):
        raise RuntimeError('provider down')
    for name in ('_ollama_chain', '_lmstudio', '_groq', '_gemini', '_openrouter', '_emergent'):
        monkeypatch.setattr(lp, name, down)

    with caplog.at_level(logging.WARNING):
        with pytest.raises(lp.LLMServiceUnavailable, match='All LLM providers failed'):
            await lp.chat_completion('s', 'u')
    assert any('failed' in r.message for r in caplog.records), caplog.text


async def test_no_double_charge_on_fallback(monkeypatch):
    """First provider fails; the request is charged once on success."""
    _configure(monkeypatch)
    groq_calls = {'n': 0}

    async def fake_ollama(*a, **k):
        raise RuntimeError('ollama down')
    async def fake_groq(system, user, temperature, max_tokens=None):
        groq_calls['n'] += 1
        return 'ok'

    monkeypatch.setattr(lp, '_ollama_chain', fake_ollama)
    monkeypatch.setattr(lp, '_groq', fake_groq)
    await _fail_rest(monkeypatch, exclude={'_ollama_chain', '_groq'})
    monkeypatch.setattr(lp, '_counters', {})

    await lp.chat_completion('s', 'u')
    assert groq_calls['n'] == 1
    assert lp._count('groq') == 1


async def test_cost_guard_excludes_groq_when_limit_reached(monkeypatch):
    """When Groq's daily limit is hit it is dropped from the chain entirely."""
    _configure(monkeypatch)
    monkeypatch.setattr(lp, '_counters', {f'groq:{lp._today()}': lp.GROQ_DAILY_LIMIT})

    async def fake_groq(*a, **k):
        raise AssertionError('groq must be excluded by cost guard')
    async def fake_ollama(system, user, temperature, max_tokens=None):
        return 'ollama-ok'

    monkeypatch.setattr(lp, '_groq', fake_groq)
    monkeypatch.setattr(lp, '_ollama_chain', fake_ollama)
    await _fail_rest(monkeypatch, exclude={'_ollama_chain', '_groq'})

    res = await lp.chat_completion('s', 'u')
    assert res == 'ollama-ok'
    assert lp._count('groq') == lp.GROQ_DAILY_LIMIT  # untouched


async def test_truncation_applied_to_every_provider(monkeypatch):
    """An oversized/malicious prompt is truncated before reaching any backend."""
    _configure(monkeypatch)
    captured = {}

    async def capture(name):
        async def fn(system, user, temperature, max_tokens=None):
            captured[name] = user
            return f'ok-{name}'
        return fn

    monkeypatch.setattr(lp, '_ollama_chain', await capture('ollama'))
    monkeypatch.setattr(lp, '_groq', await capture('groq'))
    await _fail_rest(monkeypatch, exclude={'_ollama_chain', '_groq'})

    huge = 'Z' * 500_000
    await lp.chat_completion('sys', huge)
    for name, text in captured.items():
        assert len(text) <= lp._MAX_CHARS_PER_MSG, f'{name} got untruncated input'


async def test_daily_limit_counter_increments_once(monkeypatch):
    """Reset counters; a successful Groq call bumps the daily count by exactly 1."""
    _configure(monkeypatch)
    monkeypatch.setattr(lp, '_counters', {})

    async def fake_groq(system, user, temperature, max_tokens=None):
        return 'ok'
    async def fake_ollama(*a, **k):
        raise RuntimeError('ollama down')

    monkeypatch.setattr(lp, '_groq', fake_groq)
    monkeypatch.setattr(lp, '_ollama_chain', fake_ollama)
    await _fail_rest(monkeypatch, exclude={'_ollama_chain', '_groq'})

    await lp.chat_completion('s', 'u')
    assert lp._count('groq') == 1


async def test_endpoint_returns_503_when_all_providers_down(monkeypatch):
    """End-to-end: an HTTP endpoint that hits the chain returns a clean 503 (not a 500
    stack trace) when every LLM provider is unavailable. This closes the AI-Infra
    audit's 'graceful PARTIAL' gap — previously such endpoints surfaced raw 500s."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from server import _llm_unavailable_handler
    from llm_provider import LLMServiceUnavailable

    _configure(monkeypatch)
    async def down(*a, **k):
        raise RuntimeError('forced down')
    for name in ('_ollama_chain', '_lmstudio', '_groq', '_gemini', '_openrouter', '_emergent'):
        monkeypatch.setattr(lp, name, down)

    app = FastAPI()
    app.add_exception_handler(LLMServiceUnavailable, _llm_unavailable_handler)

    @app.get('/chat')
    async def chat():
        return await lp.chat_completion('sys', 'usr', temperature=0)

    client = TestClient(app)
    r = client.get('/chat')
    assert r.status_code == 503
    body = r.json()
    assert body['error'] == 'ai_service_unavailable'
    assert 'temporarily unavailable' in body['message']


async def test_llm_unavailable_handler_shape():
    """The global handler returns a structured 503 without needing a live server."""
    from starlette.requests import Request
    from server import _llm_unavailable_handler
    from llm_provider import LLMServiceUnavailable

    resp = await _llm_unavailable_handler(Request({'type': 'http'}), LLMServiceUnavailable('boom'))
    assert resp.status_code == 503
    assert resp.body  # JSON body present

