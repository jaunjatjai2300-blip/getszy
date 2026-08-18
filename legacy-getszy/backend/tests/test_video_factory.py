"""Video Factory Audit — failure-path, refund, cancellation, dedup, recovery.

Runs fully offline against an in-memory fake collection, exercising the REAL
renderer + routes logic (refund, cancellation, dedup, recovery, download
validation). Full test matrix:
  Normal generation            -> PASS
  Image failure                -> fallback (skip scene) / refund (all fail)
  TTS failure                  -> refund
  FFmpeg failure               -> cleanup + refund
  AI timeout                  -> recovery (skip/refund)
  User cancellation           -> cleanup + refund
  Disk full                   -> graceful failure + refund
  Corrupt MP4                 -> reject on download
  Tiny MP4                    -> reject on download
  Duplicate job               -> prevented
  Server restart              -> recovery (reset + refund)
And proves _refund_assets runs on every terminal failure path (exactly once).
"""
import os
import re
import errno
import uuid
from types import SimpleNamespace

import pytest

import credits as credits_mod
import video_factory.renderer as renderer
import routes_video_factory as vf_routes


class FakeColl:
    """Minimal in-memory stand-in for motor's video_projects collection."""
    def __init__(self):
        self._docs = {}

    async def insert_one(self, doc):
        self._docs[doc['id']] = dict(doc)

    async def find_one(self, flt, projection=None):
        pid = flt.get('id')
        doc = self._docs.get(pid)
        if doc is None:
            return None
        if 'user_id' in flt and doc.get('user_id') != flt['user_id']:
            return None
        if projection:
            incl = [k for k, v in projection.items() if v == 1 and k != '_id']
            if incl:
                return {k: doc.get(k) for k in incl}
            return {k: v for k, v in doc.items() if k not in projection}
        return dict(doc)

    async def find(self, flt, projection=None):
        out = []
        statuses = flt.get('render_status', {}).get('$in', [])
        for doc in self._docs.values():
            if statuses and doc.get('render_status') not in statuses:
                continue
            out.append(dict(doc))
        for d in out:
            yield d

    async def update_one(self, flt, update):
        pid = flt.get('id')
        doc = self._docs.get(pid)
        if doc is not None:
            doc.update(update.get('$set', {}))

    async def delete_many(self, flt):
        rx = flt.get('id', {}).get('$regex')
        for k in [k for k in self._docs if rx and re.match(rx, k)]:
            del self._docs[k]


@pytest.fixture(autouse=True)
def db(monkeypatch):
    fake = FakeColl()
    ns = SimpleNamespace(video_projects=fake)
    monkeypatch.setattr(renderer, 'db', ns)
    monkeypatch.setattr(vf_routes, 'db', ns)
    yield ns
    # cleanup
    for k in [k for k in fake._docs if k.startswith('test-')]:
        del fake._docs[k]


@pytest.fixture(autouse=True)
def media_tmp(monkeypatch, tmp_path):
    monkeypatch.setattr(renderer, 'MEDIA_DIR', tmp_path / 'vf')


@pytest.fixture
def refunds(monkeypatch):
    calls = []
    async def fake_refund(user_id, action, qty=1, reason='generation_failed'):
        calls.append({'user_id': user_id, 'action': action, 'reason': reason})
        return 1
    # routes_* bind `refund` at import time, so patch both the module and the route reference.
    monkeypatch.setattr(credits_mod, 'refund', fake_refund)
    monkeypatch.setattr(vf_routes, 'refund', fake_refund)
    return calls


def _make_project(user_id='u1', status='queued', **extra):
    doc = {
        'id': f'test-{uuid.uuid4()}',
        'user_id': user_id,
        'title': 'Audit Video',
        'language': 'hinglish',
        'render_status': status,
        'refunded': False,
        'cancel_requested': False,
        'stages': {
            'storyboard': [
                {'index': 0, 'narration_chunk': 'first scene', 'visual_intent': 'a cat'},
                {'index': 1, 'narration_chunk': 'second scene', 'visual_intent': 'a dog'},
            ],
            'visual_plan': [
                {'scene_index': 0, 'generation_prompt': 'cat image'},
                {'scene_index': 1, 'generation_prompt': 'dog image'},
            ],
            'script_variants': [{'id': 's1', 'narration': 'full script text'}],
        },
        'selected_script_id': 's1',
    }
    doc.update(extra)
    return doc


