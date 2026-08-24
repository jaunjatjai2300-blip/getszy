"""Tests for the SamurAIGPT / Open-Generative-AI media suite engines."""
import os
import sys
import io
import base64
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:27017')
os.environ.setdefault('JWT_SECRET', 'test-only-media-suite-secret')
os.environ.setdefault('HF_TOKEN', 'test-free-token')

import media_providers as mp
import media_models as mm
import media_workflow as mw
import media_shorts as ms
import media_design as md
import media_fal as fal
import routes_media_suite as rms
from routes_media_suite import DesignIn
from PIL import Image


def _solid_png(w=200, h=200, color=(40, 60, 90)) -> bytes:
    b = io.BytesIO()
    Image.new('RGB', (w, h), color).save(b, 'PNG')
    return b.getvalue()


def _logo_png() -> bytes:
    b = io.BytesIO()
    Image.new('RGBA', (120, 120), (255, 0, 0, 255)).save(b, 'PNG')
    return b.getvalue()


class _FakeUpload:
    def __init__(self, data):
        self._d = data

    async def read(self):
        return self._d


class _OwnedColl:
    """Tiny Mongo-ish collection that filters find_one by query equality so
    ownership checks (user_id filter) are exercised even without a live DB."""
    def __init__(self, docs=None):
        self.docs = docs or []

    async def insert_one(self, d):
        self.docs.append(d)

    async def find_one(self, query, projection=None):
        for d in self.docs:
            if all(d.get(k) == v for k, v in query.items()):
                return d
        return None

    async def update_one(self, q, u):
        for d in self.docs:
            if all(d.get(k) == v for k, v in q.items()):
                d.update(u.get('$set', {}))



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


# ── Phase 1: Design Agent compositing (pure + route) ─────────────────────────
def test_compose_design_normal_ig_post():
    bg = _solid_png(400, 400)
    png, meta = md.compose_design(
        bg, title='Launch Day', subtitle='Join the movement', cta='Get Started',
        fmt='ig_post', primary_color='#0DC8B3',
    )
    assert isinstance(png, bytes) and png[:8] == b'\x89PNG\r\n\x1a\n'
    im = Image.open(io.BytesIO(png))
    assert im.size == (1080, 1080)
    assert meta['format'] == 'ig_post' and meta['width'] == 1080


def test_compose_design_long_title_no_overflow():
    bg = _solid_png(300, 300)
    long_title = 'This is an extremely long headline that should wrap safely and never overflow the canvas boundaries'
    png, meta = md.compose_design(bg, title=long_title, fmt='reel_cover')
    im = Image.open(io.BytesIO(png))
    assert im.size == (1080, 1920)


def test_compose_design_long_subtitle_and_cta():
    bg = _solid_png(300, 300, (10, 10, 10))
    png, _ = md.compose_design(
        bg, title='Summer Sale', subtitle=('Limited offer ' * 20), cta='Shop Now',
        fmt='poster',
    )
    assert Image.open(io.BytesIO(png)).size == (1080, 1620)


def test_compose_design_missing_optional_fields():
    bg = _solid_png(250, 250)
    png, meta = md.compose_design(bg, fmt='yt_thumb')  # no title/subtitle/cta/logo
    assert Image.open(io.BytesIO(png)).size == (1280, 720)
    assert meta['title'] == ''


def test_compose_design_with_logo():
    bg = _solid_png(250, 250)
    png, _ = md.compose_design(bg, title='Branded', logo=_logo_png(), fmt='ig_story')
    assert Image.open(io.BytesIO(png)).size == (1080, 1920)


def test_compose_design_invalid_format_raises():
    with pytest.raises(ValueError):
        md.compose_design(_solid_png(), fmt='not_a_format')


@pytest.mark.asyncio
async def test_design_compose_endpoint_stores_owned_asset(monkeypatch):
    coll = _OwnedColl()
    monkeypatch.setattr(rms, 'db', type('DB', (), {'media_designs': coll})())
    res = await rms.design_compose(
        fmt='ig_post', title='Big Idea', subtitle='sub', cta='Go',
        prompt='', model_id=None, primary_color='#ff0000', secondary_color='',
        background=_FakeUpload(_solid_png()), logo=_FakeUpload(b''), user={'id': 'u1'},
    )
    assert res['status'] == 'ok' and res['asset_id']
    assert res['width'] == 1080 and res['height'] == 1080
    assert res['image'].startswith('data:image/png;base64,')
    stored = coll.docs[0]
    assert stored['user_id'] == 'u1' and stored['fmt'] == 'ig_post'


