"""Tests for the i18n / multi-language service (Tier 3 universal)."""
import os
import asyncio

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

import routes_i18n  # noqa: E402


class FakeCursor:
    def __init__(self, items):
        self._items = items

    def __aiter__(self):
        async def gen():
            for i in self._items:
                yield i
        return gen()


class FakeColl:
    def __init__(self):
        self.docs = []

    def find(self, q, p=None):
        return FakeCursor([d for d in self.docs if d.get('lang') == q.get('lang')])

    async def update_one(self, q, u, upsert=False):
        self.docs.append({**q, **u.get('$set', {})})
        return None


class FakeDB:
    def __init__(self):
        self.translations = FakeColl()


def test_languages_lists_supported():
    routes_i18n.db = FakeDB()
    res = asyncio.run(routes_i18n.languages({'email': 'a@admin'}))
    codes = [l['code'] for l in res['languages']]
    assert 'hi' in codes and 'hinglish' in codes and 'en' in codes


def test_get_keys_returns_builtin_defaults():
    routes_i18n.db = FakeDB()
    res = asyncio.run(routes_i18n.get_keys('hi', {'email': 'a@admin'}))
    assert res['keys']['dashboard'] == 'डैशबोर्ड'
    # english returns empty map (source language)
    res_en = asyncio.run(routes_i18n.get_keys('en', {'email': 'a@admin'}))
    assert res_en['keys'] == {}


def test_auto_translate_uses_llm_and_persists():
    routes_i18n.db = FakeDB()
    routes_i18n.chat_completion = lambda s, u, session_id=None, temperature=0.2: "उत्पाद"
    res = asyncio.run(routes_i18n.auto_translate(
        routes_i18n.AutoIn(lang='hi', keys=['products']), {'email': 'a@admin'}))
    assert res['keys']['products'] == 'उत्पाद'
    # persisted
    assert any(d.get('key') == 'products' and d.get('value') == 'उत्पाद' for d in routes_i18n.db.translations.docs)
