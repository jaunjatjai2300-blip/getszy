"""Tests for the SamurAIGPT / Open-Generative-AI media suite engines."""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:27017')
os.environ.setdefault('JWT_SECRET', 'test-only-media-suite-secret')
os.environ.setdefault('HF_TOKEN', 'test-free-token')

import media_providers as mp
import media_models as mm
import media_workflow as mw
import media_shorts as ms
import routes_media_suite as rms
from routes_media_suite import DesignIn


def test_media_provider_info_is_free_and_healthy():
    info = mp.media_provider_info()
    assert info['free_only'] is True
    assert info['healthy'] is True
    assert info['usable']


@pytest.mark.asyncio
async def test_models_endpoint_lists_free_only():
    out = await rms.models()
    assert out['free_only'] is True
    models = out['models']
    # image must include the free FLUX + Pollinations entries
    ids = {m['id'] for m in models['image']}
    assert 'FLUX.1-schnell' in ids and 'pollinations' in ids
    # no paid platforms leak in
    assert all(m['free'] for cap in models.values() for m in cap)


@pytest.mark.asyncio
async def test_providers_and_skills_endpoints():
    assert (await rms.providers())['free_only'] is True
    skills = (await rms.skills())['skills']
    names = {s['name'] for s in skills}
    assert {'generate_image', 'text_to_speech', 'transcribe', 'create_shorts', 'run_workflow'} <= names


@pytest.mark.asyncio
async def test_design_endpoint_uses_free_model_registry(monkeypatch):
    monkeypatch.setattr(
        rms, 'generate_image_model',
        lambda prompt, model_id, w, h: __import__('asyncio').sleep(
            0, result={'image': 'BASE64', 'provider': 'huggingface', 'model': model_id}
        )
    )

    class _Coll:
        def __init__(self):
            self.inserted = None

        async def insert_one(self, doc):
            self.inserted = doc

    coll = _Coll()
    monkeypatch.setattr(rms, 'db', type('DB', (), {'media_designs': coll})())

    result = await rms.design(
        DesignIn(prompt='a calm poster', kind='poster', aspect='4:5', model_id='FLUX.1-schnell'),
        user={'id': 'u1'},
    )
    assert result['image'] == 'BASE64'
    assert result['provider'] == 'huggingface'
    assert coll.inserted['kind'] == 'poster'


@pytest.mark.asyncio
async def test_design_rejects_short_prompt():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await rms.design(DesignIn(prompt='  '), user={'id': 'u1'})
    assert exc.value.status_code == 400


# ── Vibe-Workflow DAG executor ─────────────────────────────────────────────
def test_topo_sort_orders_and_detects_cycle():
    nodes = [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}]
    edges = [{'from': 'a', 'to': 'b'}, {'from': 'b', 'to': 'c'}]
    assert mw.topo_sort(nodes, edges) == ['a', 'b', 'c']
    with pytest.raises(ValueError):
        mw.topo_sort(nodes, [{'from': 'a', 'to': 'b'}, {'from': 'b', 'to': 'a'}])


@pytest.mark.asyncio
async def test_run_graph_feeds_edge_inputs_and_runs_in_order():
    calls = []

    async def img(inputs, params):
        calls.append(('image', params))
        return {'image': 'IMG'}

    async def tts(inputs, params):
        # receives the image output via the edge mapped as 'image'
        calls.append(('tts', inputs))
        return {'audio': 'AUD', 'used': inputs.get('image')}

    graph = {
        'nodes': [
            {'id': 'art', 'type': 'image', 'params': {'prompt': 'cat'}},
            {'id': 'voice', 'type': 'tts', 'params': {'text': 'hi'}},
        ],
        'edges': [{'from': 'art', 'to': 'voice', 'as': 'image'}],
    }
    out = await mw.run_graph(graph, runner_overrides={'image': img, 'tts': tts})
    assert out['art'] == {'image': 'IMG'}
    assert out['voice']['used'] == {'image': 'IMG'}
    assert calls[0][0] == 'image' and calls[1][0] == 'tts'


@pytest.mark.asyncio
async def test_workflow_worker_stores_output(monkeypatch):
    class _Coll:
        def __init__(self):
            self.docs = {}

        async def insert_one(self, d):
            self.docs[d['id']] = d

        async def update_one(self, q, u):
            self.docs[q['id']].update(u['$set'])

    coll = _Coll()
    monkeypatch.setattr(rms, 'db', type('DB', (), {'media_workflows': coll})())
    monkeypatch.setattr(rms, 'run_graph', lambda graph: __import__('asyncio').sleep(0, result={'n1': {'x': 1}}))
    await coll.insert_one({'id': 'j1', 'status': 'queued'})
    await rms._workflow_worker('j1', {'nodes': [{'id': 'n1', 'type': 'image', 'params': {}}], 'edges': []})
    assert coll.docs['j1']['status'] == 'completed'
    assert coll.docs['j1']['outputs'] == {'n1': {'x': 1}}


# ── Shorts / Reel planner (pure helpers) ───────────────────────────────────
def test_shorts_caption_planning_and_srt():
    sents = ms.split_sentences('Hello world. This is a test! Really?')
    assert sents == ['Hello world.', 'This is a test!', 'Really?']
    caps = ms.assign_timeline(sents, 9.0)
    assert len(caps) == 3
    assert caps[0]['start'] == 0.0
    assert caps[-1]['end'] == 9.0
    srt = ms.make_srt(caps)
    assert '1\n00:00:00,000 --> 00:00:03,00' in srt or '00:00:03,000' in srt
    cmd = ms.build_shorts_command('in.mp4', 'out.mp4', 'cap.srt', '9:16')
    assert any('crop=720:1280' in c for c in cmd)
    assert any('subtitles=' in c for c in cmd)


@pytest.mark.asyncio
async def test_shorts_worker_records_result(monkeypatch):
    class _Coll:
        def __init__(self):
            self.docs = {}

        async def insert_one(self, d):
            self.docs[d['id']] = d

        async def update_one(self, q, u):
            self.docs[q['id']].update(u['$set'])

    coll = _Coll()
    monkeypatch.setattr(rms, 'db', type('DB', (), {'media_shorts': coll})())
    monkeypatch.setattr(
        rms, 'run_shorts',
        lambda source, params: __import__('asyncio').sleep(0, result={'output': '/tmp/shorts_out.mp4'})
    )
    await coll.insert_one({'id': 's1', 'status': 'queued'})
    await rms._shorts_worker('s1', b'bytes', {'orientation': '9:16'})
    assert coll.docs['s1']['status'] == 'completed'
    assert coll.docs['s1']['result']['output'] == '/tmp/shorts_out.mp4'
