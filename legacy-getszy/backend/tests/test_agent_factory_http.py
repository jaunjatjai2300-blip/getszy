"""Internal HTTP surface: the security properties, not the happy path.

What matters here is what the surface REFUSES. A customer must not reach it, a
disabled deployment must not reveal it, and no route may hand out a privilege the
Python runtime would not.

The app is built from the real router so the real dependencies run; only the
database and the agent runtime are substituted, because these tests are about
authorisation and refusal rather than about Mongo or the model.
"""
import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("JWT_SECRET", "test-only-agent-http-secret-32-chars!!!")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import routes_agent_factory as rf  # noqa: E402
from agent_guard import APPROVAL_REQUIRED  # noqa: E402
from auth import get_current_admin, get_current_user  # noqa: E402

ADMIN = {"id": "admin-1", "role": "admin", "email": "admin@getszy.com"}
CUSTOMER = {"id": "cust-1", "role": "customer", "email": "c@example.com"}


def build(enabled=True, admin=ADMIN, grantable=""):
    os.environ["AGENT_FACTORY_HTTP_ENABLED"] = "true" if enabled else "false"
    os.environ["AGENT_FACTORY_GRANTABLE_APPROVALS"] = grantable
    app = FastAPI()
    app.include_router(rf.router, prefix="/api")

    if admin is not None:
        # Exercise the REAL admin check by feeding it the user it inspects.
        app.dependency_overrides[get_current_user] = lambda: admin
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clean_env():
    yield
    for key in ("AGENT_FACTORY_HTTP_ENABLED", "AGENT_FACTORY_GRANTABLE_APPROVALS"):
        os.environ.pop(key, None)


# ── the surface is off unless a deployment turns it on ───────────────────────

def test_disabled_deployment_returns_404_not_403():
    """A disabled internal surface must not confirm that it exists."""
    c = build(enabled=False)
    for path in ["/api/internal/agent-factory/health",
                 "/api/internal/agent-factory/agents",
                 "/api/internal/agent-factory/tasks"]:
        r = c.get(path)
        assert r.status_code == 404, path


def test_disabled_deployment_refuses_task_submission():
    c = build(enabled=False)
    r = c.post("/api/internal/agent-factory/tasks", json={"request": "do some work"})
    assert r.status_code == 404


# ── customers can never reach it ─────────────────────────────────────────────

def test_a_customer_is_refused_even_when_enabled():
    c = build(enabled=True, admin=CUSTOMER)
    r = c.get("/api/internal/agent-factory/health")
    assert r.status_code == 403


def test_a_customer_cannot_create_an_agent():
    c = build(enabled=True, admin=CUSTOMER)
    r = c.post("/api/internal/agent-factory/agents",
               json={"description": "senior backend python engineer for api work"})
    assert r.status_code == 403


def test_every_route_depends_on_the_admin_check():
    """A route added later without the guard would be an unauthenticated hole."""
    for route in rf.router.routes:
        names = [d.call.__name__ for d in route.dependant.dependencies]
        assert "guard_enabled" in names, f"{route.path} is missing guard_enabled"


# ── approvals cannot be granted by an HTTP body alone ────────────────────────

def test_approval_is_refused_when_the_deployment_grants_nothing():
    c = build(enabled=True, grantable="")
    r = c.post("/api/internal/agent-factory/tasks",
               json={"request": "push the branch", "approvals": ["git_push"]})
    assert r.status_code == 403
    assert "AGENT_FACTORY_GRANTABLE_APPROVALS" in r.json()["detail"]


def test_unknown_approval_names_are_rejected():
    c = build(enabled=True, grantable="git_push")
    r = c.post("/api/internal/agent-factory/tasks",
               json={"request": "do the thing", "approvals": ["sudo_everything"]})
    assert r.status_code == 400
    assert "Unknown approvals" in r.json()["detail"]


def test_grantable_set_can_never_exceed_the_real_approval_list():
    os.environ["AGENT_FACTORY_GRANTABLE_APPROVALS"] = "git_push,not_a_real_gate,deploy"
    assert rf._grantable() == {"git_push", "deploy"}
    assert rf._grantable() <= APPROVAL_REQUIRED


