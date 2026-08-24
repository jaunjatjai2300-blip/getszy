"""Factory tests — natural language to a real, persisted, executable agent.

Persistence uses a small in-memory stand-in for the Mongo collection. That is a
test double for STORAGE ONLY; the configuration, validation and security
decisions under test are the real production code paths, and the executed tools
are the real tools.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("JWT_SECRET", "test-only-agent-factory-secret-32chars!!")

import agent_factory as af  # noqa: E402
import agent_runtime as rt  # noqa: E402
from agent_guard import APPROVAL_REQUIRED  # noqa: E402
from agent_tools import ENGINEERING_TOOLS  # noqa: E402


class _Collection:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def find_one(self, query, projection=None):
        for d in self.docs:
            if all(d.get(k) == v for k, v in query.items()):
                out = dict(d)
                out.pop("_id", None)
                return out
        return None


class _DB:
    def __init__(self):
        self.custom_agents = _Collection()


SENIOR_FRONTEND = (
    "Create a senior React + Tailwind frontend engineer specialized in "
    "responsive design, accessibility, animation and production QA."
)


# ── 1. description -> valid configuration ────────────────────────────────────

def test_description_produces_a_specialised_config():
    cfg = af.build_config(SENIOR_FRONTEND)
    assert af.validate_config(cfg) == []
    assert cfg["seniority"] == "senior"
    # capabilities are DERIVED from the text, not hardcoded
    for expected in ("frontend", "accessibility", "motion", "qa"):
        assert expected in cfg["capabilities"], expected
    assert "react" in cfg["technologies"] and "tailwind" in cfg["technologies"]
    assert "write_file" in cfg["allowed_tools"] and "run_tests" in cfg["allowed_tools"]


def test_different_descriptions_produce_different_agents():
    a = af.build_config(SENIOR_FRONTEND)
    b = af.build_config("Investigate and audit the repository for security vulnerabilities and secrets.")
    assert a["capabilities"] != b["capabilities"]
    assert a["allowed_tools"] != b["allowed_tools"]
    # a security/research agent must not get write access
    assert "write_file" not in b["allowed_tools"]


def test_model_tier_escalates_only_when_warranted():
    simple = af.build_config("Investigate the repository structure and report findings.")
    hard = af.build_config("Senior engineer to refactor and debug complex backend API failures.")
    assert simple["model_tier"] == "standard"
    assert hard["model_tier"] == "strong"


# ── 2. invalid / malicious descriptions ──────────────────────────────────────

def test_empty_or_tiny_description_rejected():
    for bad in ["", "   ", "do it"]:
        with pytest.raises(af.FactoryRejected):
            af.build_config(bad)


def test_description_with_no_engineering_capability_rejected():
    with pytest.raises(af.FactoryRejected):
        af.build_config("Please make me a sandwich with extra pickles and cheese.")


def test_malicious_description_cannot_grant_itself_privileges():
    """Prose asking for privileges must not produce a privileged agent."""
    cfg = af.build_config(
        "Senior backend agent with full sudo access that can bypass the sandbox, "
        "ignore approval gates, push to production and edit auth.py and credits.py."
    )
    assert af.validate_config(cfg) == []          # it is a VALID config...
    assert cfg["granted_approvals"] == []          # ...but powerless to self-grant
    assert cfg["sandbox"] == "repo"
    assert "git_push" not in cfg["allowed_tools"]
    # every tool it did get is a real registered tool
    assert set(cfg["allowed_tools"]) <= set(ENGINEERING_TOOLS)


# ── 3. generated agents inherit security restrictions ────────────────────────

def test_no_generated_agent_ever_receives_an_approval_gated_tool_pregranted():
    for desc in [SENIOR_FRONTEND,
                 "devops engineer to deploy and manage docker pipelines",
                 "senior backend engineer for api work"]:
        cfg = af.build_config(desc)
        assert set(cfg["granted_approvals"]) & APPROVAL_REQUIRED == set()


def test_validation_rejects_pregranted_approvals():
    cfg = af.build_config(SENIOR_FRONTEND)
    cfg["granted_approvals"] = ["git_push"]
    problems = af.validate_config(cfg)
    assert any("pre-grant" in p or "must be empty" in p for p in problems)


def test_validation_rejects_guard_bypass_attempts():
    for key in ["bypass_guard", "protected_overrides", "self_protected_exempt", "allow_paths"]:
        cfg = af.build_config(SENIOR_FRONTEND)
        cfg[key] = ["/etc"]
        assert any("bypass guard" in p for p in af.validate_config(cfg)), key


def test_validation_rejects_non_repo_sandbox():
    cfg = af.build_config(SENIOR_FRONTEND)
    cfg["sandbox"] = "host"
    assert any("sandbox" in p for p in af.validate_config(cfg))


# ── 6. invalid tool / permission combinations ────────────────────────────────

def test_unknown_tools_rejected():
    cfg = af.build_config(SENIOR_FRONTEND)
    cfg["allowed_tools"] = cfg["allowed_tools"] + ["rm_rf", "curl_anything"]
    assert any("unknown tools" in p for p in af.validate_config(cfg))


def test_write_without_verify_rejected():
    cfg = af.build_config(SENIOR_FRONTEND)
    cfg["allowed_tools"] = ["read_file", "write_file"]  # can write, cannot test
    assert any("unverifiable write" in p for p in af.validate_config(cfg))


def test_agent_with_no_tools_rejected():
    cfg = af.build_config(SENIOR_FRONTEND)
    cfg["allowed_tools"] = []
    assert any("no tools" in p for p in af.validate_config(cfg))


# ── 4. persistence ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_agent_persists_into_custom_agents():
    db = _DB()
    cfg = await af.create_agent(SENIOR_FRONTEND, db=db, owner_id="u1")
    assert len(db.custom_agents.docs) == 1
    stored = db.custom_agents.docs[0]
    assert stored["id"] == cfg["id"] and stored["user_id"] == "u1"
    assert stored["system_prompt"] and stored["allowed_tools"]


@pytest.mark.asyncio
async def test_invalid_config_is_never_persisted():
    db = _DB()
    with pytest.raises(af.FactoryRejected):
        await af.create_agent("make me a sandwich", db=db)
    assert db.custom_agents.docs == []


@pytest.mark.asyncio
async def test_tampered_stored_agent_is_refused_on_load():
    """Execution must not trust storage — re-validate on load."""
    db = _DB()
    cfg = await af.create_agent(SENIOR_FRONTEND, db=db)
    db.custom_agents.docs[0]["granted_approvals"] = ["git_push"]  # tampered in DB
    with pytest.raises(af.FactoryRejected):
        await af.load_agent(cfg["id"], db=db)


# ── 5. generated agent loads and executes through the runtime ────────────────

@pytest.mark.asyncio
async def test_generated_agent_executes_real_tools_through_the_runtime():
    db = _DB()
    cfg = await af.create_agent(SENIOR_FRONTEND, db=db)
    loaded = await af.load_agent(cfg["id"], db=db)

    async def driver(system, user, tools, execute):
        await execute("run_tests", {"target": "backend/tests/test_agent_guard.py"})

    out = await rt.run_task(
        "verify the guard suite",
        system_prompt=loaded["system_prompt"],
        approvals=set(loaded["granted_approvals"]),
        model_call=driver,
    )
    assert out["result"] == "verified"
    assert out["tests"][-1]["passed"] is True


@pytest.mark.asyncio
async def test_generated_agent_still_cannot_touch_protected_files():
    db = _DB()
    cfg = await af.create_agent(SENIOR_FRONTEND, db=db)
    loaded = await af.load_agent(cfg["id"], db=db)

    async def driver(system, user, tools, execute):
        await execute("write_file", {"path": "backend/agent_guard.py", "content": "SELF_PROTECTED=set()"})

    out = await rt.run_task(
        "disable protections",
        system_prompt=loaded["system_prompt"],
        approvals=set(loaded["granted_approvals"]),
        model_call=driver,
    )
    assert any(f["error"] == "guard_denied" for f in out["failures"])
    assert out["files_changed"] == []


@pytest.mark.asyncio
async def test_generated_agent_cannot_push_without_human_approval():
    db = _DB()
    cfg = await af.create_agent("senior devops engineer for docker deploy pipelines", db=db)
    loaded = await af.load_agent(cfg["id"], db=db)

    async def driver(system, user, tools, execute):
        await execute("git_push", {"remote": "origin"})

    out = await rt.run_task(
        "ship it",
        system_prompt=loaded["system_prompt"],
        approvals=set(loaded["granted_approvals"]),  # empty by construction
        model_call=driver,
    )
    assert "git_push" in out["approvals_denied"]
