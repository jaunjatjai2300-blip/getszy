import os
import sys
import time
import pytest
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:27017')
os.environ.setdefault('JWT_SECRET', 'test-only-preview-security-secret')

import auth
import routes_builder as builder_routes


class _Projects:
    def __init__(self):
        self.items = {
            'project-a': {'id': 'project-a', 'user_id': 'user-a', 'html_content': '<!DOCTYPE html><h1>A</h1>'},
            'project-b': {'id': 'project-b', 'user_id': 'user-b', 'html_content': '<!DOCTYPE html><h1>B</h1>'},
        }

    async def find_one(self, query, projection=None):
        item = self.items.get(query.get('id'))
        if not item or any(item.get(key) != value for key, value in query.items()):
            return None
        return {key: value for key, value in item.items() if not projection or projection.get(key, 1)}


class _DB:
    def __init__(self):
        self.builder_projects = _Projects()


@pytest.fixture(autouse=True)
def isolated_builder_db(monkeypatch):
    monkeypatch.setattr(builder_routes, 'db', _DB())


@pytest.mark.asyncio
async def test_owner_can_issue_and_use_project_bound_preview_token():
    issued = await builder_routes.issue_preview_token('project-a', user={'id': 'user-a'})
    response = await builder_routes.preview_project('project-a', token=issued['token'])
    assert response.status_code == 200
    assert 'A</h1>' in response.body.decode()


@pytest.mark.asyncio
async def test_other_user_cannot_issue_preview_token():
    with pytest.raises(HTTPException) as exc:
        await builder_routes.issue_preview_token('project-b', user={'id': 'user-a'})
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_expired_and_cryptographically_tampered_preview_tokens_are_denied(monkeypatch):
    # Defend against any leaked jwt.decode patch from another test: pin the real verifier.
    monkeypatch.setattr(auth.jwt, 'decode', jwt.decode)
    expired = jwt.encode({
        'sub': 'user-a', 'project_id': 'project-a', 'type': 'builder_preview',
        'exp': int(time.time()) - 1000,
    }, auth.JWT_SECRET, algorithm=auth.JWT_ALG)
    with pytest.raises(HTTPException) as expired_error:
        await builder_routes.preview_project('project-a', token=expired)
    assert expired_error.value.status_code == 401

    valid = auth.create_preview_token('user-a', 'project-a')
    header, payload, signature = valid.split('.')
    replacement = 'A' if signature[-1] != 'A' else 'B'
    tampered = f'{header}.{payload}.{signature[:-1]}{replacement}'
    with pytest.raises(HTTPException) as tampered_error:
        await builder_routes.preview_project('project-a', token=tampered)
    assert tampered_error.value.status_code == 401


@pytest.mark.asyncio
async def test_missing_invalid_and_cross_project_tokens_are_denied():
    with pytest.raises(HTTPException) as missing:
        await builder_routes.preview_project('project-a')
    assert missing.value.status_code == 401

    with pytest.raises(HTTPException) as invalid:
        await builder_routes.preview_project('project-a', token='not-a-token')
    assert invalid.value.status_code == 401

    token = auth.create_preview_token('user-a', 'project-a')
    with pytest.raises(HTTPException) as substituted:
        await builder_routes.preview_project('project-b', token=token)
    assert substituted.value.status_code == 403


def test_preview_token_is_purpose_bound_and_short_lived(monkeypatch):
    token = auth.create_preview_token('user-a', 'project-a')
    assert auth.verify_preview_token(token, 'project-a') == 'user-a'

    ordinary = auth.generate_token if hasattr(auth, 'generate_token') else auth.create_token
    ordinary = auth.create_token('user-a', 'customer')
    with pytest.raises(HTTPException) as wrong_purpose:
        auth.verify_preview_token(ordinary, 'project-a')
    assert wrong_purpose.value.status_code == 403
