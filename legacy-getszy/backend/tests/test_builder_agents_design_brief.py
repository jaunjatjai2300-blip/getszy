import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:27017')
os.environ.setdefault('JWT_SECRET', 'test-only-design-brief-fast-secret-32chars!!')

import builder_agents


class _ProviderDown(Exception):
    pass


async def _raises(*args, **kwargs):
    raise _ProviderDown('all providers failed (e.g. Groq 429)')


async def _bad_json(*args, **kwargs):
    return 'Sure! Here is your design: not actually JSON.'


async def _good_design_json(*args, **kwargs):
    return (
        '{"palette": {"primary": "#111827", "secondary": "#2563eb", "accent": "#f59e0b", '
        '"bg": "#ffffff", "text": "#111827"}, "fonts": {"display": "Space Grotesk", "body": "Inter"}, '
        '"sections": [{"name": "hero", "layout": "split", "description": "hero", '
        '"visual_style": "gradient", "elements": ["heading"]}], "animations": ["fade-in"]}'
    )


@pytest.mark.asyncio
async def test_design_brief_fast_returns_none_on_provider_failure(monkeypatch):
    monkeypatch.setattr(builder_agents, 'professional_builder_completion', _raises)
    result = await builder_agents.design_brief_fast('Build a bakery site', {}, 'sess')
    assert result is None


@pytest.mark.asyncio
async def test_design_brief_fast_returns_none_on_unparseable_output(monkeypatch):
    monkeypatch.setattr(builder_agents, 'professional_builder_completion', _bad_json)
    result = await builder_agents.design_brief_fast('Build a bakery site', {}, 'sess')
    assert result is None


@pytest.mark.asyncio
async def test_design_brief_fast_returns_none_on_timeout(monkeypatch):
    import asyncio

    async def _hangs(*args, **kwargs):
        await asyncio.sleep(999)

    monkeypatch.setattr(builder_agents, 'professional_builder_completion', _hangs)
    monkeypatch.setattr(builder_agents, '_DESIGN_BRIEF_TIMEOUT_SEC', 0.05)
    result = await builder_agents.design_brief_fast('Build a bakery site', {}, 'sess')
    assert result is None


@pytest.mark.asyncio
async def test_design_brief_fast_returns_parsed_design_on_success(monkeypatch):
    monkeypatch.setattr(builder_agents, 'professional_builder_completion', _good_design_json)
    result = await builder_agents.design_brief_fast('Build a bakery site', {}, 'sess')
    assert result['palette']['primary'] == '#111827'
    assert result['fonts']['display'] == 'Space Grotesk'


@pytest.mark.asyncio
async def test_compose_site_fast_falls_back_to_single_call_when_design_call_fails(monkeypatch):
    calls = []

    async def fake_completion(system, user, session_id=None, temperature=0.4, max_tokens=None):
        calls.append(system)
        if system == builder_agents.DESIGNER_PROMPT:
            raise _ProviderDown('groq 429, all providers failed')
        return (
            '<!DOCTYPE html><html><head><title>Bakery</title></head><body>'
            + ('x' * 4000) + '</body></html>'
        )

    monkeypatch.setattr(builder_agents, 'professional_builder_completion', fake_completion)
    html = await builder_agents.compose_site_fast('Build a bakery site', {}, 'sess')

    assert html.lower().startswith('<!doctype html')
    assert calls[0] == builder_agents.DESIGNER_PROMPT  # design step attempted first
    assert builder_agents.FAST_COMPOSITION_PROMPT in calls  # composition still ran despite design failure


@pytest.mark.asyncio
async def test_compose_site_fast_forwards_design_brief_into_composition_prompt(monkeypatch):
    seen_user_messages = []

    async def fake_completion(system, user, session_id=None, temperature=0.4, max_tokens=None):
        seen_user_messages.append((system, user))
        if system == builder_agents.DESIGNER_PROMPT:
            return await _good_design_json()
        return (
            '<!DOCTYPE html><html><head><title>Bakery</title></head><body>'
            + ('x' * 4000) + '</body></html>'
        )

    monkeypatch.setattr(builder_agents, 'professional_builder_completion', fake_completion)
    await builder_agents.compose_site_fast('Build a bakery site', {}, 'sess')

    compose_user_msg = next(
        user for system, user in seen_user_messages if system == builder_agents.FAST_COMPOSITION_PROMPT
    )
    assert 'DESIGN BRIEF' in compose_user_msg
    assert '#111827' in compose_user_msg
