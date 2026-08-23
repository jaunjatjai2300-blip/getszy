import os
import sys
import types

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('JWT_SECRET', 'test-sprint-secret-with-at-least-32-bytes')
import routes_builder as builder


class ProjectCollection:
    def __init__(self, events):
        self.events = events
        self.rows = []

    async def update_one(self, flt, update, upsert=False):
        self.events.append(('project_upsert', flt, update, upsert))
        self.rows.append(update['$setOnInsert'])


class FakeDB:
    def __init__(self, events):
        self.builder_projects = ProjectCollection(events)


class Brief:
    def model_dump(self):
        return {'brand_name': 'Verified Brand'}


@pytest.mark.asyncio
async def test_operation_persists_project_before_succeeded_and_uses_operation_as_debit_ref(monkeypatch):
    events = []
    operation = {
        'operation_id': 'op-1', 'user_id': 'u1', 'status': 'PENDING',
        'credit_state': 'NOT_DEBITED', 'payload': {'prompt': 'Build a site', 'name': '', 'brief': {}},
        'resource_id': None,
    }
    monkeypatch.setattr(builder, 'db', FakeDB(events))
    monkeypatch.setattr(builder, 'claim_execution', lambda *args: _value(operation))
    monkeypatch.setattr(builder, 'deduct', lambda *args, **kwargs: _value((True, '', 45)))
    monkeypatch.setattr(builder, 'extract_brief_v3', lambda *args, **kwargs: _value(Brief()))
    monkeypatch.setattr(builder, 'composition_context', lambda *args: {'brand_name': 'Verified Brand'})
    monkeypatch.setattr(builder, 'compose_site_fast', lambda *args, **kwargs: _value('<!DOCTYPE html><html></html>'))
    monkeypatch.setattr(builder, 'evaluate_landing_page_quality', lambda *args: {'status': 'ready_for_human_review'})
    monkeypatch.setattr(builder, 'append_provider_attempt', lambda op, item: _event(events, 'attempt', item))
    monkeypatch.setattr(builder, 'update_operation', lambda op, item: _event(events, 'operation_update', item))

    await builder._run_website_operation('op-1')

    debit_event = next(item for item in events if item[0] == 'operation_update' and item[1].get('credit_state') == 'DEBITED')
    success_index = next(i for i, item in enumerate(events) if item[0] == 'operation_update' and item[1].get('status') == 'SUCCEEDED')
    project_index = next(i for i, item in enumerate(events) if item[0] == 'project_upsert')
    assert debit_event[1]['resource_id']
    assert project_index < success_index
    assert events[project_index][1]['user_id'] == 'u1'
    assert events[project_index][3] is True


@pytest.mark.asyncio
async def test_operation_failure_refunds_the_same_operation_reference(monkeypatch):
    events = []
    operation = {
        'operation_id': 'op-failure', 'user_id': 'u1', 'status': 'PENDING',
        'credit_state': 'NOT_DEBITED', 'payload': {'prompt': 'Build a site', 'name': '', 'brief': {}},
        'resource_id': None,
    }
    monkeypatch.setattr(builder, 'db', FakeDB(events))
    monkeypatch.setattr(builder, 'claim_execution', lambda *args: _value(operation))
    monkeypatch.setattr(builder, 'deduct', lambda *args, **kwargs: _value((True, '', 45)))
    monkeypatch.setattr(builder, 'extract_brief_v3', lambda *args, **kwargs: _value(Brief()))
    monkeypatch.setattr(builder, 'composition_context', lambda *args: {})

    async def fails(*args, **kwargs):
        raise RuntimeError('provider unavailable')

    monkeypatch.setattr(builder, 'compose_site_fast', fails)
    monkeypatch.setattr(builder, 'append_provider_attempt', lambda op, item: _event(events, 'attempt', item))
    monkeypatch.setattr(builder, 'update_operation', lambda op, item: _event(events, 'operation_update', item))
    monkeypatch.setattr(builder, 'refund', lambda user, action, **kwargs: _event(events, 'refund', {'user': user, 'action': action, **kwargs}))

    await builder._run_website_operation('op-failure')

    assert [item for item in events if item[0] == 'refund'] == [
        ('refund', {'user': 'u1', 'action': 'builder_website', 'reason': 'managed_composition_failed', 'ref_id': 'op-failure'})
    ]
    assert any(item[0] == 'operation_update' and item[1].get('status') == 'FAILED_REFUNDED' for item in events)


async def _value(value):
    return value


async def _event(events, kind, value):
    events.append((kind, value))
