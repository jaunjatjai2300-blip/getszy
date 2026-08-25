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

from agent_tools import ENGINEERING_SCHEMAS

logger = logging.getLogger("getszy.agent.llm")

MAX_TOOL_ROUNDS = 8

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
    """
    preferred = TIER_MODELS.get(tier or "standard", TIER_MODELS["standard"])
    if installed is None:
        installed = installed_models()
    for m in preferred:
        if m in installed:
            return m
    return None


def installed_models() -> list[str]:
    """Models actually present in the local Ollama daemon."""
    import httpx
    import llm_provider as lp
    try:
        r = httpx.get(f"{lp.OLLAMA_BASE_URL}/api/tags", timeout=4.0)
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
    import llm_provider as lp

    usable: list[str] = []
    # Local first: free, no quota. Only counts if a model is actually installed.
    if _ollama_has_model(lp):
        usable.append("ollama")
    if getattr(lp, "LMSTUDIO_BASE_URL", "") and _lmstudio_reachable(lp):
        usable.append("lmstudio")
    if getattr(lp, "GROQ_API_KEY", "") and lp._under_limit("groq"):
        usable.append("groq")
    if getattr(lp, "OPENROUTER_API_KEY", "") and lp._openrouter_customer_allowed():
        usable.append("openrouter")
    return usable


def _ollama_has_model(lp) -> bool:
    """An Ollama daemon with zero models cannot serve a request.

    Checked explicitly because a reachable daemon is not the same as a usable
    provider — that distinction is exactly what made an earlier run look
    available when it was not.
    """
    import httpx

    try:
        r = httpx.get(f"{lp.OLLAMA_BASE_URL}/api/tags", timeout=4.0)
        if r.status_code != 200:
            return False
        return bool((r.json() or {}).get("models"))
    except Exception:
        return False


def _lmstudio_reachable(lp) -> bool:
    import httpx

    try:
        return httpx.get(f"{lp.LMSTUDIO_BASE_URL}/models", timeout=3.0).status_code == 200
    except Exception:
        return False


def _transport(name: str):
    """Return the real provider transport from llm_provider."""
    import llm_provider as lp

    return {
        "groq": lp._groq_with_tools,
        "openrouter": lp._openrouter_with_tools,
        "lmstudio": lp._lmstudio_with_tools,
        "ollama": lp._ollama_with_tools,
    }[name]


async def engineering_tool_loop(
    *,
    system: str,
    user: str,
    execute,
    tools: list | None = None,
    temperature: float = 0.2,
    max_rounds: int = MAX_TOOL_ROUNDS,
    provider: str | None = None,
) -> str:
    """Run the agentic loop with the ENGINEERING toolset.

    `execute(name, args) -> str` is supplied by the runtime so every tool call is
    guarded and audited. This function never calls tools directly.

    Signature matches what agent_runtime.run_task injects as `model_call`.
    """
    schemas = tools or ENGINEERING_SCHEMAS
    candidates = [provider] if provider else available_providers()
    if not candidates:
        raise NoEngineeringProvider(
            "No tool-capable LLM provider is usable. Checked: Ollama (needs at "
            "least one installed model), LM Studio, Groq, OpenRouter. Install a "
            "local model (e.g. `ollama pull qwen2.5:7b`) or configure a provider key."
        )

    last_error: Exception | None = None
    for name in candidates:
        try:
            return await _run_with(name, system, user, schemas, execute, temperature, max_rounds)
        except Exception as e:  # try the next provider in the chain
            last_error = e
            logger.warning("engineering loop: provider %s failed: %s", name, e)

    raise NoEngineeringProvider(f"All providers failed. Last error: {last_error}")


async def _run_with(name, system, user, schemas, execute, temperature, max_rounds) -> str:
    call = _transport(name)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]

    for _round in range(max_rounds):
        msg = await call(messages, schemas, temperature)
        calls = msg.get("tool_calls") or []
        if not calls:
            return msg.get("content") or ""

        messages.append({
            "role": "assistant",
            "content": msg.get("content") or "",
            "tool_calls": calls,
        })
        for tc in calls:
            fn = (tc.get("function") or {}).get("name")
            args = _args(tc)
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


def _args(tool_call: dict) -> dict:
    raw = (tool_call.get("function") or {}).get("arguments", {})
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw or "{}")
    except Exception:
        return {}


__all__ = ["engineering_tool_loop", "available_providers", "NoEngineeringProvider", "MAX_TOOL_ROUNDS"]