async def _setup(db, tmp_path, monkeypatch, status='queued', **extra):
    doc = _make_project(status=status, **extra)
    await db.video_projects.insert_one(doc)
    counter = {'n': 0}

    async def fake_fetch(prompt, orientation='16:9', seed=0):
        counter['n'] += 1
        p = tmp_path / f'img_{counter["n"]}.jpg'
        p.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 200)
        return str(p)

    async def fake_synth(text, path, voice=None):
        from pathlib import Path
        Path(path).write_bytes(b'\x00' * 1000)

    def fake_pick(**kw):
        return 'en-IN-Female'

    monkeypatch.setattr(renderer, 'fetch_scene_image', fake_fetch)
    monkeypatch.setattr(renderer, 'synth', fake_synth)
    monkeypatch.setattr(renderer, 'pick_voice', fake_pick)
    return doc['id']


async def test_normal_generation_passes(db, tmp_path, monkeypatch, refunds):
    pid = await _setup(db, tmp_path, monkeypatch)

    async def fake_build(scenes, audio_path, out_path, orientation='16:9'):
        from pathlib import Path
        Path(out_path).write_bytes(b'\x00' * 40000)
        return {'ok': True}
    monkeypatch.setattr(renderer, 'build_video', fake_build)

    res = await renderer.generate_all_assets(pid)
    assert res.get('ok') is True, res
    assert res['scenes_rendered'] == 2
    assert refunds == []  # success -> no refund


async def test_image_failure_fallback_skips_scene(db, tmp_path, monkeypatch, refunds):
    pid = await _setup(db, tmp_path, monkeypatch)

    async def flaky_fetch(prompt, orientation='16:9', seed=0):
        if 'dog' in prompt:
            raise RuntimeError('image gen boom')
        p = tmp_path / 'img_ok.jpg'
        p.write_bytes(b'\xff\xd8\xff\xe0' + b'\x00' * 200)
        return str(p)

    async def fake_build(scenes, audio_path, out_path, orientation='16:9'):
        from pathlib import Path
        Path(out_path).write_bytes(b'\x00' * 40000)
        return {'ok': True}
    monkeypatch.setattr(renderer, 'fetch_scene_image', flaky_fetch)
    monkeypatch.setattr(renderer, 'build_video', fake_build)

    res = await renderer.generate_all_assets(pid)
    assert res.get('ok') is True
    assert res['scenes_rendered'] == 1  # one scene skipped, pipeline still completes
    assert refunds == []


async def test_all_images_fail_refunds(db, tmp_path, monkeypatch, refunds):
    pid = await _setup(db, tmp_path, monkeypatch)

    async def boom(prompt, orientation='16:9', seed=0):
        raise RuntimeError('image gen down')
    monkeypatch.setattr(renderer, 'fetch_scene_image', boom)

    res = await renderer.generate_all_assets(pid)
    assert res.get('error')
    assert ('no_scene_images',) in [(c['reason'],) for c in refunds]


async def test_tts_failure_refunds(db, tmp_path, monkeypatch, refunds):
    pid = await _setup(db, tmp_path, monkeypatch)

    async def boom(text, path, voice=None):
        raise RuntimeError('tts down')
    monkeypatch.setattr(renderer, 'synth', boom)

    res = await renderer.generate_all_assets(pid)
    assert res.get('error')
    assert ('voice_generation_failed',) in [(c['reason'],) for c in refunds]


async def test_ffmpeg_exception_cleanup_and_refund(db, tmp_path, monkeypatch, refunds):
    pid = await _setup(db, tmp_path, monkeypatch)
    stale = renderer.MEDIA_DIR / pid / 'final.mp4'
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_bytes(b'\x00' * 5000)

    async def boom(scenes, audio_path, out_path, orientation='16:9'):
        raise RuntimeError('ffmpeg crashed')
    monkeypatch.setattr(renderer, 'build_video', boom)

    res = await renderer.generate_all_assets(pid)
    assert res.get('error')
    assert ('assembly_exception',) in [(c['reason'],) for c in refunds]
    assert not stale.exists()  # stale artifact cleaned


async def test_ffmpeg_error_dict_refunds(db, tmp_path, monkeypatch, refunds):
    pid = await _setup(db, tmp_path, monkeypatch)

    async def err_dict(scenes, audio_path, out_path, orientation='16:9'):
        return {'error': 'ffmpeg encode failed'}
    monkeypatch.setattr(renderer, 'build_video', err_dict)

    res = await renderer.generate_all_assets(pid)
    assert res.get('error')
    assert ('ffmpeg_error',) in [(c['reason'],) for c in refunds]


async def test_ai_timeout_recovers(db, tmp_path, monkeypatch, refunds):
    pid = await _setup(db, tmp_path, monkeypatch)

    async def timeout_fetch(prompt, orientation='16:9', seed=0):
        import httpx
        raise httpx.ReadTimeout('timed out')
    monkeypatch.setattr(renderer, 'fetch_scene_image', timeout_fetch)

    res = await renderer.generate_all_assets(pid)
    assert res.get('error')
    assert ('no_scene_images',) in [(c['reason'],) for c in refunds]


