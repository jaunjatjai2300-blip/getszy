"""Reliability-suite tests: deterministic premium fallback, LLM validation, race.

These run without a live Mongo/LLM (providers and compose are monkeypatched), so
they exercise the production-suite guarantees locally: the customer ALWAYS gets a
complete premium page, garbage 200s are rejected, and race mode returns fast.
"""
import pytest

import llm_provider as lp
import routes_builder as builder_routes
import builder_agents
from builder_agents import _premium_template


# ── Premium template fallback (the "no error, ever" guarantee) ────────────────
def test_premium_template_is_valid_and_premium():
    html = _premium_template(
        'a coffee shop',
        {
            'brand_name': 'Brew & Co',
            'primary_goal': 'sell coffee online',
            'primary_cta': 'Order coffee',
            'audience': 'city professionals',
            'proof_points': ['Trusted by 200+ offices'],
        },
    )
    assert html.lower().startswith('<!doctype html')
    assert '</html>' in html.lower()
    assert '<title>' in html.lower()
    assert 'name="viewport"' in html.lower()
    assert html.lower().count('<h1') == 1, 'exactly one H1 required'
    assert 'Brew' in html
    # No fabrication / placeholder trigger words that fail the quality preflight.
    assert 'lorem' not in html.lower()
    assert '[your' not in html.lower()
    assert 'guarantee' not in html.lower()
    # Tailwind CDN present so the page renders styled.
    assert 'cdn.tailwindcss.com' in html


def test_premium_template_passes_core_quality_checks():
    from builder_quality import evaluate_landing_page_quality
    html = _premium_template('a yoga studio', {'brand_name': 'Calm'})
    report = evaluate_landing_page_quality(html, {'brand_name': 'Calm'})
    assert report['status'] in ('ready_for_human_review', 'needs_work')
    # It must at least clear the structural/markup required checks.
    assert report['required_checks_passed'] >= 10


@pytest.mark.asyncio
async def test_safe_compose_falls_back_to_template(monkeypatch):
    async def _boom(*_a, **_k):
        raise RuntimeError('all providers down')

    monkeypatch.setattr(builder_agents, 'compose_site_fast', _boom)
    html, used_fallback = await builder_routes._safe_compose('a cafe', 'sess', {'brand_name': 'Cafe'})
    assert used_fallback is True
    assert html.lower().startswith('<!doctype html')
    assert 'Cafe' in html


# ── Provider validation: reject empty/invalid 200s ───────────────────────────
@pytest.mark.asyncio
async def test_provider_chain_rejects_empty_content(monkeypatch):
    monkeypatch.setattr(lp, 'GROQ_API_KEY', 'x')
    monkeypatch.setattr(lp, 'GEMINI_API_KEY', 'x')
    monkeypatch.setattr(lp, 'OLLAMA_MODELS', ['o'])

    async def empty(*_a, **_k):
        return ''  # a 200 with no content must NOT be accepted

    monkeypatch.setattr(lp, '_groq', empty)
    monkeypatch.setattr(lp, '_gemini', empty)
    monkeypatch.setattr(lp, '_ollama_chain', empty)

    with pytest.raises(lp.LLMServiceUnavailable):
        await lp.chat_completion('s', 'u')


# ── Race mode: first valid success wins (instant output) ─────────────────────
@pytest.mark.asyncio
async def test_race_returns_first_valid_success(monkeypatch):
    monkeypatch.setattr(lp, 'GROQ_API_KEY', 'x')
    monkeypatch.setattr(lp, 'GEMINI_API_KEY', 'x')
    monkeypatch.setattr(lp, 'OLLAMA_MODELS', ['o'])

    async def groq(*_a, **_k):
        return 'from-groq'

    async def gemini(*_a, **_k):
        return 'from-gemini'

    async def ollama(*_a, **_k):
        return 'from-ollama'

    monkeypatch.setattr(lp, '_groq', groq)
    monkeypatch.setattr(lp, '_gemini', gemini)
    monkeypatch.setattr(lp, '_ollama_chain', ollama)

    res = await lp.chat_completion('s', 'u')
    assert res in ('from-groq', 'from-gemini', 'from-ollama')


@pytest.mark.asyncio
async def test_race_still_raises_when_all_fail(monkeypatch):
    monkeypatch.setattr(lp, 'GROQ_API_KEY', 'x')
    monkeypatch.setattr(lp, 'GEMINI_API_KEY', 'x')
    monkeypatch.setattr(lp, 'OLLAMA_MODELS', ['o'])

    async def down(*_a, **_k):
        raise RuntimeError('down')

    monkeypatch.setattr(lp, '_groq', down)
    monkeypatch.setattr(lp, '_gemini', down)
    monkeypatch.setattr(lp, '_ollama_chain', down)

    with pytest.raises(lp.LLMServiceUnavailable):
        await lp.chat_completion('s', 'u')
