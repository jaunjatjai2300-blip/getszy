import asyncio
import os
import sys
import types

import pytest
from pymongo.errors import DuplicateKeyError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('JWT_SECRET', 'test-credit-marker-secret')
import credits as credits_mod


class CreditTransactions:
    """Minimal stateful projection collection with the required unique-ref behavior."""

    def __init__(self):
        self.rows = []

    async def find_one(self, flt, projection=None):
        for row in self.rows:
            if all(row.get(key) == value for key, value in flt.items()):
                return dict(row)
        return None

    async def insert_one(self, row):
        ref_id = row.get('ref_id')
        if ref_id and any(
            existing.get('user_id') == row.get('user_id')
            and existing.get('type') == row.get('type')
            and existing.get('ref_id') == ref_id
            for existing in self.rows
        ):
            raise DuplicateKeyError('duplicate operation ledger reference')
        saved = dict(row)
        saved['_id'] = len(self.rows) + 1
        self.rows.append(saved)
        return types.SimpleNamespace(inserted_id=saved['_id'])

    async def update_one(self, flt, update):
        for row in self.rows:
            if all(row.get(key) == value for key, value in flt.items()):
                row.update(update.get('$set', {}))
                return types.SimpleNamespace(modified_count=1)
        return types.SimpleNamespace(modified_count=0)


class Users:
    """Models only the Mongo filters and updates used by the credit layer.

    `marker_read_barrier` creates a same-ref pre-read race. There is deliberately
    no Python lock around `find_one_and_update`: it models Mongo's single-document
    atomic command, whose filter decides the only debit winner.
    """

    def __init__(self, credits=50):
        self.doc = {
            'id': 'u1', 'credits': credits, 'role': 'customer',
            'paid_debit_markers': [],
        }
        self.marker_read_barrier = None
        self.marker_read_count = 0

    async def find_one(self, flt, projection=None):
        if flt.get('id') != 'u1':
            return None
        ref_id = flt.get('paid_debit_markers.ref_id')
        if ref_id and self.marker_read_barrier is not None:
            self.marker_read_count += 1
            if self.marker_read_count == 2:
                self.marker_read_barrier.set()
            await self.marker_read_barrier.wait()
        if ref_id and not any(marker['ref_id'] == ref_id for marker in self.doc['paid_debit_markers']):
            return None
        return {
            **self.doc,
            'paid_debit_markers': [dict(marker) for marker in self.doc['paid_debit_markers']],
        }

    async def find_one_and_update(self, flt, update, return_document=False, projection=None):
        if flt.get('id') != 'u1':
            return None
        minimum = flt.get('credits', {}).get('$gte')
        if minimum is not None and self.doc['credits'] < minimum:
            return None
        ref_id = update.get('$push', {}).get('paid_debit_markers', {}).get('ref_id')
        marker_filter = flt.get('paid_debit_markers', {})
        if ref_id and '$not' in marker_filter:
            if any(marker['ref_id'] == ref_id for marker in self.doc['paid_debit_markers']):
                return None
        self.doc['credits'] += update.get('$inc', {}).get('credits', 0)
        if ref_id:
            self.doc['paid_debit_markers'].append(dict(update['$push']['paid_debit_markers']))
        return {
            **self.doc,
            'paid_debit_markers': [dict(marker) for marker in self.doc['paid_debit_markers']],
        }

    async def update_one(self, flt, update):
        ref_id = flt.get('paid_debit_markers.ref_id')
        if ref_id:
            for marker in self.doc['paid_debit_markers']:
                if marker['ref_id'] == ref_id:
                    if 'paid_debit_markers.$.ledger_state' in update.get('$set', {}):
                        marker['ledger_state'] = update['$set']['paid_debit_markers.$.ledger_state']
                    return types.SimpleNamespace(modified_count=1)
            return types.SimpleNamespace(modified_count=0)
        return types.SimpleNamespace(modified_count=1)


class FakeDB:
    def __init__(self, credits=50):
        self.users = Users(credits)
        self.credit_transactions = CreditTransactions()


@pytest.fixture
def db(monkeypatch):
    fake = FakeDB(50)
    monkeypatch.setattr(credits_mod, 'db', fake)
    return fake


def spend_rows(db, ref_id=None):
    rows = [row for row in db.credit_transactions.rows if row['type'] == 'spend']
    return [row for row in rows if ref_id is None or row.get('ref_id') == ref_id]


