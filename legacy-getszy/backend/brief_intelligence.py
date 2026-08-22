"""Getszy Brief Intelligence v3.

A strict no-hallucination extraction layer used before managed website composition.
The model proposes JSON; this module validates its shape and removes values that
are not directly supported by the customer's natural-language command.
"""
from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from llm_provider import professional_builder_completion


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Contact(_StrictModel):
    phone: str | None = None
    email: str | None = None
    whatsapp: str | None = None
    website: str | None = None


class SocialLinks(_StrictModel):
    instagram: str | None = None
    facebook: str | None = None
    youtube: str | None = None


class DesignDirection(_StrictModel):
    style: str | None = None
    colors: list[str] = Field(default_factory=list, max_length=8)


class BriefIntelligenceV3(_StrictModel):
    request_type: Literal['create'] = 'create'
    business_name: str | None = None
    business_type: str | None = None
    location: str | None = None
    target_audience: list[str] = Field(default_factory=list, max_length=12)
    services_or_products: list[str] = Field(default_factory=list, max_length=20)
    design_direction: DesignDirection = Field(default_factory=DesignDirection)
    primary_goal: str | None = None
    cta: str | None = None
    languages: list[str] = Field(default_factory=list, max_length=8)
    contact: Contact = Field(default_factory=Contact)
    social_links: SocialLinks = Field(default_factory=SocialLinks)
    requested_pages: list[str] = Field(default_factory=list, max_length=16)
    functional_requirements: list[str] = Field(default_factory=list, max_length=20)
    specific_features: list[str] = Field(default_factory=list, max_length=20)
    approved_facts: list[str] = Field(default_factory=list, max_length=30)


class BriefIntelligenceError(ValueError):
    """Raised when managed extraction does not produce a valid safe brief."""


BRIEF_INTELLIGENCE_V3_PROMPT = """You are Getszy Brief Intelligence v3, a strict no-hallucination data extractor for production websites.

Your only job is to convert the customer natural-language command into one valid JSON object. Never invent, assume, strengthen, weaken, or add information.

Rules:
- Preserve explicit contact values and social URLs exactly. Never copy phone into WhatsApp. Never construct contact or social values.
- approved_facts contains only explicit factual claims, normalized only for spelling/grammar without changing meaning.
- services_or_products may contain explicitly mentioned services or products, but do not turn them into extra claims.
- business_type only when directly and unambiguously stated. Do not infer e-commerce from a product name.
- target_audience only when explicitly mentioned. Beauty salon alone has no target audience; "women ke liye salon" may include Women.
- primary_goal only when explicit intent supports it: admission/admissions supports Admissions; booking supports Bookings; sale/shop/buy supports Sales; lead/enquiry supports Leads; branding/design/style alone does not imply Branding.
- cta only when explicitly requested. Never invent it from a goal.
- requested_pages and functional_requirements only contain explicitly requested pages or functionality.
- If a customer corrects a value, use the latest explicit value.
- Empty values must be null or []. request_type is always create.

Output only JSON with exactly these keys:
{
  "request_type":"create",
  "business_name":null,
  "business_type":null,
  "location":null,
  "target_audience":[],
  "services_or_products":[],
  "design_direction":{"style":null,"colors":[]},
  "primary_goal":null,
  "cta":null,
  "languages":[],
  "contact":{"phone":null,"email":null,"whatsapp":null,"website":null},
  "social_links":{"instagram":null,"facebook":null,"youtube":null},
  "requested_pages":[],
  "functional_requirements":[],
  "specific_features":[],
  "approved_facts":[]
}
"""


def _extract_json(raw: str) -> dict:
    raw = (raw or '').strip()
    start, end = raw.find('{'), raw.rfind('}')
    if start < 0 or end <= start:
        raise BriefIntelligenceError('Managed extraction did not return JSON.')
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError as exc:
        raise BriefIntelligenceError('Managed extraction returned invalid JSON.') from exc


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", (value or '').lower()) if len(token) > 1}


def _supported(value: str | None, raw: str, minimum_ratio: float = 0.72) -> bool:
    """Conservative lexical support check that permits small grammar normalization."""
    value = (value or '').strip()
    if not value:
        return False
    raw_lower = raw.lower()
    if value.lower() in raw_lower:
        return True
    value_tokens = _tokens(value)
    if not value_tokens:
        return False
    raw_tokens = _tokens(raw)
    return len(value_tokens & raw_tokens) / len(value_tokens) >= minimum_ratio


def _exact_contact_supported(value: str | None, raw: str) -> bool:
    if not value:
        return False
    compact_value = re.sub(r"[^a-z0-9]", '', value.lower())
    compact_raw = re.sub(r"[^a-z0-9]", '', raw.lower())
    return bool(compact_value) and compact_value in compact_raw


def _filter_list(values: list[str], raw: str) -> list[str]:
    return [value for value in values if _supported(value, raw)]


def _approved_fact_supported(value: str, raw: str) -> bool:
    """Allow minor grammar normalization, never a stronger claim."""
    lower_value, lower_raw = value.lower(), raw.lower()
    strengthening = ('happy', 'best', 'top', 'leading', 'trusted', 'award-winning', 'unbeatable')
    if '+' in value and '+' not in raw:
        return False
    if any(term in lower_value and term not in lower_raw for term in strengthening):
        return False
    return _supported(value, raw, minimum_ratio=0.55)


