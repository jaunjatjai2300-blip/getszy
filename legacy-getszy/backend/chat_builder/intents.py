"""Intent classifier for the Universal AI Chat Builder.

Uses the existing LLM provider abstraction (no new integrations) to classify
free-form user prompts into an intent plus a params object that can be dispatched
to any registered capability.

Designed to be extended: adding a capability to `capabilities.CAPABILITIES` also
makes it available here without code changes to this module.
"""
import json
from typing import Dict, Any, List
from llm_provider import chat_completion
from chat_builder.capabilities import CAPABILITIES


def _capabilities_catalog(min_level: int = 1) -> str:
    """Only include capabilities the caller is allowed to invoke.

    min_level: 0=visitor 1=customer 2=founder 3=admin (from auth.ROLE_LEVEL).
    """
    from auth import ROLE_LEVEL
    lines: List[str] = []
    for cid, spec in CAPABILITIES.items():
        cap_level = ROLE_LEVEL.get(spec.get('min_role', 'customer'), 1)
        if cap_level > min_level:
            continue
        params_hint = ', '.join([f"{k}: {v}" for k, v in spec.get('params', {}).items()])
        lines.append(f'  - {cid}: {spec["desc"]} | params({params_hint})')
    return '\n'.join(lines)


SYSTEM_PROMPT = (
    'You are the router for Getszy Build Studio, a self-serve AI platform for Indian '
    'creators + founders. Given a user message and short conversation history, decide '
    'which capability to invoke. NEVER invent capabilities that are not listed.\n\n'
    'CAPABILITIES:\n__CATALOG__\n\n'
    'RULES:\n'
    '1. Reply ONLY JSON with keys: intent, params, human_reply. No prose outside JSON.\n'
    '2. `intent` must be one of the capability ids above, OR `general_chat` if the user is just chatting.\n'
    '3. `params` must satisfy the required fields of that capability (see param hints). Infer missing '
    'fields from context; if truly ambiguous, set intent=general_chat and ask a clarifying question '
    'in human_reply.\n'
    '4. `human_reply` is a SHORT (≤30 words) Hinglish/Hindi acknowledgement of what you are about to do, '
    'or a clarifying question when intent=general_chat. Keep it warm and conversational, like a friend.\n'
    '5. Never expose raw JSON to the user — it is machine-facing only.'
)


async def classify(user_message: str, history: List[Dict[str, Any]] | None = None, min_level: int = 1) -> Dict[str, Any]:
    """Return {intent, params, human_reply}. Guaranteed to have all three keys.

    min_level: caller's role level; only capabilities at or below that level are exposed.
    """
    catalog = _capabilities_catalog(min_level=min_level)
    sys = SYSTEM_PROMPT.replace('__CATALOG__', catalog)
    # Compact history hint (last 6 turns)
    hist_lines: List[str] = []
    for m in (history or [])[-6:]:
        role = m.get('role', 'user')
        txt = (m.get('content') or '')[:400]
        hist_lines.append(f'{role.upper()}: {txt}')
    user_prompt = ('CONVERSATION SO FAR:\n' + '\n'.join(hist_lines) + '\n\n') if hist_lines else ''
    user_prompt += f'USER MESSAGE:\n{user_message[:2000]}'
    raw = await chat_completion(system=sys, user=user_prompt, temperature=0.3)
    parsed = _parse(raw)
    # Sanitize
    intent = parsed.get('intent') or 'general_chat'
    if intent not in CAPABILITIES and intent != 'general_chat':
        intent = 'general_chat'
    return {
        'intent': intent,
        'params': parsed.get('params') or {},
        'human_reply': (parsed.get('human_reply') or '').strip() or 'Ok, chalte hain!',
        'raw': raw[:2000] if raw else '',
    }


def _parse(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}
    s = raw.find('{'); e = raw.rfind('}')
    if s == -1:
        return {}
    try:
        return json.loads(raw[s:e + 1])
    except Exception:
        return {}
