"""Automated tests for the new Workspace Deepening + Live Co-Host endpoints.

Covers:
  - POST /workspace/{id}/tasks/generate
  - POST /workspace/{id}/version  (snapshot)
  - POST /workspace/{id}/version/{vid}/restore
  - POST /live/session  + /live/session/{id}/next  + /live/session/{id}/suggest

The LLM is mocked so the tests are deterministic and need no provider keys.
Run: python -m pytest tests/test_workspace_live.py -v
"""
import os
import sys
import json
import asyncio
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('DB_NAME', 'getszy_test')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests-32chars-minimum!!')

from db import db  # noqa: E402
import llm_provider  # noqa: E402
import routes_workspace  # noqa: E402
import routes_live  # noqa: E402


USER = {'id': 'test-ws-user', 'email': 'test-ws@getszy.com', 'role': 'customer'}


def _now():
    return datetime.now(timezone.utc).isoformat()


LIVE_JSON = json.dumps({
    "opening": "Welcome to the show, everyone!",
    "segments": [
        {"title": "Intro", "line": "Hey folks, so glad you're here."},
        {"title": "Main", "line": "Let's dive into today's topic."},
        {"title": "Wrap", "line": "Quick recap before we take questions."},
    ],
    "cta": "Subscribe and hit the bell!",
})


async def _fake_live(**kwargs):
    sid = kwargs.get('session_id', '')
    if sid.startswith('suggest-'):
        return "Let's keep the energy up and take a question from the chat!"
    return LIVE_JSON


async def _fake_tasks(**kwargs):
    return json.dumps([
        {"title": "Write the outline", "status": "todo"},
        {"title": "Record the intro", "status": "todo"},
    ])


async def _make_project(pid):
    await db.chat_projects.insert_one(
        {'id': pid, 'user_id': USER['id'], 'title': 'WS test', 'created_at': _now()})


async def _add_messages(pid, n=3):
    docs = []
    for i in range(n):
        docs.append({
            'id': str(uuid.uuid4()), 'project_id': pid, 'user_id': USER['id'],
            'role': 'user' if i % 2 == 0 else 'assistant',
            'content': f'message {i}', 'created_at': _now(),
        })
    await db.chat_messages.insert_many(docs)


async def _cleanup(pid):
    await db.chat_projects.delete_many({'id': pid})
    await db.chat_messages.delete_many({'project_id': pid})
    await db.chat_assets.delete_many({'project_id': pid})
    await db.workspace_tasks.delete_many({'project_id': pid})
    await db.workspace_plans.delete_many({'project_id': pid})
    await db.workspace_versions.delete_many({'project_id': pid})
    await db.live_sessions.delete_many({'user_id': USER['id']})


def test_generate_tasks_persists(monkeypatch):
    monkeypatch.setattr(llm_provider, 'chat_completion', _fake_tasks)
    pid = f'test-{uuid.uuid4().hex}'

    async def _run():
        await _make_project(pid)
        await _add_messages(pid)
        res = await routes_workspace.generate_tasks(pid, USER)
        assert res['ok'] is True
        assert res['count'] == 2
        assert res['tasks'][0]['title'] == 'Write the outline'
        stored = await db.workspace_tasks.count_documents({'project_id': pid})
        assert stored == 2

    try:
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup(pid))


def test_generate_tasks_requires_conversation(monkeypatch):
    monkeypatch.setattr(llm_provider, 'chat_completion', _fake_tasks)
    pid = f'test-{uuid.uuid4().hex}'

    async def _run():
        await _make_project(pid)  # no messages
        try:
            await routes_workspace.generate_tasks(pid, USER)
            assert False, 'expected HTTPException 400'
        except Exception as e:  # noqa: BLE001
            assert getattr(e, 'status_code', None) == 400

    try:
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup(pid))


def test_snapshot_and_restore(monkeypatch):
    monkeypatch.setattr(llm_provider, 'chat_completion', _fake_tasks)
    pid = f'test-{uuid.uuid4().hex}'

    async def _run():
        await _make_project(pid)
        await _add_messages(pid, 3)
        await routes_workspace.generate_tasks(pid, USER)  # creates 2 tasks
        await db.workspace_plans.update_one(
            {'project_id': pid},
            {'$set': {'project_id': pid, 'user_id': USER['id'],
                      'summary': 'plan', 'steps': ['a'], 'updated_at': _now()}},
            upsert=True)

        snap = await routes_workspace.snapshot(pid, routes_workspace.VersionIn(label='v1'), USER)
        vid = snap['id']
        assert snap['message_count'] == 3
        assert snap['task_count'] == 2

        # Tamper with live state.
        await db.chat_messages.delete_many({'project_id': pid})
        await db.workspace_tasks.delete_many({'project_id': pid})
        assert await db.chat_messages.count_documents({'project_id': pid}) == 0

        # Restore must roll everything back exactly.
        rest = await routes_workspace.restore_version(pid, vid, USER)
        assert rest.get('restored') is True
        assert await db.chat_messages.count_documents({'project_id': pid}) == 3
        assert await db.workspace_tasks.count_documents({'project_id': pid}) == 2

    try:
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup(pid))


def test_get_workspace_includes_tasks(monkeypatch):
    monkeypatch.setattr(llm_provider, 'chat_completion', _fake_tasks)
    pid = f'test-{uuid.uuid4().hex}'

    async def _run():
        await _make_project(pid)
        await _add_messages(pid)
        await routes_workspace.generate_tasks(pid, USER)
        ws = await routes_workspace.get_workspace(pid, USER)
        assert ws['project']['id'] == pid
        assert len(ws['tasks']) == 2

    try:
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup(pid))


def test_create_live_session(monkeypatch):
    monkeypatch.setattr(llm_provider, 'chat_completion', _fake_live)

    async def _run():
        sess = await routes_live.create_session(
            routes_live.LiveSessionIn(topic='Launch my course live'), USER)
        assert 'id' in sess
        assert sess['opening']
        assert len(sess['segments']) >= 1
        assert sess['cta']
        assert await db.live_sessions.count_documents({'id': sess['id']}) == 1

    try:
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup('x'))


def test_live_next_cue_progress_and_done(monkeypatch):
    monkeypatch.setattr(llm_provider, 'chat_completion', _fake_live)

    async def _run():
        sess = await routes_live.create_session(
            routes_live.LiveSessionIn(topic='Q&A live'), USER)
        sid = sess['id']
        n = len(sess['segments'])

        first = await routes_live.next_cue(sid, USER)
        assert first['done'] is False
        assert first['cue'] is not None

        last = first
        for _ in range(n + 1):
            last = await routes_live.next_cue(sid, USER)
        assert last['done'] is True
        assert last['cue'] is None
        assert last['progress'].startswith(f'{n}/')

    try:
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup('x'))


def test_live_suggest_line(monkeypatch):
    monkeypatch.setattr(llm_provider, 'chat_completion', _fake_live)

    async def _run():
        sess = await routes_live.create_session(
            routes_live.LiveSessionIn(topic='React live'), USER)
        r = await routes_live.suggest_line(
            sess['id'], routes_live.LiveLineIn(transcript='Thanks for joining!'), USER)
        assert 'line' in r
        assert r['line']

    try:
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup('x'))


def test_create_live_session_short_topic():
    async def _run():
        try:
            await routes_live.create_session(
                routes_live.LiveSessionIn(topic='hi'), USER)
            assert False, 'expected HTTPException 400'
        except Exception as e:  # noqa: BLE001
            assert getattr(e, 'status_code', None) == 400

    try:
        asyncio.run(_run())
    finally:
        asyncio.run(_cleanup('x'))
