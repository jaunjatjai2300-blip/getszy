"""Agent Factory — engineering tool loop.

`llm_provider.chat_completion_with_tools` is hardwired to the COMMERCE registry
(`tools.get_schemas` / `tools.execute_tool`). Rather than modify that production
file and risk the commerce tool architecture, this module reuses the provider
transports underneath it and supplies the ENGINEERING registry instead.

Reused from llm_provider (not reimplemented):
  * the provider tool-call transports (_groq_with_tools, _openrouter_with_tools,
    _lmstudio_with_tools, _ollama_with_tools)
  * the daily-limit / availability logic used to decide which are usable

Owned here:
  * engineering schemas and dispatch, via agent_tools
  * the agent message loop and tool-result feedback
  * a hard failure when no provider is genuinely usable

There is NO fallback that returns text without tools, and no stub provider. If
nothing is reachable this raises, because a plausible-sounding answer produced
without the ability to actually inspect the repository is worse than an error.
"""
from __future__ import annotations

import json
import logging
import os

from agent_tools import ENGINEERING_SCHEMAS

logger = logging.getLogger("getszy.agent.llm")

MAX_TOOL_ROUNDS = 8

# A local 14B model reasoning over tool schemas on a CPU-only VPS can take
# minutes for a single round. llm_provider's 120s is tuned for hosted commerce
# calls and would time out mid-plan here, which reads as "the model failed" when
# it was simply still thinking.
OLLAMA_TIMEOUT_SEC = float(os.environ.get("AGENT_LLM_TIMEOUT_SEC", "600"))

# Ollama's default context is small, and it TRUNCATES SILENTLY when the
# conversation outgrows it. In a tool loop that means the original instruction
# and the early tool results fall out of the window part-way through, and the
# model starts answering a question it can no longer see -- which looks like the
# model being incapable rather than the context being too short.
#
# Raising this costs KV-cache memory, so it is tunable: on a small host it has to
# be traded against the model actually fitting in RAM.
OLLAMA_NUM_CTX = int(os.environ.get("AGENT_LLM_NUM_CTX", "8192"))

# Model tier -> concrete local model. The factory assigns a tier from the agent
# description; without this mapping that tier was dead config, assigned and then
# ignored. Cheapest capable model by default, escalating only for hard work.
TIER_MODELS = {
    "light": ["llama3.2:3b", "qwen2.5:7b"],
    "standard": ["qwen2.5-coder:7b", "qwen2.5:7b", "llama3.2:3b"],
    "strong": ["qwen2.5-coder:14b", "qwen2.5-coder:7b", "qwen2.5:7b"],
}


def model_for_tier(tier: str, installed: list[str] | None = None) -> str | None:
    """Best INSTALLED model for a tier, or None if none of them are present.

    Never returns a model that is not actually installed — asking Ollama for an
    absent model fails at request time, which is a worse failure mode than
    refusing up front.

    Exact tag matches are preferred across the whole tier before falling back to
    base-name matches, so a host with `qwen2.5-coder:14b` is not served the
    `:latest` tag of a weaker family member just because it appears earlier.
    """
    preferred = TIER_MODELS.get(tier or "standard", TIER_MODELS["standard"])
    if installed is None:
        installed = installed_models()
    for m in preferred:
        if m in installed:
            return m
    # Same family, different tag (e.g. ':latest'). Still guaranteed installed.
    for m in preferred:
        base = m.split(":")[0]
        for have in installed:
            if have.split(":")[0] == base:
                return have
    return None


def ollama_base_url() -> str:
    """The Ollama endpoint, WITHOUT requiring the commerce stack to import.

    llm_provider is authoritative when it imports, but it pulls in tools -> db,
    which raises KeyError('MONGO_URL') when that is unset. Asking which models
    exist on a host is an infrastructure probe and must not depend on a database
    being configured, so this falls back to the same env var and default that
    llm_provider itself uses.
    """
    try:
        import llm_provider as lp

        return lp.OLLAMA_BASE_URL
    except Exception:
        return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


def _ollama_secret() -> str:
    """Bearer token for a protected Ollama endpoint, if one is configured."""
    try:
        import llm_provider as lp

        return getattr(lp, "OLLAMA_SECRET", "") or ""
    except Exception:
        return os.environ.get("OLLAMA_SECRET", "")


def installed_models() -> list[str]:
    """Models actually present in the local Ollama daemon."""
    import httpx

    try:
        r = httpx.get(f"{ollama_base_url()}/api/tags", timeout=4.0)
        if r.status_code != 200:
            return []
        return [m.get("name", "") for m in (r.json() or {}).get("models", [])]
    except Exception:
        return []


class NoEngineeringProvider(RuntimeError):
    """No provider with tool-calling support is currently usable."""