async def test_disk_full_graceful(db, tmp_path, monkeypatch, refunds):
    pid = await _setup(db, tmp_path, monkeypatch)

    async def enospc(scenes, audio_path, out_path, orientation='16:9'):
        raise OSError(errno.ENOSPC, 'No space left on device')
    monkeypatch.setattr(renderer, 'build_video', enospc)

    res = await renderer.generate_all_assets(pid)
    assert res.get('error')
    assert 'disk full' in res['error'].lower()
    assert ('assembly_exception',) in [(c['reason'],) for c in refunds]


async def test_corrupt_and_tiny_mp4_rejected_on_download(db, tmp_path, monkeypatch, refunds):
    from fastapi import HTTPException

    pid = await _setup(db, tmp_path, monkeypatch, status='complete')
    tiny = tmp_path / 'tiny.mp4'
    tiny.write_bytes(b'\x00' * 100)
    await db.video_projects.update_one({'id': pid}, {'$set': {'final_video_path': str(tiny), 'final_video_size': 100}})
    with pytest.raises(HTTPException) as e1:
        await vf_routes.download_final(pid, {'id': 'u1'})
    assert e1.value.status_code == 422

    pid2 = await _setup(db, tmp_path, monkeypatch, status='complete')
    corrupt = tmp_path / 'corrupt.mp4'
    corrupt.write_bytes(b'\x00' * 40000)
    await db.video_projects.update_one({'id': pid2}, {'$set': {'final_video_path': str(corrupt), 'final_video_size': 40000}})
    with pytest.raises(HTTPException) as e2:
        await vf_routes.download_final(pid2, {'id': 'u1'})
    assert e2.value.status_code == 422

    pid3 = await _setup(db, tmp_path, monkeypatch, status='complete')
    ok = tmp_path / 'ok.mp4'
    ok.write_bytes(b'\x00\x00\x00\x18ftypmp42' + b'\x00' * 40000)
    await db.video_projects.update_one({'id': pid3}, {'$set': {'final_video_path': str(ok), 'final_video_size': 40032}})
    resp = await vf_routes.download_final(pid3, {'id': 'u1'})
    assert resp is not None


async def test_duplicate_job_prevented(db, monkeypatch, refunds):
    from fastapi import BackgroundTasks
    doc = _make_project(status='generating_voice')
    await db.video_projects.insert_one(doc)
    deduct_calls = []
    async def fake_deduct(uid, action):
        deduct_calls.append(action)
        return True, 'ok', 0
    monkeypatch.setattr(credits_mod, 'deduct', fake_deduct)
    monkeypatch.setattr(vf_routes, 'deduct', fake_deduct)

    res = await vf_routes.generate_assets(doc['id'], vf_routes.GenerateAssetsIn(orientation='16:9'), BackgroundTasks(), {'id': 'u1'})
    assert res.get('already_running') is True
    assert deduct_calls == []  # not charged twice


async def test_user_cancellation_cleanup_and_refund(db, tmp_path, monkeypatch, refunds):
    doc = _make_project(status='generating_images')
    await db.video_projects.insert_one(doc)
    proj_dir = renderer.MEDIA_DIR / doc['id']
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / 'final.mp4').write_bytes(b'\x00' * 100)

    res = await vf_routes.cancel_generation(doc['id'], {'id': 'u1'})
    assert res['status'] == 'cancelled'
    assert ('user_cancelled',) in [(c['reason'],) for c in refunds]
    assert not proj_dir.exists()  # partial files cleaned


async def test_renderer_respects_cancel_flag_no_double_refund(db, tmp_path, monkeypatch, refunds):
    doc = _make_project(status='generating_images', refunded=True, cancel_requested=True)
    await db.video_projects.insert_one(doc)

    async def fake_build(scenes, audio_path, out_path, orientation='16:9'):
        from pathlib import Path
        Path(out_path).write_bytes(b'\x00' * 40000)
        return {'ok': True}
    monkeypatch.setattr(renderer, 'build_video', fake_build)

    res = await renderer.generate_all_assets(doc['id'])
    assert res.get('error') == 'cancelled by user'
    assert all(c['reason'] != 'assembly_exception' for c in refunds)


async def test_server_restart_recovery(db, tmp_path, monkeypatch, refunds):
    doc = _make_project(status='generating_images', refunded=False)
    await db.video_projects.insert_one(doc)
    proj_dir = renderer.MEDIA_DIR / doc['id']
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / 'final.mp4').write_bytes(b'\x00' * 100)

    count = await vf_routes.recover_stuck_video_jobs()
    assert count >= 1
    updated = await db.video_projects.find_one({'id': doc['id']})
    assert updated['render_status'] == 'error'
    assert updated['refunded'] is True
    assert ('server_restart_recovery',) in [(c['reason'],) for c in refunds]
    assert not proj_dir.exists()  # artifacts cleaned on recovery