@pytest.mark.asyncio
async def test_design_compose_generation_failure_is_safe(monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setattr(
        rms, 'generate_image_model',
        lambda p, m, w, h: __import__('asyncio').sleep(0, result={'error': 'hf down'}),
    )
    coll = _OwnedColl()
    monkeypatch.setattr(rms, 'db', type('DB', (), {'media_designs': coll})())
    with pytest.raises(HTTPException) as exc:
        await rms.design_compose(
            fmt='ig_post', title='x', prompt='cat', background=_FakeUpload(b''),
            logo=_FakeUpload(b''), user={'id': 'u1'},
        )
    assert exc.value.status_code == 502
    assert 'hf down' in exc.value.detail


@pytest.mark.asyncio
async def test_design_compose_invalid_format_is_400(monkeypatch):
    from fastapi import HTTPException
    coll = _OwnedColl()
    monkeypatch.setattr(rms, 'db', type('DB', (), {'media_designs': coll})())
    with pytest.raises(HTTPException) as exc:
        await rms.design_compose(
            fmt='bogus', title='x', background=_FakeUpload(_solid_png()),
            logo=_FakeUpload(b''), user={'id': 'u1'},
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_design_asset_enforces_ownership(monkeypatch):
    from fastapi import HTTPException
    from fastapi.responses import Response
    png = _solid_png(1080, 1080)
    doc = {'id': 'a1', 'user_id': 'owner', 'png': base64.b64encode(png).decode()}
    coll = _OwnedColl([doc])
    monkeypatch.setattr(rms, 'db', type('DB', (), {'media_designs': coll})())
    res = await rms.design_asset('a1', user={'id': 'owner'})
    assert isinstance(res, Response) and res.body[:8] == b'\x89PNG\r\n\x1a\n'
    with pytest.raises(HTTPException) as exc:
        await rms.design_asset('a1', user={'id': 'attacker'})
    assert exc.value.status_code == 404


# ── Phase 5: ownership on workflow/shorts status ──────────────────────────────
@pytest.mark.asyncio
async def test_workflow_status_enforces_ownership(monkeypatch):
    from fastapi import HTTPException
    doc = {'id': 'j1', 'user_id': 'u1', 'status': 'completed', 'outputs': {}}
    coll = _OwnedColl([doc])
    monkeypatch.setattr(rms, 'db', type('DB', (), {'media_workflows': coll})())
    ok = await rms.workflow_status('j1', user={'id': 'u1'})
    assert ok['id'] == 'j1'
    with pytest.raises(HTTPException) as exc:
        await rms.workflow_status('j1', user={'id': 'attacker'})
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_shorts_status_enforces_ownership(monkeypatch):
    from fastapi import HTTPException
    doc = {'id': 's1', 'user_id': 'u1', 'status': 'completed', 'result': {}}
    coll = _OwnedColl([doc])
    monkeypatch.setattr(rms, 'db', type('DB', (), {'media_shorts': coll})())
    ok = await rms.shorts_status('s1', user={'id': 'u1'})
    assert ok['id'] == 's1'
    with pytest.raises(HTTPException) as exc:
        await rms.shorts_status('s1', user={'id': 'attacker'})
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_shorts_file_enforces_ownership(monkeypatch, tmp_path):
    from fastapi import HTTPException
    from fastapi.responses import FileResponse
    vid = tmp_path / 'out.mp4'
    vid.write_bytes(b'fakevideo')
    doc = {'id': 's1', 'user_id': 'u1', 'result': {'output': str(vid)}}
    coll = _OwnedColl([doc])
    monkeypatch.setattr(rms, 'db', type('DB', (), {'media_shorts': coll})())
    res = await rms.shorts_file('s1', user={'id': 'u1'})
    assert isinstance(res, FileResponse)
    with pytest.raises(HTTPException) as exc:
        await rms.shorts_file('s1', user={'id': 'attacker'})
    assert exc.value.status_code == 404


# ── Phase 6: Fal.ai optional provider (never required, never leaks key) ──────
def test_fal_not_advertised_without_key(monkeypatch):
    monkeypatch.delenv('FAL_KEY', raising=False)
    assert fal.fal_image_models() == []
    models = mm.list_free_models()
    assert not any(m.get('provider') == 'fal.ai' for cap in models.values() for m in cap)


@pytest.mark.asyncio
async def test_fal_generation_safe_when_unconfigured(monkeypatch):
    monkeypatch.delenv('FAL_KEY', raising=False)
    res = await fal.generate_image_fal('a cat')
    assert 'error' in res  # graceful, never raises


@pytest.mark.asyncio
async def test_fal_model_delegation_unconfigured_is_safe(monkeypatch):
    monkeypatch.delenv('FAL_KEY', raising=False)
    res = await mm.generate_image_model('a cat', 'fal/flux-schnell', 64, 64)
    assert 'error' in res  # free suite continues; no crash


# ── Phase 8: workflow robustness ─────────────────────────────────────────────
def test_run_graph_unknown_node_type_raises():
    graph = {'nodes': [{'id': 'x', 'type': 'bogus', 'params': {}}], 'edges': []}

    async def _r():
        return await mw.run_graph(graph)

    import asyncio
    with pytest.raises(ValueError):
        asyncio.run(_r())


@pytest.mark.asyncio
async def test_workflow_run_rejects_unknown_node_type(monkeypatch):
    from fastapi import HTTPException
    coll = _OwnedColl()
    monkeypatch.setattr(rms, 'db', type('DB', (), {'media_workflows': coll})())
    with pytest.raises(HTTPException) as exc:
        await rms.workflow_run({'graph': {'nodes': [{'id': 'x', 'type': 'bogus'}], 'edges': []}}, None, user={'id': 'u1'})
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_workflow_worker_records_failure(monkeypatch):
    coll = _OwnedColl()
    monkeypatch.setattr(rms, 'db', type('DB', (), {'media_workflows': coll})())
    async def _boom(graph):
        raise ValueError('boom')
    monkeypatch.setattr(rms, 'run_graph', _boom)
    await coll.insert_one({'id': 'j2', 'status': 'queued'})
    await rms._workflow_worker('j2', {'nodes': [{'id': 'n', 'type': 'image', 'params': {}}], 'edges': []})
    assert coll.docs[0]['status'] == 'failed'
    assert 'boom' in coll.docs[0]['error']


# ── Phase 7: shorts output integrity (command integrity, audio preserved) ─────
def test_shorts_command_preserves_audio_and_9_16():
    cmd = ms.build_shorts_command('in.mp4', 'out.mp4', 'c.srt', '9:16')
    assert any('crop=720:1280' in c for c in cmd)
    assert '-c:a' in cmd and 'copy' in cmd
    assert any('subtitles=' in c for c in cmd)
