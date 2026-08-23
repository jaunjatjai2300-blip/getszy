"""Tests for the free media suite surface (SamurAIGPT / Open-Generative-AI)."""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:27017')
os.environ.setdefault('JWT_SECRET', 'test-only-media-suite-secret')
os.environ.setdefault('HF_TOKEN', 'test-free-token')

import media_providers as mp
import routes_media_suite as rms
from routes_media_suite import DesignIn


def test_media_provider_info_is_free_and_healthy():
    info = mp.media_provider_info()
    assert info['free_only'] is True
    assert info['healthy'] is True
    assert isinstance(info['usable'], list) and info['usable']
    for key, cap in info['providers'].items():
        assert cap['free'] is True
        assert cap['blocked_by_paid_policy'] is False


@pytest.mark.asyncio
async def test_providers_endpoint(monkeypatch):
    status = await rms.providers()
    assert status['free_only'] is True
    assert status['healthy'] is True


@pytest.mark.asyncio
async def test_skills_catalog_includes_core_media_tools():
    out = await rms.skills()
    names = {s['name'] for s in out['skills']}
    assert {'generate_image', 'text_to_speech', 'transcribe', 'create_shorts', 'run_workflow'} <= names
    assert out['free_only'] is True


@pytest.mark.asyncio
async def test_design_endpoint_uses_free_pipeline_and_stores_record(monkeypatch):
    # Avoid any network call and any real DB write.
    monkeypatch.setattr(
        rms, 'generate_image',
        lambda prompt, w, h: __import__('asyncio').sleep(0, result={'image': 'BASE64', 'provider': 'pollinations'})
    )

    class _Coll:
        def __init__(self):
            self.inserted = None

        async def insert_one(self, doc):
            self.inserted = doc
            return None

    coll = _Coll()
    monkeypatch.setattr(rms, 'db', type('DB', (), {'media_designs': coll})())

    result = await rms.design(DesignIn(prompt='a calm poster', kind='poster', aspect='4:5'), user={'id': 'u1'})
    assert result['image'] == 'BASE64'
    assert result['provider'] == 'pollinations'
    assert result['id']
    assert coll.inserted is not None
    assert coll.inserted['user_id'] == 'u1'
    assert coll.inserted['kind'] == 'poster'


@pytest.mark.asyncio
async def test_design_rejects_short_prompt():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        await rms.design(DesignIn(prompt='  '), user={'id': 'u1'})
    assert exc.value.status_code == 400
