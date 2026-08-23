import os
import sys
import types

import pytest
from pymongo.errors import DuplicateKeyError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('JWT_SECRET', 'test-sprint-secret-with-at-least-32-bytes')
import paid_operations as operations


class PaidOperations:
    def __init__(self):
        self.rows = []

    async def insert_one(self, row):
        identity = (row['user_id'], row['action_type'], row['idempotency_key'])
        if any((item['user_id'], item['action_type'], item['idempotency_key']) == identity for item in self.rows):
            raise DuplicateKeyError('unique customer intention')
        self.rows.append(dict(row))
        return types.SimpleNamespace(inserted_id=len(self.rows))

    async def find_one(self, flt, projection=None):
        for row in self.rows:
            if all(row.get(key) == value for key, value in flt.items()):
                return dict(row)
        return None


class FakeDB:
    def __init__(self):
        self.paid_operations = PaidOperations()


@pytest.mark.asyncio
async def test_same_customer_action_key_reuses_one_authoritative_operation(monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr(operations, 'db', fake)
    first, created = await operations.create_or_reuse_operation(
        user_id='customer-a', action_type='builder_website', idempotency_key='intent-1', payload={'prompt': 'hello'},
    )
    second, reused = await operations.create_or_reuse_operation(
        user_id='customer-a', action_type='builder_website', idempotency_key='intent-1', payload={'prompt': 'ignored'},
    )
    assert created is True and reused is False
    assert first['operation_id'] == second['operation_id']
    assert len(fake.paid_operations.rows) == 1
    assert second['payload'] == {'prompt': 'hello'}


@pytest.mark.asyncio
async def test_operation_identity_is_scoped_to_user_and_action(monkeypatch):
    fake = FakeDB()
    monkeypatch.setattr(operations, 'db', fake)
    a, _ = await operations.create_or_reuse_operation(user_id='customer-a', action_type='builder_website', idempotency_key='same', payload={})
    b, _ = await operations.create_or_reuse_operation(user_id='customer-b', action_type='builder_website', idempotency_key='same', payload={})
    c, _ = await operations.create_or_reuse_operation(user_id='customer-a', action_type='builder_refine', idempotency_key='same', payload={})
    assert len({a['operation_id'], b['operation_id'], c['operation_id']}) == 3


def test_customer_view_excludes_payload_and_provider_errors():
    view = operations.customer_operation_view({
        'operation_id': 'op1', 'action_type': 'builder_website', 'status': operations.RUNNING,
        'credit_state': 'DEBITED', 'payload': {'secret': 'do-not-expose'},
        'provider_attempts': [{'provider_error': 'sensitive internal trace'}], 'created_at': 'now', 'updated_at': 'now',
    })
    assert view['operation_id'] == 'op1'
    assert 'payload' not in view and 'provider_attempts' not in view
