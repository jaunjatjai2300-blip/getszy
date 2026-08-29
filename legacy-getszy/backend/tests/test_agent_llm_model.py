"""Tests for model selection actually reaching the request, and tool restriction
actually being enforced.

Both were previously advertised but not connected: `model_for_tier` returned a
name that the transport ignored in favour of the commerce default, and the
factory's `allowed_tools` was published to the model without being enforced when
a tool was called. These tests fail if either regresses.

No network: the transport is exercised against a stub HTTP client so the request
payload can be inspected directly.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("JWT_SECRET", "test-only-agent-llm-secret-32-chars!!!!")

import agent_llm  # noqa: E402
import agent_runtime as rt  # noqa: E402


# ── tier -> installed model ──────────────────────────────────────────────────

def test_tier_resolves_to_an_installed_model():
    installed = ["llama3.2:3b", "qwen2.5:7b", "qwen2.5-coder:14b"]
    assert agent_llm.model_for_tier("strong", installed) == "qwen2.5-coder:14b"
    assert agent_llm.model_for_tier("light", installed) == "llama3.2:3b"


def test_tier_never_returns_an_uninstalled_model():
    assert agent_llm.model_for_tier("strong", []) is None
    chosen = agent_llm.model_for_tier("strong", ["llama3.2:3b"])
    assert chosen in (None, "llama3.2:3b")


def test_exact_tag_wins_over_a_same_family_fallback():
    """A ':latest' sibling must not shadow the exact tag the tier asked for."""
    installed = ["qwen2.5-coder:latest", "qwen2.5-coder:14b"]
    assert agent_llm.model_for_tier("strong", installed) == "qwen2.5-coder:14b"


def test_same_family_different_tag_is_accepted_when_exact_is_absent():
    installed = ["qwen2.5-coder:latest"]
    assert agent_llm.model_for_tier("strong", installed) == "qwen2.5-coder:latest"


# ── the chosen model reaches the HTTP payload ────────────────────────────────

class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _Client:
    """Stub httpx.AsyncClient that records the request instead of sending it."""
    captured: list[dict] = []
    replies: list[dict] = []

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, headers=None, json=None):
        _Client.captured.append({"url": url, "json": json})
        reply = _Client.replies.pop(0) if _Client.replies else {"content": "done"}
        return _Response({"message": reply})


@pytest.fixture
def stub_http(monkeypatch):
    import httpx

    _Client.captured = []
    _Client.replies = []
    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    return _Client


@pytest.mark.asyncio
async def test_pinned_model_is_sent_in_the_request(stub_http):
    call = agent_llm._transport("ollama", "qwen2.5-coder:14b")
    await call([{"role": "user", "content": "hi"}], [], 0.1)
    assert stub_http.captured, "no request was made"
    assert stub_http.captured[0]["json"]["model"] == "qwen2.5-coder:14b"


def test_pinned_transport_reports_which_model_it_will_use():
    call = agent_llm._transport("ollama", "qwen2.5:7b")
    assert getattr(call, "pinned_model", None) == "qwen2.5:7b"


@pytest.mark.asyncio
async def test_loop_records_the_model_that_actually_ran(stub_http):
    evidence: dict = {}

    async def execute(name, args):
        return json.dumps({"ok": True})

    stub_http.replies = [{"content": "finished"}]
    out = await agent_llm.engineering_tool_loop(
        system="s", user="u", execute=execute, tools=[],
        provider="ollama", model="qwen2.5-coder:14b", evidence=evidence,
    )
    assert out == "finished"
    assert evidence["provider"] == "ollama"
    assert evidence["model"] == "qwen2.5-coder:14b"
    assert evidence["rounds"] == 1


@pytest.mark.asyncio
async def test_loop_records_every_tool_the_model_selected(stub_http):
    seen = []

    async def execute(name, args):
        seen.append(name)
        return json.dumps({"ok": True})

    stub_http.replies = [
        {"content": "", "tool_calls": [
            {"id": "1", "function": {"name": "read_file", "arguments": {"path": "backend/agent_guard.py"}}}]},
        {"content": "all done"},
    ]
    evidence: dict = {}
    await agent_llm.engineering_tool_loop(
        system="s", user="u", execute=execute, tools=[],
        provider="ollama", model="qwen2.5:7b", evidence=evidence,
    )
    assert seen == ["read_file"]
    assert evidence["tool_calls"] == ["read_file"]
    assert evidence["rounds"] == 2


# ── allowed_tools is enforced, not merely advertised ─────────────────────────

@pytest.mark.asyncio
async def test_tool_outside_the_agents_allowlist_is_refused():
    """A model can name a tool it was never offered; the executor must refuse it."""
    results = {}

    async def driver(system, user, tools, execute):
        results["offered"] = sorted(s["function"]["name"] for s in tools)
        results["write"] = json.loads(await execute("write_file", {"path": "x.txt", "content": "y"}))
        results["read"] = json.loads(await execute("read_file", {"path": "backend/agent_guard.py"}))

    await rt.run_task(
        "inspect only",
        system_prompt="test",
        model_call=driver,
        max_attempts=1,
        allowed_tools=["read_file", "run_tests"],
    )

    assert results["offered"] == ["read_file", "run_tests"]
    assert results["write"]["error"] == "tool_not_permitted"
    assert "content" in results["read"], "permitted tool must still work"


@pytest.mark.asyncio
async def test_no_allowlist_means_the_full_registry_is_offered():
    from agent_tools import ENGINEERING_TOOLS

    offered = {}

    async def driver(system, user, tools, execute):
        offered["names"] = {s["function"]["name"] for s in tools}

    await rt.run_task("anything", system_prompt="test", model_call=driver, max_attempts=1)
    assert offered["names"] == set(ENGINEERING_TOOLS)


@pytest.mark.asyncio
async def test_refused_tool_is_recorded_in_the_audit():
    async def driver(system, user, tools, execute):
        await execute("git_push", {"remote": "origin"})

    audit = await rt.run_task(
        "try to push", system_prompt="test", model_call=driver,
        max_attempts=1, allowed_tools=["read_file"],
    )
    assert any(a["tool"] == "git_push" and not a["ok"] for a in audit["actions"])
    assert any(f.get("error") == "tool_not_permitted" for f in audit["failures"])


# ── the factory runtime is not agent-writable ────────────────────────────────

def test_factory_runtime_files_are_self_protected():
    """An agent that can rewrite verify() can certify its own failures as passes."""
    from agent_guard import SELF_PROTECTED

    for critical in [
        "backend/agent_runtime.py",
        "backend/agent_factory.py",
        "backend/agent_llm.py",
        "backend/agent_persistence.py",
        "backend/acceptance_agent_factory.py",
        "backend/acceptance_persistence.py",
        "backend/acceptance_delegation.py",
    ]:
        assert critical in SELF_PROTECTED, critical


# ── acceptance harness path normalisation ────────────────────────────────────
#
# The agent sandbox is <git root>/legacy-getszy, so `git show --name-only`
# returns "legacy-getszy/backend/x.py" while the guard speaks in
# "backend/x.py". Comparing them unnormalised makes every criterion match
# nothing and pass for the wrong reason.

def test_git_paths_are_normalised_to_the_sandbox_root():
    import acceptance_agent_factory as acc

    assert acc.sandbox_relative(
        "legacy-getszy/backend/slug_utils.py", "legacy-getszy/") == "backend/slug_utils.py"


def test_paths_outside_the_sandbox_are_dropped_not_mismatched():
    import acceptance_agent_factory as acc

    assert acc.sandbox_relative("README.md", "legacy-getszy/") is None


def test_no_prefix_means_paths_pass_through_unchanged():
    import acceptance_agent_factory as acc

    assert acc.sandbox_relative("backend/slug_utils.py", "") == "backend/slug_utils.py"


def test_protected_file_would_be_detected_after_normalisation():
    """The regression this guards: a protected path must still be recognised
    once the git prefix is stripped."""
    import acceptance_agent_factory as acc
    from agent_guard import SELF_PROTECTED

    normalised = acc.sandbox_relative("legacy-getszy/backend/auth.py", "legacy-getszy/")
    assert normalised in SELF_PROTECTED


def test_missing_executable_is_reported_not_raised():
    """A missing binary must become a preflight message, not a traceback."""
    import acceptance_agent_factory as acc

    out = acc.sh("definitely-not-a-real-binary-xyz")
    assert out["code"] == 127
    assert "not found" in out["err"]


@pytest.mark.asyncio
async def test_context_window_is_set_explicitly(stub_http):
    """Ollama truncates silently, which would drop the task mid tool-loop."""
    call = agent_llm._transport("ollama", "qwen2.5-coder:7b")
    await call([{"role": "user", "content": "hi"}], [], 0.1)
    options = stub_http.captured[0]["json"]["options"]
    assert options["num_ctx"] == agent_llm.OLLAMA_NUM_CTX
    assert options["num_ctx"] >= 4096


# ── tool calls emitted as text instead of structured fields ──────────────────
#
# Observed on the VPS: qwen2.5-coder:7b selected the right tool with the right
# argument but printed it in `content`. The loop saw tool_calls == [] and treated
# a plan as a final answer, doing nothing for three attempts while the model was
# behaving correctly.

SCHEMAS = [
    {"type": "function", "function": {"name": "read_file", "parameters": {}}},
    {"type": "function", "function": {"name": "run_tests", "parameters": {}}},
]


def test_recovers_the_exact_payload_the_vps_model_produced():
    content = '{"name": "read_file", "arguments": {"path": "backend/tests/test_slug_utils.py"}}'
    calls = agent_llm._tool_calls_from_content(content, SCHEMAS)
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "read_file"
    assert calls[0]["function"]["arguments"] == {"path": "backend/tests/test_slug_utils.py"}


def test_recovers_from_a_markdown_fence():
    content = 'I will start by reading it.\n```json\n{"name": "run_tests", "arguments": {}}\n```'
    calls = agent_llm._tool_calls_from_content(content, SCHEMAS)
    assert [c["function"]["name"] for c in calls] == ["run_tests"]


def test_recovers_from_a_tool_call_tag_wrapper():
    content = '<tool_call>{"name": "read_file", "arguments": {"path": "a.py"}}</tool_call>'
    calls = agent_llm._tool_calls_from_content(content, SCHEMAS)
    assert calls[0]["function"]["arguments"] == {"path": "a.py"}


def test_recovers_the_openai_style_nesting():
    content = '{"function": {"name": "read_file", "arguments": "{\\"path\\": \\"b.py\\"}"}}'
    calls = agent_llm._tool_calls_from_content(content, SCHEMAS)
    assert calls[0]["function"]["arguments"] == {"path": "b.py"}


def test_prose_is_never_turned_into_an_action():
    for content in [
        "I will read backend/tests/test_slug_utils.py and then run the tests.",
        "",
        "Here is some JSON: {\"unrelated\": true}",
    ]:
        assert agent_llm._tool_calls_from_content(content, SCHEMAS) == []


def test_an_unregistered_tool_name_is_never_executed():
    """Recovering a call the model made is honest; inventing a tool is not."""
    content = '{"name": "rm_rf", "arguments": {"path": "/"}}'
    assert agent_llm._tool_calls_from_content(content, SCHEMAS) == []


@pytest.mark.asyncio
async def test_structured_tool_calls_take_precedence(stub_http):
    """A model that populates the field correctly must be unaffected."""
    seen = []

    async def execute(name, args):
        seen.append(name)
        return json.dumps({"ok": True})

    stub_http.replies = [
        {"content": '{"name": "run_tests", "arguments": {}}',
         "tool_calls": [{"id": "1", "function": {"name": "read_file", "arguments": {"path": "x"}}}]},
        {"content": "done"},
    ]
    ev: dict = {}
    await agent_llm.engineering_tool_loop(
        system="s", user="u", execute=execute, tools=SCHEMAS,
        provider="ollama", model="qwen2.5:7b", evidence=ev,
    )
    assert seen == ["read_file"], "the structured field must win"
    assert ev.get("recovered_tool_calls", 0) == 0


@pytest.mark.asyncio
async def test_loop_executes_a_call_that_arrived_as_content(stub_http):
    """End to end: the previously-dropped call now reaches the executor."""
    seen = []

    async def execute(name, args):
        seen.append((name, args))
        return json.dumps({"ok": True})

    stub_http.replies = [
        {"content": '{"name": "read_file", "arguments": {"path": "backend/tests/test_slug_utils.py"}}'},
        {"content": "I have read it."},
    ]
    ev: dict = {}
    out = await agent_llm.engineering_tool_loop(
        system="s", user="u", execute=execute, tools=SCHEMAS,
        provider="ollama", model="qwen2.5-coder:7b", evidence=ev,
    )
    assert seen == [("read_file", {"path": "backend/tests/test_slug_utils.py"})]
    assert ev["recovered_tool_calls"] == 1
    assert ev["tool_calls"] == ["read_file"]
    assert out == "I have read it."


# ── an identical call repeated forever teaches the model nothing ─────────────
#
# A real specialist ran the same failing pytest fifteen times and exhausted its
# rounds without ever attempting the write it needed.

@pytest.mark.asyncio
async def test_an_identically_repeated_call_is_intervened_on(stub_http):
    executed = []

    async def execute(name, args):
        executed.append(name)
        return json.dumps({"exit_code": 2, "passed": False})

    call = {"id": "1", "function": {"name": "run_tests", "arguments": {"target": "t.py"}}}
    stub_http.replies = [{"content": "", "tool_calls": [call]} for _ in range(6)] + \
                        [{"content": "giving up"}]
    ev: dict = {}
    await agent_llm.engineering_tool_loop(
        system="s", user="u", execute=execute, tools=[],
        provider="ollama", model="qwen2.5-coder:7b", evidence=ev, max_rounds=8,
    )
    assert len(executed) == agent_llm.MAX_IDENTICAL_REPEATS, \
        f"the tool must stop being run after {agent_llm.MAX_IDENTICAL_REPEATS} identical calls"
    assert ev["repeated_calls"] >= 1


@pytest.mark.asyncio
async def test_a_legitimate_write_then_test_cycle_is_not_intervened_on(stub_http):
    """write -> test -> write -> test is normal repair, not a stuck loop."""
    executed = []

    async def execute(name, args):
        executed.append(name)
        return json.dumps({"ok": True})

    def tc(n, name, args):
        return {"id": str(n), "function": {"name": name, "arguments": args}}

    stub_http.replies = [
        {"content": "", "tool_calls": [tc(1, "write_file", {"path": "a.py", "content": "v1"})]},
        {"content": "", "tool_calls": [tc(2, "run_tests", {"target": "t.py"})]},
        {"content": "", "tool_calls": [tc(3, "write_file", {"path": "a.py", "content": "v2"})]},
        {"content": "", "tool_calls": [tc(4, "run_tests", {"target": "t.py"})]},
        {"content": "done"},
    ]
    ev: dict = {}
    await agent_llm.engineering_tool_loop(
        system="s", user="u", execute=execute, tools=[],
        provider="ollama", model="qwen2.5-coder:7b", evidence=ev, max_rounds=8,
    )
    assert executed == ["write_file", "run_tests", "write_file", "run_tests"]
    assert ev.get("repeated_calls", 0) == 0


@pytest.mark.asyncio
async def test_the_repeat_guard_says_the_tool_was_not_run(stub_http):
    """It must be honest that no tool ran, not fabricate a result."""
    seen = []

    async def execute(name, args):
        return json.dumps({"exit_code": 2})

    call = {"id": "1", "function": {"name": "run_tests", "arguments": {}}}
    stub_http.replies = [{"content": "", "tool_calls": [call]} for _ in range(5)] + \
                        [{"content": "stopping"}]

    original = agent_llm._transport

    await agent_llm.engineering_tool_loop(
        system="s", user="u", execute=execute, tools=[],
        provider="ollama", model="qwen2.5-coder:7b", max_rounds=8,
    )
    # the guard message is fed back as the tool result
    fed = [m for m in stub_http.captured[-1]["json"]["messages"] if m.get("role") == "tool"]
    guard_messages = [m for m in fed if "repeated_call" in m["content"]]
    assert guard_messages, "the model must be told it is repeating itself"
    assert "not run again" in guard_messages[0]["content"]


# ── regression: the tool loop bounds honestly (surfaced by the spec_e2e run) ──
@pytest.mark.asyncio
async def test_tool_loop_bounds_and_reports_when_model_never_finishes(stub_http):
    """A model that keeps calling tools and never emits a final answer must hit
    the max_rounds bound and RAISE an honest failure — never hang, never fabricate
    a success. This is exactly what surfaced the spec_e2e failure: an ill-posed
    task with no reachable stopping condition. The runtime is correct; it bounds
    and reports rather than looping forever or claiming success."""
    async def execute(name, args):
        return json.dumps({"exit_code": 1, "passed": False})   # never a passing state

    # every round is another (distinct, so repeat-detection does not short-circuit)
    # tool call — the model never produces a final answer
    stub_http.replies = [
        {"content": "", "tool_calls": [
            {"id": str(i), "function": {"name": "read_file", "arguments": {"path": f"backend/x{i}.py"}}}]}
        for i in range(12)
    ]
    with pytest.raises(agent_llm.NoEngineeringProvider) as e:
        await agent_llm.engineering_tool_loop(
            system="s", user="u", execute=execute, tools=[],
            provider="ollama", model="qwen2.5-coder:14b", max_rounds=8)
    assert "exceeded 8 rounds" in str(e.value)          # honest bound, not a silent success