def available_providers() -> list[str]:
    """Which tool-capable providers are usable right now, cheapest first.

    Reads the same configuration llm_provider uses, so this cannot drift from
    production's view of what is available.
    """
    usable: list[str] = []
    # Local first: free, no quota. Only counts if a model is actually installed.
    # Probed without llm_provider so a missing MONGO_URL cannot hide a working
    # local model.
    if _ollama_has_model():
        usable.append("ollama")

    try:
        import llm_provider as lp
    except Exception as e:
        # Hosted providers are configured in llm_provider. If it cannot import we
        # genuinely do not know about them, so we report only what we verified
        # rather than guessing in either direction.
        logger.warning(
            "llm_provider did not import (%s); reporting locally-verified providers only.", e
        )
        return usable

    if getattr(lp, "LMSTUDIO_BASE_URL", "") and _lmstudio_reachable(lp):
        usable.append("lmstudio")
    if getattr(lp, "GROQ_API_KEY", "") and lp._under_limit("groq"):
        usable.append("groq")
    if getattr(lp, "OPENROUTER_API_KEY", "") and lp._openrouter_customer_allowed():
        usable.append("openrouter")
    return usable


def _ollama_has_model() -> bool:
    """An Ollama daemon with zero models cannot serve a request.

    Checked explicitly because a reachable daemon is not the same as a usable
    provider — that distinction is exactly what made an earlier run look
    available when it was not.
    """
    return bool(installed_models())


def _lmstudio_reachable(lp) -> bool:
    import httpx

    try:
        return httpx.get(f"{lp.LMSTUDIO_BASE_URL}/models", timeout=3.0).status_code == 200
    except Exception:
        return False


def _transport(name: str, model: str | None = None):
    """Return the real provider transport from llm_provider.

    For Ollama an explicit model can be pinned; see `_ollama_pinned`.
    """
    if name == "ollama" and model:
        return _ollama_pinned(model)

    import llm_provider as lp

    return {
        "groq": lp._groq_with_tools,
        "openrouter": lp._openrouter_with_tools,
        "lmstudio": lp._lmstudio_with_tools,
        "ollama": lp._ollama_with_tools,
    }[name]


def _ollama_pinned(model: str):
    """Ollama tool transport pinned to an explicit model.

    `llm_provider._ollama_with_tools` hardcodes `OLLAMA_MODELS[0]`, so a
    tier-selected model would never reach the request — the tier would look
    connected while every call silently used the commerce default.

    The obvious shortcut, reassigning `lp.OLLAMA_MODELS`, is not safe: those
    globals are shared with live commerce traffic in the same process, so a
    concurrent customer request would be served whatever model the agent picked.
    This posts to the same endpoint with the same auth and differs only in the
    model field.
    """
    import httpx

    async def call(messages, tools, temperature):
        headers = {}
        secret = _ollama_secret()
        if secret:
            headers["Authorization"] = f"Bearer {secret}"
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT_SEC) as client:
            r = await client.post(
                f"{ollama_base_url()}/api/chat",
                headers=headers,
                json={
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_ctx": OLLAMA_NUM_CTX,
                    },
                },
            )
            r.raise_for_status()
            return r.json().get("message", {})

    call.pinned_model = model  # so the caller can record what actually ran
    return call


async def engineering_tool_loop(
    *,
    system: str,
    user: str,
    execute,
    tools: list | None = None,
    temperature: float = 0.2,
    max_rounds: int = MAX_TOOL_ROUNDS,
    provider: str | None = None,
    model: str | None = None,
    tier: str | None = None,
    evidence: dict | None = None,
) -> str:
    """Run the agentic loop with the ENGINEERING toolset.

    `execute(name, args) -> str` is supplied by the runtime so every tool call is
    guarded and audited. This function never calls tools directly.

    Signature matches what agent_runtime.run_task injects as `model_call`.

    `evidence`, when supplied, is filled in with what ACTUALLY ran — provider,
    model, rounds and the tool names the model chose. It is an out-parameter so
    a caller can prove which model did the work rather than assuming it.
    """
    schemas = tools or ENGINEERING_SCHEMAS
    candidates = [provider] if provider else available_providers()
    if not candidates:
        raise NoEngineeringProvider(
            "No tool-capable LLM provider is usable. Checked: Ollama (needs at "
            "least one installed model), LM Studio, Groq, OpenRouter. Install a "
            "local model (e.g. `ollama pull qwen2.5:7b`) or configure a provider key."
        )

    # A tier is only meaningful for the local provider, where we choose the model.
    if model is None and tier and "ollama" in candidates:
        model = model_for_tier(tier)

    last_error: Exception | None = None
    for name in candidates:
        try:
            return await _run_with(
                name, system, user, schemas, execute, temperature, max_rounds,
                model if name == "ollama" else None, evidence,
            )
        except Exception as e:  # try the next provider in the chain
            last_error = e
            logger.warning("engineering loop: provider %s failed: %s", name, e)

    raise NoEngineeringProvider(f"All providers failed. Last error: {last_error}")


