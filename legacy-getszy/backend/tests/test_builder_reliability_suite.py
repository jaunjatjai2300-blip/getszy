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


# ── Free-tier guard: no paid models, token budgets ───────────────────────────
@pytest.mark.asyncio
async def test_emergent_is_never_in_customer_chain(monkeypatch):
    """Paid providers (Emergent/gpt-4o-mini) must be excluded from the chain
    even if a key is configured and FREE_ONLY is off."""
    monkeypatch.setattr(lp, 'GROQ_API_KEY', 'x')
    monkeypatch.setattr(lp, 'EMERGENT_LLM_KEY', 'paid-key')
    monkeypatch.setattr(lp, 'FREE_ONLY', False)
    monkeypatch.setattr(lp, 'ALLOW_PAID_PROVIDERS', False)

    async def groq(*_a, **_k):
        return 'ok'

    monkeypatch.setattr(lp, '_groq', groq)
    monkeypatch.setattr(lp, '_gemini', RuntimeError('down'))
    monkeypatch.setattr(lp, '_ollama_chain', RuntimeError('down'))
    monkeypatch.setattr(lp, '_lmstudio', RuntimeError('down'))
    monkeypatch.setattr(lp, '_openrouter', RuntimeError('down'))

    res = await lp.chat_completion('s', 'u')
    assert res == 'ok'
    names = [n for n, _ in lp._build_chain('s', 'u', 0.4, 'sid')]
    assert 'emergent' not in names


@pytest.mark.asyncio
async def test_openrouter_requires_free_model_under_free_only(monkeypatch):
    """Under FREE_ONLY, an OpenRouter model without the `:free` suffix is excluded."""
    monkeypatch.setattr(lp, 'FREE_ONLY', True)
    monkeypatch.setattr(lp, 'OPENROUTER_API_KEY', 'x')
    monkeypatch.setattr(lp, 'OPENROUTER_MODEL', 'anthropic/claude-3.5-sonnet')
    monkeypatch.setattr(lp, 'OPENROUTER_CUSTOMER_FALLBACK', True)
    monkeypatch.setattr(lp, 'OPENROUTER_FREE_MODELS', [])

    names = [n for n, _ in lp._build_chain('s', 'u', 0.4, 'sid')]
    assert not any(n.startswith('openrouter') for n in names)

    # A `:free` model is allowed.
    monkeypatch.setattr(lp, 'OPENROUTER_MODEL', 'meta-llama/llama-3.1-8b-instruct:free')
    names2 = [n for n, _ in lp._build_chain('s', 'u', 0.4, 'sid')]
    assert any(n.startswith('openrouter') for n in names2)


@pytest.mark.asyncio
async def test_token_budget_skip_when_exhausted(monkeypatch):
    """When Groq's rolling token budget is spent, it is skipped and Gemini wins."""
    monkeypatch.setattr(lp, 'GROQ_API_KEY', 'x')
    monkeypatch.setattr(lp, 'GEMINI_API_KEY', 'x')
    monkeypatch.setattr(lp, 'TOKEN_BUDGETS', {'groq': {'tpm': 100, 'daily': 10**9},
                                              'gemini': {'tpm': 10**9, 'daily': 10**9},
                                              'openrouter': {'tpm': 10**9, 'daily': 10**9}})
    monkeypatch.setattr(lp, '_TOK_MIN', {'groq': [(0.0, 10**9)]})  # already over TPM
    monkeypatch.setattr(lp, '_TOK_DAY', {})

    order = []

    async def groq(*_a, **_k):
        order.append('groq')
        return 'groq-ok'

    async def gemini(*_a, **_k):
        order.append('gemini')
        return 'gemini-ok'

    monkeypatch.setattr(lp, '_gemini', gemini)
    monkeypatch.setattr(lp, '_groq', groq)
    monkeypatch.setattr(lp, '_ollama_chain', RuntimeError('down'))
    monkeypatch.setattr(lp, '_lmstudio', RuntimeError('down'))
    monkeypatch.setattr(lp, '_openrouter', RuntimeError('down'))

    res = await lp.chat_completion('s', 'u')
    assert res == 'gemini-ok'
    assert 'groq' not in order  # skipped, never attempted


@pytest.mark.asyncio
async def test_per_request_max_tokens_is_capped(monkeypatch):
    """A caller requesting a huge max_tokens must be capped to the free-tier cap."""
    monkeypatch.setattr(lp, 'GROQ_API_KEY', 'x')
    captured = {}

    async def groq(system, user, temperature, max_tokens=None):
        captured['max_tokens'] = max_tokens
        return 'ok'

    monkeypatch.setattr(lp, '_groq', groq)
    monkeypatch.setattr(lp, '_gemini', RuntimeError('down'))
    monkeypatch.setattr(lp, '_ollama_chain', RuntimeError('down'))
    monkeypatch.setattr(lp, '_lmstudio', RuntimeError('down'))
    monkeypatch.setattr(lp, '_openrouter', RuntimeError('down'))

    await lp.chat_completion('s', 'u', max_tokens=1_000_000)
    assert captured['max_tokens'] <= lp.PER_PROVIDER_MAX_TOKENS['groq']


# ── Premium template variety ───────────────────────────────────────────────
def test_premium_template_selects_vertical():
    from builder_agents import _vertical_for, _premium_template
    assert _vertical_for({}, 'a family pizza restaurant in Brooklyn') == 'restaurant'
    assert _vertical_for({}, 'a B2B SaaS analytics dashboard') == 'saas'
    assert _vertical_for({}, 'freelance photographer portfolio') == 'portfolio'
    assert _vertical_for({}, 'online store selling sneakers') == 'ecommerce'
    assert _vertical_for({}, 'a yoga and wellness clinic') == 'health'
    assert _vertical_for({}, 'a generic consultancy') == 'default'


def test_premium_template_vertical_sections_render():
    from builder_agents import _premium_template
    html = _premium_template('a family pizza restaurant', {'brand_name': 'Forno', 'vertical': 'restaurant'})
    assert 'Menu' in html
    assert 'Visit' in html
    # still exactly one H1, valid, premium
    assert html.lower().count('<h1') == 1
    assert 'cdn.tailwindcss.com' in html
    assert 'guarantee' not in html.lower()


def test_premium_template_vertical_default_fallback():
    from builder_agents import _premium_template
    html = _premium_template('a consultancy', {'brand_name': 'Northwind'})
    assert 'Why it works' in html
    assert html.lower().startswith('<!doctype html')