def test_default_deployment_grants_no_approvals():
    os.environ.pop("AGENT_FACTORY_GRANTABLE_APPROVALS", None)
    assert rf._grantable() == set()


# ── capability is reported honestly ──────────────────────────────────────────

def test_task_submission_refused_when_the_sandbox_is_not_configured(monkeypatch):
    """Accepting work that would fail on every tool call is not acceptable."""
    monkeypatch.setattr(rf, "REPO_ROOT_VALID", False)
    c = build(enabled=True)
    r = c.post("/api/internal/agent-factory/tasks", json={"request": "make a change"})
    assert r.status_code == 503
    assert "fails closed" in r.json()["detail"] or "failing closed" in r.json()["detail"]


def test_health_reports_sandbox_and_model_state(monkeypatch):
    monkeypatch.setattr(rf.agent_llm, "installed_models", lambda: ["qwen2.5-coder:7b"])
    c = build(enabled=True)
    body = c.get("/api/internal/agent-factory/health").json()
    assert body["enabled"] is True
    assert "sandbox_ready" in body
    assert body["installed_models"] == ["qwen2.5-coder:7b"]
    assert body["models_by_tier"]["strong"] == "qwen2.5-coder:7b"
    assert body["grantable_approvals"] == []
    assert body["max_repair_attempts"] == 3


def test_task_refused_when_no_local_model_is_installed(monkeypatch):
    """Internal work must not silently fall back to a customer provider."""
    monkeypatch.setattr(rf.agent_llm, "model_for_tier", lambda *a, **k: None)
    monkeypatch.setattr(rf.agent_llm, "installed_models", lambda: [])
    c = build(enabled=True)
    r = c.post("/api/internal/agent-factory/tasks", json={"request": "make a change"})
    assert r.status_code == 503
    assert "customer providers" in r.json()["detail"]


# ── responses never leak reasoning or another admin's work ───────────────────

def test_task_view_exposes_evidence_but_not_reasoning():
    record = {
        "operation_id": "op-1", "status": "SUCCEEDED",
        "payload": {"request": "r", "agent_id": "master"},
        "evidence": {"tools_used": ["read_file"]},
        "credit_state": "NOT_DEBITED",
        "lease_owner": "worker-A", "provider_attempts": [{"prompt": "secret reasoning"}],
    }
    view = rf._public_task(record)
    assert view["evidence"] == {"tools_used": ["read_file"]}
    assert "provider_attempts" not in view
    assert "lease_owner" not in view


def test_agent_view_does_not_expose_the_system_prompt_in_lists():
    cfg = {"id": "a1", "name": "n", "system_prompt": "internal instructions",
           "allowed_tools": ["read_file"], "granted_approvals": []}
    assert "system_prompt" not in rf._public_agent(cfg)


# ── the router is actually registered ────────────────────────────────────────

def test_router_is_wired_into_the_application_registry():
    registry = importlib.import_module("app.router_registry")
    modules = [m for _, m, _ in registry.INTERNAL_ROUTERS]
    assert "routes_agent_factory" in modules
    # Mount it the way server.py does, then read the OpenAPI paths. This FastAPI
    # version defers inclusion behind opaque _IncludedRouter objects, so walking
    # .routes finds nothing; generating the schema forces real resolution and
    # reflects what is actually served.
    app = FastAPI()
    app.include_router(registry.load_all_routers(), prefix="/api")
    paths = set(app.openapi()["paths"])
    served = sorted(p for p in paths if "agent-factory" in p)
    assert served, "the internal router is not reachable in the assembled app"
    for expected in ["/api/internal/agent-factory/health",
                     "/api/internal/agent-factory/agents",
                     "/api/internal/agent-factory/tasks"]:
        assert expected in served, (expected, served)


def test_the_http_module_is_self_protected():
    from agent_guard import SELF_PROTECTED

    assert "backend/routes_agent_factory.py" in SELF_PROTECTED