def _whatsapp_is_explicit(value: str | None, raw: str) -> bool:
    """Never infer WhatsApp from a phone number that merely appears in the command."""
    if not _exact_contact_supported(value, raw):
        return False
    label = re.search(r'\b(?:whats\s*app|wa)\b', raw, re.IGNORECASE)
    if not label:
        return False
    # Require the explicit WhatsApp label to be near the supplied value, avoiding
    # a separate phone number being silently copied into the WhatsApp field.
    start = max(0, label.start() - 48)
    end = min(len(raw), label.end() + 96)
    return _exact_contact_supported(value, raw[start:end])


def _goal_is_explicit(goal: str | None, raw: str) -> bool:
    if not goal:
        return False
    raw_lower = raw.lower()
    required_terms = {
        'Admissions': ('admission', 'admissions', 'enrol', 'enroll'),
        'Bookings': ('book', 'booking', 'appointment', 'reserve'),
        'Sales': ('sale', 'sell', 'shop', 'buy', 'purchase', 'order'),
        'Leads': ('lead', 'enquiry', 'inquiry', 'inquire'),
        'Information': ('information', 'info', 'details'),
        'Branding': ('branding', 'brand identity'),
    }
    terms = required_terms.get(goal)
    return _supported(goal, raw) if terms is None else any(term in raw_lower for term in terms)


def validate_and_sanitize_brief(payload: dict, raw_command: str) -> BriefIntelligenceV3:
    """Reject extra/wrong JSON shapes and clear unsupported inferred values."""
    try:
        brief = BriefIntelligenceV3.model_validate(payload)
    except ValidationError as exc:
        raise BriefIntelligenceError('Brief JSON does not match the required schema.') from exc

    updates: dict = {}
    for key in ('business_name', 'business_type', 'location', 'cta'):
        value = getattr(brief, key)
        updates[key] = value if _supported(value, raw_command) else None

    updates['target_audience'] = _filter_list(brief.target_audience, raw_command)
    updates['services_or_products'] = _filter_list(brief.services_or_products, raw_command)
    updates['languages'] = _filter_list(brief.languages, raw_command)
    updates['requested_pages'] = _filter_list(brief.requested_pages, raw_command)
    updates['functional_requirements'] = _filter_list(brief.functional_requirements, raw_command)
    updates['specific_features'] = _filter_list(brief.specific_features, raw_command)
    updates['approved_facts'] = [
        value for value in brief.approved_facts if _approved_fact_supported(value, raw_command)
    ]
    updates['primary_goal'] = brief.primary_goal if _goal_is_explicit(brief.primary_goal, raw_command) else None

    style = brief.design_direction.style
    colors = _filter_list(brief.design_direction.colors, raw_command)
    updates['design_direction'] = DesignDirection(
        style=style if _supported(style, raw_command) else None,
        colors=colors,
    )

    contact = {}
    for key, value in brief.contact.model_dump().items():
        if key == 'whatsapp':
            contact[key] = value if _whatsapp_is_explicit(value, raw_command) else None
        else:
            contact[key] = value if _exact_contact_supported(value, raw_command) else None
    updates['contact'] = Contact(**contact)

    socials = {}
    for key, value in brief.social_links.model_dump().items():
        socials[key] = value if _exact_contact_supported(value, raw_command) else None
    updates['social_links'] = SocialLinks(**socials)
    return brief.model_copy(update=updates)


def merge_latest_explicit_brief(previous: BriefIntelligenceV3 | None, latest: BriefIntelligenceV3) -> BriefIntelligenceV3:
    """Latest explicit values win; empty latest fields never erase known facts."""
    if previous is None:
        return latest
    merged = previous.model_dump()
    for key, value in latest.model_dump().items():
        if key in ('request_type',):
            continue
        if isinstance(value, dict):
            merged[key] = {**merged.get(key, {}), **{k: v for k, v in value.items() if v not in (None, [])}}
        elif value not in (None, []):
            merged[key] = value
    return BriefIntelligenceV3.model_validate(merged)


def composition_context(brief: BriefIntelligenceV3, customer_brief: dict | None = None) -> dict:
    """Build the only facts/context allowed into the page-composition prompt."""
    customer_brief = customer_brief or {}
    return {
        'brief_intelligence_v3': brief.model_dump(),
        'brand_name': customer_brief.get('brand_name') or brief.business_name,
        'audience': customer_brief.get('audience') or ', '.join(brief.target_audience),
        'primary_goal': customer_brief.get('primary_goal') or brief.primary_goal,
        'primary_cta': customer_brief.get('primary_cta') or brief.cta,
        'visual_style': customer_brief.get('visual_style') or brief.design_direction.style,
        'offer': customer_brief.get('offer') or '; '.join(brief.services_or_products),
        'proof_points': list(customer_brief.get('proof_points') or []) + list(brief.approved_facts),
        'contact': brief.contact.model_dump(),
        'social_links': brief.social_links.model_dump(),
        'requested_pages': brief.requested_pages,
        'functional_requirements': brief.functional_requirements,
    }


async def extract_brief_v3(raw_command: str, session_id: str = 'brief') -> BriefIntelligenceV3:
    raw = await professional_builder_completion(
        system=BRIEF_INTELLIGENCE_V3_PROMPT,
        user=f'CUSTOMER NATURAL COMMAND:\n{raw_command}',
        session_id=f'{session_id}-brief-v3',
        temperature=0,
        max_tokens=1800,
    )
    return validate_and_sanitize_brief(_extract_json(raw), raw_command)


__all__ = [
    'BriefIntelligenceError', 'BriefIntelligenceV3', 'composition_context',
    'extract_brief_v3', 'merge_latest_explicit_brief', 'validate_and_sanitize_brief',
]