def refund_rows(db, ref_id=None):
    rows = [row for row in db.credit_transactions.rows if row['type'] == 'refund']
    return [row for row in rows if ref_id is None or row.get('ref_id') == ref_id]


@pytest.mark.asyncio
async def test_crash_after_atomic_marker_then_repeated_recovery_is_exactly_once(db, monkeypatch):
    """The process fails after atomic user update but before ledger projection."""
    original_reconcile = credits_mod.reconcile_operation_debit_ledger

    async def simulated_process_failure(*args, **kwargs):
        raise RuntimeError('simulated process failure after atomic debit marker write')

    monkeypatch.setattr(credits_mod, 'reconcile_operation_debit_ledger', simulated_process_failure)
    with pytest.raises(RuntimeError, match='simulated process failure'):
        await credits_mod.deduct('u1', 'builder_website', ref_id='crash-op')

    assert db.users.doc['credits'] == 45
    assert len(db.users.doc['paid_debit_markers']) == 1
    marker = db.users.doc['paid_debit_markers'][0]
    assert marker['ref_id'] == 'crash-op'
    assert marker['action'] == 'builder_website'
    assert marker['amount'] == 5
    assert marker['ledger_state'] == 'PENDING'
    assert spend_rows(db, 'crash-op') == []

    monkeypatch.setattr(credits_mod, 'reconcile_operation_debit_ledger', original_reconcile)
    for _ in range(3):
        await credits_mod.reconcile_operation_debit_ledger('u1', 'builder_website', 1, 'crash-op')

    assert db.users.doc['credits'] == 45
    assert db.users.doc['paid_debit_markers'][0]['ledger_state'] == 'WRITTEN'
    assert len(spend_rows(db, 'crash-op')) == 1

    # Customer retry reattaches to the durable marker and cannot charge a second time.
    assert await credits_mod.deduct('u1', 'builder_website', ref_id='crash-op') == (True, '', 45)
    assert len(db.users.doc['paid_debit_markers']) == 1
    assert len(spend_rows(db, 'crash-op')) == 1


@pytest.mark.asyncio
async def test_concurrent_same_reference_has_one_debit_marker_and_spend(db):
    db.users.marker_read_barrier = asyncio.Event()
    outcomes = await asyncio.gather(*[
        credits_mod.deduct('u1', 'builder_website', ref_id='same-operation')
        for _ in range(8)
    ])

    assert db.users.marker_read_count >= 2
    assert all(outcome == (True, '', 45) for outcome in outcomes)
    assert db.users.doc['credits'] == 45
    assert [marker['ref_id'] for marker in db.users.doc['paid_debit_markers']] == ['same-operation']
    assert len(spend_rows(db, 'same-operation')) == 1


@pytest.mark.asyncio
async def test_different_references_insufficient_credit_and_legacy_callers(db, monkeypatch):
    assert await credits_mod.deduct('u1', 'builder_website', ref_id='operation-a') == (True, '', 45)
    assert await credits_mod.deduct('u1', 'builder_website', ref_id='operation-b') == (True, '', 40)
    assert {marker['ref_id'] for marker in db.users.doc['paid_debit_markers']} == {'operation-a', 'operation-b'}
    assert len(spend_rows(db)) == 2

    before_legacy_balance = db.users.doc['credits']
    assert await credits_mod.deduct('u1', 'script') == (True, '', before_legacy_balance - 1)
    assert len(db.users.doc['paid_debit_markers']) == 2
    assert len(spend_rows(db)) == 3

    poor = FakeDB(0)
    monkeypatch.setattr(credits_mod, 'db', poor)
    result = await credits_mod.deduct('u1', 'builder_website', ref_id='no-funds')
    assert result[0] is False and result[2] == 0
    assert poor.users.doc['credits'] == 0
    assert poor.users.doc['paid_debit_markers'] == []
    assert spend_rows(poor) == []


@pytest.mark.asyncio
async def test_terminal_failure_refund_is_exactly_once_after_operation_debit(db):
    assert await credits_mod.deduct('u1', 'builder_website', ref_id='failed-op') == (True, '', 45)

    refunds = [
        await credits_mod.refund('u1', 'builder_website', ref_id='failed-op')
        for _ in range(3)
    ]

    assert refunds == [50, 50, 50]
    assert db.users.doc['credits'] == 50
    assert len(spend_rows(db, 'failed-op')) == 1
    assert len(refund_rows(db, 'failed-op')) == 1
