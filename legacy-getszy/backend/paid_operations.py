"""Durable customer-paid operation records.

This module deliberately does not debit credits or invoke providers.  It gives every
customer intention one durable identity and a lease-controlled execution record;
credits remain controlled by the user-document marker in ``credits.py``.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid
from typing import Any, Optional

from pymongo.errors import DuplicateKeyError

from db import db


PENDING = 'PENDING'
RUNNING = 'RUNNING'
SUCCEEDED = 'SUCCEEDED'
FAILED_REFUNDED = 'FAILED_REFUNDED'
REJECTED_NO_CHARGE = 'REJECTED_NO_CHARGE'
TERMINAL_STATUSES = {SUCCEEDED, FAILED_REFUNDED, REJECTED_NO_CHARGE}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def lease_until(seconds: int = 120) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def customer_operation_view(operation: dict) -> dict:
    """Return a customer-safe operation view without provider/internal errors."""
    return {
        'operation_id': operation['operation_id'],
        'action_type': operation['action_type'],
        'status': operation['status'],
        'resource_id': operation.get('resource_id'),
        'credit_state': operation.get('credit_state', 'NOT_DEBITED'),
        'result_ref': operation.get('result_ref'),
        'failure_code': operation.get('failure_code'),
        'created_at': operation.get('created_at'),
        'updated_at': operation.get('updated_at'),
        'started_at': operation.get('started_at'),
        'completed_at': operation.get('completed_at'),
    }


async def create_or_reuse_operation(
    *, user_id: str, action_type: str, idempotency_key: str, payload: dict
) -> tuple[dict, bool]:
    """Create exactly one operation per user/action/key, or return its original."""
    key = (idempotency_key or '').strip()
    if not key or len(key) > 200:
        raise ValueError('A valid Idempotency-Key is required')
    created_at = now()
    operation = {
        'operation_id': str(uuid.uuid4()),
        'user_id': user_id,
        'action_type': action_type,
        'idempotency_key': key,
        'status': PENDING,
        'credit_state': 'NOT_DEBITED',
        'resource_id': None,
        'result_ref': None,
        'failure_code': None,
        'provider_attempts': [],
        'payload': payload,
        'lease_expires_at': None,
        'lease_owner': None,
        'created_at': created_at,
        'updated_at': created_at,
        'started_at': None,
        'completed_at': None,
    }
    try:
        await db.paid_operations.insert_one(operation)
        operation.pop('_id', None)
        return operation, True
    except DuplicateKeyError:
        existing = await db.paid_operations.find_one(
            {'user_id': user_id, 'action_type': action_type, 'idempotency_key': key},
            {'_id': 0},
        )
        if not existing:
            raise
        return existing, False


async def get_operation_for_user(operation_id: str, user_id: str) -> Optional[dict]:
    return await db.paid_operations.find_one(
        {'operation_id': operation_id, 'user_id': user_id}, {'_id': 0}
    )


async def get_operation_by_key_for_user(action_type: str, idempotency_key: str, user_id: str) -> Optional[dict]:
    return await db.paid_operations.find_one(
        {'action_type': action_type, 'idempotency_key': idempotency_key, 'user_id': user_id}, {'_id': 0}
    )


async def claim_execution(operation_id: str, worker_id: str) -> Optional[dict]:
    """Acquire a short renewable lease for a pending or abandoned operation.

    The conditional Mongo update—not a process-local lock—selects the sole worker.
    """
    current = now()
    return await db.paid_operations.find_one_and_update(
        {
            'operation_id': operation_id,
            'status': {'$in': [PENDING, RUNNING]},
            '$or': [
                {'status': PENDING},
                {'lease_expires_at': {'$lte': current}},
                {'lease_expires_at': None},
            ],
        },
        {
            '$set': {
                'status': RUNNING,
                'lease_owner': worker_id,
                'lease_expires_at': lease_until(),
                'started_at': current,
                'updated_at': current,
            },
        },
        return_document=True,
        projection={'_id': 0},
    )


async def update_operation(operation_id: str, values: dict) -> None:
    values = {**values, 'updated_at': now()}
    await db.paid_operations.update_one({'operation_id': operation_id}, {'$set': values})


async def append_provider_attempt(operation_id: str, attempt: dict) -> None:
    await db.paid_operations.update_one(
        {'operation_id': operation_id},
        {'$push': {'provider_attempts': attempt}, '$set': {'updated_at': now()}},
    )


async def list_recoverable_operation_ids(action_type: str, limit: int = 25) -> list[str]:
    cutoff = now()
    cursor = db.paid_operations.find(
        {
            'action_type': action_type,
            'status': {'$in': [PENDING, RUNNING]},
            '$or': [
                {'status': PENDING},
                {'lease_expires_at': {'$lte': cutoff}},
                {'lease_expires_at': None},
            ],
        },
        {'_id': 0, 'operation_id': 1},
    ).sort('created_at', 1).limit(limit)
    return [item['operation_id'] async for item in cursor]
