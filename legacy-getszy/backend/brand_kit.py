"""Brand Memory — per-customer brand profile reused across every generation.

This is the moat: competitors make you re-brief on every asset. We persist the
brand (name, industry, colors, fonts, tone, USP, logo, audience) once and inject
it into every architect call so output is always on-brand without re-typing.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from db import db


async def get_brand(user_id: str) -> Optional[Dict[str, Any]]:
    return await db.brand_kits.find_one({'user_id': user_id}, {'_id': 0})


async def save_brand(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    data = {k: v for k, v in data.items() if v not in (None, '', [], {})}
    data['user_id'] = user_id
    data['updated_at'] = datetime.now(timezone.utc).isoformat()
    await db.brand_kits.update_one({'user_id': user_id}, {'$set': data}, upsert=True)
    return await get_brand(user_id)


def brand_block(brand: Optional[Dict[str, Any]]) -> str:
    if not brand:
        return ''
    parts = []
    if brand.get('name'):
        parts.append(f"Brand: {brand['name']}")
    if brand.get('industry'):
        parts.append(f"Industry: {brand['industry']}")
    if brand.get('tagline'):
        parts.append(f"Tagline: {brand['tagline']}")
    if brand.get('usp'):
        parts.append(f"Unique Selling Proposition: {brand['usp']}")
    if brand.get('audience'):
        parts.append(f"Target audience: {brand['audience']}")
    if brand.get('tone'):
        parts.append(f"Tone of voice: {brand['tone']}")
    colors = brand.get('colors')
    if colors:
        parts.append('Brand colors: ' + (', '.join(colors) if isinstance(colors, list) else str(colors)))
    if brand.get('fonts'):
        parts.append(f"Preferred fonts: {brand['fonts']}")
    if brand.get('logo_url'):
        parts.append(f"Logo URL: {brand['logo_url']}")
    if brand.get('social'):
        parts.append(f"Social handles: {brand['social']}")
    if brand.get('forbidden'):
        parts.append(f"Avoid using: {brand['forbidden']}")
    if not parts:
        return ''
    return "BRAND KIT (strictly follow for every decision — colors, tone, naming, CTA):\n- " + "\n- ".join(parts)
