import os
import sys
import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:27017')
os.environ.setdefault('JWT_SECRET', 'test-only-builder-control-contract-secret')

from models import BuilderEvidenceItem, BuilderEvidenceUpdateIn, BuilderReleaseReviewIn, BuilderVersionIn, BuilderProjectIn
import routes_builder as builder_routes
from routes_builder import router, create_project_operation


def test_builder_control_models_validate_customer_review_data():
    item = BuilderEvidenceItem(claim='Starting at ₹999', source='Approved catalog', status='approved')
    body = BuilderEvidenceUpdateIn(items=[item])

    assert body.items[0].claim == 'Starting at ₹999'
    assert BuilderVersionIn(label='Approved mobile revision').label == 'Approved mobile revision'
    assert BuilderReleaseReviewIn(confirm_evidence_review=True).confirm_evidence_review is True


class _ProjectCollection:
    def __init__(self):
        self.saved = []

    async def insert_one(self, document):
        self.saved.append(document)


class _BuilderDB:
    def __init__(self):
        self.builder_projects = _ProjectCollection()


def _fake_operation(operation_id='op-1'):
    return {
        'operation_id': operation_id, 'user_id': 'customer-test', 'action_type': 'builder_website',
        'status': 'PENDING', 'credit_state': 'NOT_DEBITED', 'resource_id': None,
        'result_ref': None, 'failure_code': None,
        'created_at': '2024-01-01T00:00:00+00:00', 'updated_at': '2024-01-01T00:00:00+00:00',
        'started_at': None, 'completed_at': None,
    }


@pytest.mark.asyncio
async def test_create_project_operation_returns_accepted_envelope(monkeypatch):
    captured = {}

    async def fake_create(*, user_id, action_type, idempotency_key, payload):
        captured.update({
            'user_id': user_id, 'action_type': action_type,
            'idempotency_key': idempotency_key, 'payload': payload,
        })
        return _fake_operation(), True

    monkeypatch.setattr(builder_routes, 'create_or_reuse_operation', fake_create)
    monkeypatch.setattr(builder_routes.asyncio, 'create_task', lambda coro: None)

    result = await create_project_operation(
        BuilderProjectIn(prompt='Build a beauty studio website', brief={'primary_goal': 'Book appointments', 'primary_cta': 'Book now'}),
        idempotency_key='key-1',
        user={'id': 'customer-test', 'role': 'customer'},
    )

    assert result['accepted'] is True
    assert result['reused'] is False
    assert result['operation']['operation_id'] == 'op-1'
    assert result['operation']['status'] == 'PENDING'
    assert captured['action_type'] == 'builder_website'
    assert captured['idempotency_key'] == 'key-1'
    assert captured['payload']['prompt'] == 'Build a beauty studio website'


@pytest.mark.asyncio
async def test_create_project_operation_reuses_same_idempotency_key(monkeypatch):
    async def fake_create(*, user_id, action_type, idempotency_key, payload):
        return _fake_operation(), True

    monkeypatch.setattr(builder_routes, 'create_or_reuse_operation', fake_create)
    monkeypatch.setattr(builder_routes.asyncio, 'create_task', lambda coro: None)
    body = BuilderProjectIn(prompt='Build a beauty studio website')

    r1 = await create_project_operation(body, idempotency_key='same-key', user={'id': 'customer-test', 'role': 'customer'})
    assert r1['reused'] is False

    async def fake_reuse(*, user_id, action_type, idempotency_key, payload):
        return _fake_operation(), False

    monkeypatch.setattr(builder_routes, 'create_or_reuse_operation', fake_reuse)
    r2 = await create_project_operation(body, idempotency_key='same-key', user={'id': 'customer-test', 'role': 'customer'})

    assert r2['reused'] is True
    assert r1['operation']['operation_id'] == r2['operation']['operation_id']


def test_builder_control_routes_are_registered_before_dynamic_project_route():
    paths = [route.path for route in router.routes]

    assert '/builder/projects/{pid}/controls' in paths
    assert '/builder/projects/{pid}/evidence' in paths
    assert '/builder/projects/{pid}/versions' in paths
    assert '/builder/projects/{pid}/release-review' in paths
    assert paths.index('/builder/projects/{pid}/controls') < paths.index('/builder/projects/{pid}')
