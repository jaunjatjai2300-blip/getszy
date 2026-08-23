import json
import os
import sys
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')
os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('INTEGRATION_ENCRYPTION_KEY', 'test-integration-secret')


class FakeCollection:
    def __init__(self):
        self.docs = []

    async def update_one(self, flt, update, upsert=False):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in flt.items()):
                doc.update(update.get('$set', {}))
                for key in update.get('$unset', {}):
                    doc.pop(key, None)
                return SimpleNamespace(upserted_id=None)
        if upsert:
            doc = dict(update.get('$set', {}))
            self.docs.append(doc)
        return SimpleNamespace(upserted_id=None)

    async def delete_one(self, flt):
        for index, doc in enumerate(self.docs):
            if all(doc.get(key) == value for key, value in flt.items()):
                self.docs.pop(index)
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)


class FakeDB:
    def __init__(self):
        self.user_integrations = FakeCollection()


@pytest.fixture
def integrations_db(monkeypatch):
    import routes_integrations

    database = FakeDB()
    monkeypatch.setattr(routes_integrations, 'db', database)
    return routes_integrations, database, {'id': 'u1'}


def test_api_credentials_encrypt_with_dedicated_fernet_key(integrations_db):
    routes_integrations, _, _ = integrations_db

    encrypted = routes_integrations._encrypt_credentials({'token': 'do-not-store-this-plaintext'})

    assert encrypted != 'do-not-store-this-plaintext'
    decrypted = routes_integrations._credential_cipher().decrypt(encrypted.encode())
    assert json.loads(decrypted) == {'token': 'do-not-store-this-plaintext'}


@pytest.mark.asyncio
async def test_beta_gate_does_not_falsely_mark_oauth_connected(integrations_db):
    routes_integrations, database, user = integrations_db

    with pytest.raises(HTTPException) as exc:
        await routes_integrations.connect_integration(
            routes_integrations.ConnectIn(integration_id='gmail'),
            user=user,
        )

    assert exc.value.status_code == 503
    assert database.user_integrations.docs == []


@pytest.mark.asyncio
async def test_disconnect_accepts_json_body_and_is_user_scoped(integrations_db):
    routes_integrations, database, user = integrations_db
    database.user_integrations.docs.append({
        'user_id': 'u1',
        'integration_id': 'razorpay',
        'status': 'configured',
    })

    result = await routes_integrations.disconnect_integration(
        routes_integrations.DisconnectIn(integration_id='razorpay'),
        user=user,
    )

    assert result == {'ok': True, 'status': 'disconnected'}
    assert database.user_integrations.docs == []


@pytest.mark.asyncio
async def test_disconnect_does_not_delete_another_users_connection(integrations_db):
    routes_integrations, database, user = integrations_db
    database.user_integrations.docs.append({
        'user_id': 'other-user',
        'integration_id': 'razorpay',
        'status': 'configured',
    })

    with pytest.raises(HTTPException) as exc:
        await routes_integrations.disconnect_integration(
            routes_integrations.DisconnectIn(integration_id='razorpay'),
            user=user,
        )

    assert exc.value.status_code == 404
    assert len(database.user_integrations.docs) == 1
