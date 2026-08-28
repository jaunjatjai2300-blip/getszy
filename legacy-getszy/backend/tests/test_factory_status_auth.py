"""/factory/status must be admin-only — it exposes internal resource/limit/ledger
internals that must not leak to customers. These tests hit the real app through
the existing auth contract (get_current_admin -> get_current_user); no second
auth mechanism is introduced. The dependency fails before the handler, so no DB
is required.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017/test")
os.environ.setdefault("JWT_SECRET", "review-only-secret-32-characters-long!!")

from fastapi.testclient import TestClient  # noqa: E402
from server import app  # noqa: E402

client = TestClient(app)


def test_factory_status_refuses_unauthenticated():
    r = client.get("/api/factory/status")
    assert r.status_code in (401, 403)          # not public any more


def test_factory_status_refuses_bad_token():
    r = client.get("/api/factory/status", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code in (401, 403)


def test_health_stays_public():
    # /health must remain reachable for Docker/uptime monitors — not gated.
    r = client.get("/api/health")
    assert r.status_code in (200, 503)          # ok, or honest 503 when DB is down — never 401/403
    assert r.status_code not in (401, 403)
