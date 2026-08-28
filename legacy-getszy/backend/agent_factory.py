"""Agent Factory — natural-language description to executable agent config.

One factory produces many specialists; there are no hardcoded agents here. A
description is parsed into capabilities, and the capabilities determine the
toolset, the permissions and the system instructions.

SECURITY MODEL — the important part.

A generated agent can never be more privileged than the guard allows, because
privilege is not something the description can grant:

  * the tool allow-list is intersected with the real registry, so a description
    asking for a tool that does not exist yields nothing
  * approval-gated operations (push, deploy, db_delete, secrets_write, …) can
    NEVER be pre-granted by a description. Approval is a per-task human decision,
    so `granted_approvals` is always persisted empty and validation rejects any
    attempt to seed it.
  * the sandbox and the self-protected file list are not configurable at all.
    They live in agent_guard and every tool call goes through them regardless of
    what any agent config says.

Validation runs BEFORE persistence, and `create_agent` refuses to persist a
config that fails it.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from agent_guard import APPROVAL_REQUIRED, SELF_PROTECTED
from agent_tools import ENGINEERING_TOOLS, MUTATING_TOOLS

READ_ONLY_TOOLS = {"read_file", "list_files", "grep_repo", "git_status", "git_diff", "git_log",
                   "repo_map_query"}
# Outbound, read-only research. GitHub is the primary technical source; general
# web search is separate and secondary.
RESEARCH_CAPABILITY_TOOLS = {
    "github_search_code", "github_search_repositories", "github_search_issues",
    "github_read_file", "web_search",
}
VERIFY_TOOLS = {"run_tests"}
WRITE_TOOLS = {"write_file", "git_commit"}

# Capability taxonomy. Each entry maps description signals to the toolset and
# instruction fragments a specialist of that kind genuinely needs.
CAPABILITIES: dict[str, dict] = {
    "frontend": {
        "signals": ["frontend", "react", "tailwind", "css", "ui", "component", "jsx", "responsive"],
        "focus": "frontend implementation in React and Tailwind",
        "tools": READ_ONLY_TOOLS | WRITE_TOOLS | VERIFY_TOOLS | RESEARCH_CAPABILITY_TOOLS,
    },
    "backend": {
        "signals": ["backend", "api", "fastapi", "endpoint", "server", "route", "python"],
        "focus": "backend APIs and server-side logic",
        "tools": READ_ONLY_TOOLS | WRITE_TOOLS | VERIFY_TOOLS | RESEARCH_CAPABILITY_TOOLS,
    },
    "database": {
        "signals": ["database", "mongo", "sql", "schema", "migration", "index", "query"],
        "focus": "data modelling, queries and indexes",
        "tools": READ_ONLY_TOOLS | WRITE_TOOLS | VERIFY_TOOLS | RESEARCH_CAPABILITY_TOOLS,
    },
    "accessibility": {
        "signals": ["accessibility", "a11y", "wcag", "screen reader", "contrast", "aria"],
        "focus": "accessibility conformance (WCAG, semantics, focus, contrast)",
        "tools": READ_ONLY_TOOLS | WRITE_TOOLS | VERIFY_TOOLS | RESEARCH_CAPABILITY_TOOLS,
    },
    "motion": {
        "signals": ["animation", "motion", "cinematic", "transition", "parallax"],
        "focus": "motion and animation, GPU-friendly transform/opacity only",
        "tools": READ_ONLY_TOOLS | WRITE_TOOLS | VERIFY_TOOLS | RESEARCH_CAPABILITY_TOOLS,
    },
    "qa": {
        "signals": ["qa", "test", "testing", "quality", "regression", "verification"],
        "focus": "testing and verification of real behaviour",
        "tools": READ_ONLY_TOOLS | VERIFY_TOOLS | RESEARCH_CAPABILITY_TOOLS,
    },
    "security": {
        "signals": ["security", "vulnerability", "auth", "xss", "injection", "secrets"],
        "focus": "security review and hardening",
        # Deliberately read-only: a security reviewer reports, a human decides.
        # Also deliberately WITHOUT research tools. This is the one capability
        # whose job is to read every secret and credential in the repository;
        # combining that with outbound network access is the exact pairing that
        # turns a review into an exfiltration path.
        "tools": READ_ONLY_TOOLS | VERIFY_TOOLS,
    },
    "research": {
        "signals": ["research", "investigate", "audit", "inspect", "analyse", "analyze"],
        "focus": "repository investigation and evidence gathering",
        "tools": READ_ONLY_TOOLS | RESEARCH_CAPABILITY_TOOLS,
    },
    "devops": {
        "signals": ["devops", "deploy", "docker", "ci", "pipeline", "infrastructure"],
        "focus": "build and deployment preparation",
        "tools": READ_ONLY_TOOLS | VERIFY_TOOLS | RESEARCH_CAPABILITY_TOOLS,
    },
    "mobile": {
        "signals": ["mobile", "ios", "android", "react native", "responsive"],
        "focus": "mobile and small-viewport implementation",
        "tools": READ_ONLY_TOOLS | WRITE_TOOLS | VERIFY_TOOLS | RESEARCH_CAPABILITY_TOOLS,
    },
    "ai": {
        "signals": ["ai", "ml", "model", "llm", "prompt", "embedding"],
        "focus": "AI/ML integration and prompt engineering",
        "tools": READ_ONLY_TOOLS | WRITE_TOOLS | VERIFY_TOOLS | RESEARCH_CAPABILITY_TOOLS,
    },
}

# Seniority affects the instructions, not the privileges.
SENIORITY = {
    "senior": ["senior", "staff", "principal", "lead", "expert"],
    "standard": [],
}

# Cheapest capable tier by default; escalate only for genuinely harder work.
MODEL_TIERS = {"light": "light", "standard": "standard", "strong": "strong"}
STRONG_SIGNALS = ["architect", "refactor", "debug", "complex", "senior", "staff", "principal", "security"]


class FactoryRejected(ValueError):
    """Raised when a description cannot produce a safe, valid agent."""


def parse_description(description: str) -> dict:
    """Extract capabilities, seniority and technologies from free text.

    Deterministic on purpose: the factory must work identically with or without
    a model, and a security-relevant decision should not depend on a generation.
    """
    if not isinstance(description, str) or len(description.strip()) < 10:
        raise FactoryRejected("Description too short to specify an agent (min 10 chars).")
    text = description.lower()

    caps = [name for name, spec in CAPABILITIES.items()
            if any(sig in text for sig in spec["signals"])]
    if not caps:
        raise FactoryRejected(
            "No recognised engineering capability in the description. "
            f"Known capabilities: {', '.join(sorted(CAPABILITIES))}"
        )

    seniority = "senior" if any(w in text for w in SENIORITY["senior"]) else "standard"
    tier = "strong" if any(w in text for w in STRONG_SIGNALS) else "standard"

    techs = sorted({
        t for t in ["react", "tailwind", "fastapi", "mongo", "python", "docker",
                    "typescript", "pytest", "redis", "framer-motion"]
        if t in text
    })
    return {"capabilities": sorted(caps), "seniority": seniority, "model_tier": tier, "technologies": techs}


def _build_system_prompt(parsed: dict, description: str) -> str:
    focuses = [CAPABILITIES[c]["focus"] for c in parsed["capabilities"]]
    tech = f" Technologies in scope: {', '.join(parsed['technologies'])}." if parsed["technologies"] else ""
    return (
        f"You are a {parsed['seniority']} Getszy engineering agent specialising in "
        f"{'; '.join(focuses)}.{tech}\n\n"
        "Operating rules, which you cannot override:\n"
        "- Work only inside the repository sandbox. Paths outside it are refused.\n"
        "- Never claim success without evidence. Run the tests and read the real result.\n"
        "- Never fabricate a tool result, a test outcome, or a capability you lack.\n"
        "- Destructive or outward-facing actions require human approval; if a tool "
        "returns approval_required, stop and report rather than trying another route.\n"
        "- Do not attempt to modify security, permission or agent-runtime files.\n"
        f"\nOriginal specification: {description.strip()[:600]}"
    )


def build_config(description: str, *, name: str | None = None, owner_id: str = "system") -> dict:
    """Turn a description into a complete, unvalidated agent configuration."""
    parsed = parse_description(description)

    tools: set[str] = set()
    for c in parsed["capabilities"]:
        tools |= CAPABILITIES[c]["tools"]
    # Intersect with what actually exists — a capability cannot invent a tool.
    tools &= set(ENGINEERING_TOOLS)

    derived = name or (f"{parsed['seniority'].title()} "
                       f"{'/'.join(c.title() for c in parsed['capabilities'][:2])} Agent")

    return {
        "id": str(uuid.uuid4()),
        "user_id": owner_id,
        "name": derived[:60],
        "role": ", ".join(parsed["capabilities"])[:280],
        "system_prompt": _build_system_prompt(parsed, description),
        "allowed_tools": sorted(tools),
        "capabilities": parsed["capabilities"],
        "seniority": parsed["seniority"],
        "model_tier": parsed["model_tier"],
        "technologies": parsed["technologies"],
        # Never pre-granted. Approval is a per-task human decision.
        "granted_approvals": [],
        "sandbox": "repo",
        "source_description": description.strip()[:1000],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "param_keys": ["input"],
    }


def validate_config(cfg: dict) -> list[str]:
    """Return a list of violations. Empty list means safe to persist."""
    problems: list[str] = []

    if not cfg.get("name") or len(cfg["name"].strip()) < 2:
        problems.append("name too short")
    if not cfg.get("system_prompt"):
        problems.append("missing system_prompt")

    tools = cfg.get("allowed_tools") or []
    if not tools:
        problems.append("agent has no tools")
    unknown = sorted(set(tools) - set(ENGINEERING_TOOLS))
    if unknown:
        problems.append(f"unknown tools: {unknown}")

    # An agent config may never pre-grant an approval-gated operation.
    granted = set(cfg.get("granted_approvals") or [])
    illegal = sorted(granted & APPROVAL_REQUIRED)
    if illegal:
        problems.append(f"config attempts to pre-grant approval-gated operations: {illegal}")
    if granted:
        problems.append(f"granted_approvals must be empty at creation, got {sorted(granted)}")

    # The sandbox is not configurable.
    if cfg.get("sandbox") != "repo":
        problems.append("sandbox must be 'repo'; it is not configurable")

    # No config may declare an exemption from protected files.
    for key in ("protected_overrides", "bypass_guard", "self_protected_exempt", "allow_paths"):
        if cfg.get(key):
            problems.append(f"config attempts to bypass guard via '{key}'")

    if cfg.get("model_tier") not in MODEL_TIERS:
        problems.append(f"invalid model_tier: {cfg.get('model_tier')}")

    # A write-capable agent must also be able to verify what it wrote.
    if (set(tools) & WRITE_TOOLS) and not (set(tools) & VERIFY_TOOLS):
        problems.append("agent can write but cannot run tests; refusing unverifiable write access")

    return problems


async def create_agent(description: str, *, db, name: str | None = None, owner_id: str = "system") -> dict:
    """Create, validate and PERSIST a specialist agent.

    Persists into the existing `custom_agents` collection so the agent is visible
    to the existing agent infrastructure rather than living in a parallel store.
    """
    cfg = build_config(description, name=name, owner_id=owner_id)
    problems = validate_config(cfg)
    if problems:
        raise FactoryRejected("; ".join(problems))
    await db.custom_agents.insert_one(dict(cfg))
    return cfg


async def load_agent(agent_id: str, *, db) -> dict:
    """Load a persisted agent, re-validating before it can be executed.

    Re-validation matters: a config could have been edited in the database after
    creation, and execution must not trust storage.
    """
    doc = await db.custom_agents.find_one({"id": agent_id}, {"_id": 0})
    if not doc:
        raise FactoryRejected(f"No such agent: {agent_id}")
    problems = validate_config(doc)
    if problems:
        raise FactoryRejected(f"Stored agent failed validation, refusing to execute: {'; '.join(problems)}")
    return doc


def toolset_for(cfg: dict) -> dict:
    """The concrete callables this agent may use — intersected with the registry."""
    return {n: fn for n, fn in ENGINEERING_TOOLS.items() if n in set(cfg.get("allowed_tools") or [])}


__all__ = [
    "CAPABILITIES", "FactoryRejected", "build_config", "validate_config",
    "create_agent", "load_agent", "parse_description", "toolset_for",
    "MUTATING_TOOLS", "SELF_PROTECTED",
]