async def _run_with(name, system, user, schemas, execute, temperature, max_rounds,
                    model=None, evidence=None) -> str:
    call = _transport(name, model)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]

    if evidence is not None:
        evidence["provider"] = name
        evidence["model"] = getattr(call, "pinned_model", None) or _default_model(name)
        evidence["rounds"] = 0
        evidence.setdefault("tool_calls", [])

    for _round in range(max_rounds):
        msg = await call(messages, schemas, temperature)
        if evidence is not None:
            evidence["rounds"] = _round + 1
        content = msg.get("content") or ""
        calls = msg.get("tool_calls") or []

        # Some models emit the call as text rather than in the structured field.
        recovered = False
        if not calls:
            calls = _tool_calls_from_content(content, schemas)
            recovered = bool(calls)
            if recovered and evidence is not None:
                evidence["recovered_tool_calls"] = (
                    evidence.get("recovered_tool_calls", 0) + len(calls)
                )

        if not calls:
            if evidence is not None:
                evidence["final_content"] = content
            return content

        messages.append({
            "role": "assistant",
            # When the call was recovered, the content IS the call. Replaying it
            # as text as well would invite the model to simply repeat itself.
            "content": "" if recovered else content,
            "tool_calls": calls,
        })
        for tc in calls:
            fn = (tc.get("function") or {}).get("name")
            args = _args(tc)
            if evidence is not None:
                evidence["tool_calls"].append(fn)
            # Guarded + audited by the runtime's executor, never called directly.
            result = await execute(fn, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id"),
                "content": result,
            })

    # Out of rounds without a final answer is a failure, not a silent success.
    raise NoEngineeringProvider(
        f"Tool loop exceeded {max_rounds} rounds without producing a final answer."
    )


_TOOL_CALL_TAGS = ("<tool_call>", "</tool_call>", "<tool_calls>", "</tool_calls>")


def _known_tool_names(schemas) -> set[str]:
    names = set()
    for s in schemas or []:
        fn = (s or {}).get("function") or {}
        if fn.get("name"):
            names.add(fn["name"])
    return names


def _json_objects(text: str) -> list:
    """Every top-level JSON object in a string, in order.

    A plain `json.loads` fails when the model wraps the call in prose or a
    markdown fence, which is exactly the case this exists to handle.
    """
    out: list = []
    depth = 0
    start = None
    in_string = False
    escaped = False
    for i, ch in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    out.append(json.loads(text[start:i + 1]))
                except Exception:
                    pass
                start = None
    return out


def _tool_calls_from_content(content: str, schemas) -> list[dict]:
    """Recover tool calls a model emitted as text instead of structured fields.

    Observed with qwen2.5-coder through Ollama: the model selects the right tool
    with the right arguments but prints it as JSON in the message content rather
    than populating `tool_calls`. Ollama passes that straight through, so the
    loop saw "no tool calls", treated a plan as a final answer, and did nothing —
    three attempts in a row, with the model behaving correctly the whole time.

    Deliberately strict: only an object naming a tool that is actually in the
    supplied schemas becomes an action. Prose, or JSON that merely resembles a
    call, is never executed. Recovering a call the model really made is honest;
    inventing one would not be.
    """
    if not content or "{" not in content:
        return []
    known = _known_tool_names(schemas)
    if not known:
        return []

    text = content
    for tag in _TOOL_CALL_TAGS:
        text = text.replace(tag, " ")

    calls: list[dict] = []
    for obj in _json_objects(text):
        if not isinstance(obj, dict):
            continue
        fn = obj["function"] if isinstance(obj.get("function"), dict) else obj
        name = fn.get("name")
        if not isinstance(name, str) or name not in known:
            continue
        args = fn.get("arguments", fn.get("parameters", {}))
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        calls.append({
            "id": f"recovered-{len(calls)}",
            "function": {"name": name, "arguments": args if isinstance(args, dict) else {}},
        })
    return calls


def _default_model(name: str) -> str | None:
    """The model a non-pinned transport will use, read from llm_provider config."""
    import llm_provider as lp

    if name == "ollama":
        models = getattr(lp, "OLLAMA_MODELS", [])
        return models[0] if models else None
    return getattr(lp, {
        "groq": "GROQ_MODEL",
        "openrouter": "OPENROUTER_MODEL",
        "lmstudio": "LMSTUDIO_MODEL",
    }.get(name, ""), None)


def _args(tool_call: dict) -> dict:
    raw = (tool_call.get("function") or {}).get("arguments", {})
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except Exception:
        return {}


__all__ = [
    "engineering_tool_loop", "available_providers", "NoEngineeringProvider",
    "MAX_TOOL_ROUNDS", "TIER_MODELS", "model_for_tier", "installed_models",
]
