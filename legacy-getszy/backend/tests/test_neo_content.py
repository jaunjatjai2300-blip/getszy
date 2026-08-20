"""Tests for the universal AI content engine (Tier 3 Neo Studio).

Mocks the LLM; verifies both AI path and template fallback.
Run: python -m pytest tests/test_neo_content.py -v
"""
import os
import asyncio

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

import routes_neo_content  # noqa: E402


def test_generate_uses_ai_when_available(monkeypatch):
    async def _ai_copy(*args, **kwargs):
        return "AI generated copy"
    monkeypatch.setattr(routes_neo_content, 'chat_completion', _ai_copy)
    res = asyncio.run(routes_neo_content.generate(
        routes_neo_content.GenerateIn(type='ad_copy', context={'name': 'Chai'}, language='hinglish'), {'email': 'a@admin'}))
    assert res['content'] == 'AI generated copy'
    assert res['source'] == 'ai'


def test_generate_falls_back_to_template():
    def boom(*a, **k):
        raise RuntimeError("llm down")
    routes_neo_content.chat_completion = boom
    res = asyncio.run(routes_neo_content.generate(
        routes_neo_content.GenerateIn(type='product_description', context={'name': 'Chai', 'category': 'beverages'}), {'email': 'a@admin'}))
    assert res['source'] == 'template'
    assert 'Chai' in res['content']


def test_translate_fallback():
    routes_neo_content.chat_completion = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down"))
    res = asyncio.run(routes_neo_content.translate(
        routes_neo_content.TranslateIn(text='Hello', to='hi'), {'email': 'a@admin'}))
    # Honest failure: we must NOT pretend an untranslated string is a translation.
    assert res['source'] == 'none'
    assert res['translated'] == 'Hello'
