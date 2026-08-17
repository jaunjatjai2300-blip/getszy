"""Behavioral test for Tier 1 #6 NL query: POST /admin/founder/ask.

Mocks kpi() + chat_completion (no live Mongo/LLM).
Run: python -m pytest tests/test_founder_ask.py -v
"""
import os
import asyncio

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

import routes_founder  # noqa: E402


def test_ask_returns_llm_answer():
    async def fake_kpi():
        return {'total_users': 120, 'revenue_total': 5000.0}

    async def fake_llm(system, user, temperature=0.3):
        return 'Neo: revenue is healthy.'

    routes_founder.kpi = fake_kpi
    routes_founder.chat_completion = fake_llm

    async def run():
        return await routes_founder.ask(
            routes_founder.AskIn(question='How are sales today?'))
    res = asyncio.run(run())

    assert res['answer'] == 'Neo: revenue is healthy.'
    assert res['metrics']['total_users'] == 120
