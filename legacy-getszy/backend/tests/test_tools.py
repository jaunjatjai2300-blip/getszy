import os, sys, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')


@pytest.mark.asyncio
async def test_calculate_tool():
    from tools import execute_tool
    assert await execute_tool('calculate', {'expression': '(1200-300)*0.4'}) == '360.0'
    assert 'unsupported' in await execute_tool('calculate', {'expression': 'import os'})


@pytest.mark.asyncio
async def test_search_products_tool(monkeypatch):
    import tools as T, json
    class FakeCur:
        def __init__(self, items): self.items = items
        def limit(self, n): return self
        def __aiter__(self):
            async def gen():
                for i in self.items: yield i
            return gen()
    class FakeColl:
        def find(self, q, proj=None): return FakeCur([{'name': 'Red Saree', 'slug': 'red-saree', 'price': 1500, 'category': 'Saree'}])
    class FakeDB:
        products = FakeColl()
    monkeypatch.setattr(T, 'db', FakeDB())
    res = await T.execute_tool('search_products', {'query': 'saree', 'max_price': 2000})
    data = json.loads(res)
    assert any('Saree' in d['name'] for d in data)


@pytest.mark.asyncio
async def test_tool_agent_loop(monkeypatch):
    import llm_provider as L
    calls = {'n': 0}
    async def fake_llm(messages, schemas=None, temperature=0.4):
        calls['n'] += 1
        if calls['n'] == 1:
            return {'content': '', 'tool_calls': [
                {'id': 'c1', 'type': 'function', 'function': {'name': 'calculate', 'arguments': {'expression': '2+2'}}},
            ]}
        return {'content': 'The answer is 4.', 'tool_calls': None}
    monkeypatch.setattr(L, '_lmstudio_with_tools', fake_llm)
    monkeypatch.setattr(L, '_ollama_with_tools', fake_llm)
    out = await L.chat_completion_with_tools('sys', 'what is 2+2', ['calculate'], history=[], session_id='s1')
    assert '4' in out
    assert calls['n'] == 2


@pytest.mark.asyncio
async def test_agent_chat_uses_tools(monkeypatch):
    import routes_agents as R
    captured = {}
    async def fake(*a, **k):
        captured['tools'] = a[2] if len(a) > 2 else k.get('tool_names')
        return 'Hi from agent with tools'
    monkeypatch.setattr(R, 'chat_completion_with_tools', fake)
    # Avoid the real DB insert at the end of agent_chat
    class FakeColl:
        async def insert_one(self, *a, **k): return None
    class FakeDB:
        agent_chats = FakeColl()
    monkeypatch.setattr(R, 'db', FakeDB())
    res = await R.agent_chat('business-advisor', R.AgentChatIn(message='plan my pricing'), user={'id': 'u1'})
    assert res['response'] == 'Hi from agent with tools'
    # expert agents default to the full tool set
    assert 'search_products' in captured['tools']
