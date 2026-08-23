"""Unit tests for the instant premium composition path.

NOTE: authored without a runnable environment here (no deps/Mongo on this host).
Run these in the project's CI / non-prod environment before any release.
They monkeypatch the managed provider so no network/LLM is required.
"""
import asyncio

import pytest

from builder_agents import (
    FAST_COMPOSITION_PROMPT,
    ProfessionalCompositionError,
    _extract_html,
    compose_site_fast,
    polish_site_async,
)


def _fake_html() -> str:
    return (
        "<!DOCTYPE html><html><head><title>Cafe</title>"
        "<meta name='description' content='x'></head>"
        "<body><h1>Cafe</h1><p>Welcome</p></body></html>"
    )


async def _ok(*_args, **_kwargs) -> str:
    return _fake_html()


async def _bad(*_args, **_kwargs) -> str:
    return "this is not html at all"


def test_prompt_forbids_fabricated_proof_and_is_premium():
    assert "Never invent testimonials" in FAST_COMPOSITION_PROMPT
    assert "premium" in FAST_COMPOSITION_PROMPT.lower()


def test_compose_handles_null_brief(monkeypatch):
    captured = {}

    async def _cap(*_args, **kwargs):
        captured["kwargs"] = kwargs
        return _fake_html()

    monkeypatch.setattr("builder_agents.professional_builder_completion", _cap)
    html = asyncio.run(compose_site_fast("a cafe", brief=None, session_id="t"))
    assert html.lower().startswith("<!doctype html")
    assert "user" in captured["kwargs"]


def test_compose_injects_explicit_style_override(monkeypatch):
    captured = {}

    async def _cap(*_args, **kwargs):
        captured["kwargs"] = kwargs
        return _fake_html()

    monkeypatch.setattr("builder_agents.professional_builder_completion", _cap)
    asyncio.run(
        compose_site_fast("a cafe", brief={}, session_id="t", style_profile="dark luxury editorial")
    )
    assert "dark luxury editorial" in captured["kwargs"]["user"]


def test_compose_raises_when_no_html(monkeypatch):
    monkeypatch.setattr("builder_agents.professional_builder_completion", _bad)
    with pytest.raises(ProfessionalCompositionError):
        asyncio.run(compose_site_fast("x", brief={}, session_id="t"))


def test_polish_returns_original_on_provider_failure(monkeypatch):
    monkeypatch.setattr("builder_agents.professional_builder_completion", _bad)
    original = "<html><body>hi</body></html>"
    out = asyncio.run(polish_site_async(original, brief={}, session_id="t"))
    assert out == original


def test_extract_html_strips_fences():
    cleaned = _extract_html("```html\n<!DOCTYPE html><p>1</p>\n```")
    assert cleaned.lower().startswith("<!doctype")
