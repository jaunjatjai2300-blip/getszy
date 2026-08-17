"""Tests for real (non-simulated) AI Workforce task/workflow execution.

Patches db + the LLM provider so it runs fast with no live services.
"""
import asyncio

import pytest


@pytest.fixture
def mod():
    import routes_ai_workforce
    return routes_ai_workforce


class FakeCol:
    def __init__(self):
        self.docs = {}
        self.updates = []

    async def find_one(self, q, proj=None):
        if isinstance(q, dict) and q.get('id'):
            return self.docs.get(q['id'])
        return None

    async def update_one(self, q, update):
        self.updates.append((q, update))
        if isinstance(q, dict) and q.get('id') in self.docs:
            self.docs[q['id']].update(update.get('$set', {}))
        return None


class FakeDB:
    def __init__(self):
        self.ai_tasks = FakeCol()
        self.ai_workflows = FakeCol()


@pytest.fixture
def setup(mod, monkeypatch):
    db = FakeDB()
    monkeypatch.setattr(mod, 'db', db)
    monkeypatch.setattr(mod, 'chat_completion', lambda *a, **k: asyncio.sleep(0, result='REAL_LLM_OUTPUT'))
    return db


def test_run_task_executes_real_prompt(mod, setup):
    tid = 't1'
    setup.ai_tasks.docs[tid] = {'id': tid, 'user_id': 'u1', 'status': 'queued',
                                'payload': {'prompt': 'write a tagline'}}
    resp = asyncio.run(mod.run_task(tid, user={'id': 'u1'}))
    assert resp['status'] == 'completed'
    assert resp['result'] == {'output': 'REAL_LLM_OUTPUT'}
    assert setup.ai_tasks.docs[tid]['result'] == {'output': 'REAL_LLM_OUTPUT'}


def test_run_task_empty_payload_no_fake(mod, setup):
    tid = 't2'
    setup.ai_tasks.docs[tid] = {'id': tid, 'user_id': 'u1', 'status': 'queued', 'payload': {}}
    resp = asyncio.run(mod.run_task(tid, user={'id': 'u1'}))
    assert resp['status'] == 'completed'
    assert 'note' in resp['result']  # honest: nothing to run, not a fake success


def test_execute_workflow_runs_each_step(mod, setup):
    wid = 'w1'
    setup.ai_workflows.docs[wid] = {'id': wid, 'user_id': 'u1', 'run_count': 0,
                                    'steps': [{'prompt': 'a'}, {'prompt': 'b'}]}
    resp = asyncio.run(mod.execute_workflow(wid, user={'id': 'u1'}))
    assert resp['status'] == 'executed'
    assert len(resp['results']) == 2
    assert all(r['result'] == {'output': 'REAL_LLM_OUTPUT'} for r in resp['results'])
    assert setup.ai_workflows.docs[wid]['run_count'] == 1
