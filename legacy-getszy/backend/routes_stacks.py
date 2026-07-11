"""YAML Campaign Stacks routes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timezone

from auth import get_current_admin
from db import db
from stacks.executor import parse, execute

router = APIRouter(prefix='/admin/stacks', tags=['stacks'])


class StackIn(BaseModel):
    yaml: str
    save: bool = True


class StackUpdate(BaseModel):
    yaml: str


@router.get('')
async def list_stacks(_=Depends(get_current_admin)):
    cur = db.campaign_stacks.find({}, {'_id': 0}).sort('updated_at', -1)
    return {'items': [doc async for doc in cur]}


@router.post('/parse')
async def parse_stack(payload: StackIn, _=Depends(get_current_admin)):
    try:
        data = parse(payload.yaml)
        return {'ok': True, 'parsed': data, 'step_count': len(data.get('steps', []) or [])}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post('/save')
async def save_stack(payload: StackIn, admin=Depends(get_current_admin)):
    try:
        data = parse(payload.yaml)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    sid = str(uuid.uuid4())
    doc = {
        'id': sid,
        'name': data['name'],
        'yaml': payload.yaml,
        'parsed': data,
        'admin_id': admin['id'],
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.campaign_stacks.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.put('/{stack_id}')
async def update_stack(stack_id: str, payload: StackUpdate, _=Depends(get_current_admin)):
    try:
        data = parse(payload.yaml)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    update = {'yaml': payload.yaml, 'parsed': data, 'name': data['name'], 'updated_at': datetime.now(timezone.utc).isoformat()}
    r = await db.campaign_stacks.update_one({'id': stack_id}, {'$set': update})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail='Stack not found')
    return {'ok': True}


@router.delete('/{stack_id}')
async def delete_stack(stack_id: str, _=Depends(get_current_admin)):
    r = await db.campaign_stacks.delete_one({'id': stack_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Stack not found')
    return {'ok': True}


@router.post('/{stack_id}/run')
async def run_stack(stack_id: str, admin=Depends(get_current_admin)):
    doc = await db.campaign_stacks.find_one({'id': stack_id}, {'_id': 0})
    if not doc:
        raise HTTPException(status_code=404, detail='Stack not found')
    result = await execute(doc['parsed'], admin)
    record = {**result, 'stack_id': stack_id, 'admin_id': admin['id']}
    await db.stack_runs.insert_one(record)
    record.pop('_id', None)
    return record


@router.post('/run-once')
async def run_once(payload: StackIn, admin=Depends(get_current_admin)):
    """Parse + execute without saving — for quick experiments."""
    try:
        data = parse(payload.yaml)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return await execute(data, admin)


@router.get('/runs/recent')
async def recent_runs(limit: int = 20, _=Depends(get_current_admin)):
    cur = db.stack_runs.find({}, {'_id': 0}).sort('started_at', -1).limit(limit)
    return {'items': [doc async for doc in cur]}


# ── Seed pre-built templates ──────────────────────────────────────────────────

TEMPLATE_YAMLS = [
    (
        "Diwali Sale Campaign",
        """name: "Diwali Sale Campaign 2026"
description: "Curate trending Diwali products, enforce 40% margin, generate brand hero image."
audience: [women, girls, kids]

steps:
  - skill: scan_trending
    params: { count: 12 }

  - skill: import_trending
    params: { count: 6, min_score: 80 }

  - skill: enforce_margins
    params: { dry_run: false }

  - skill: generate_hero_image
    params:
      prompt: "festive diwali sale banner with marigold flowers and diyas, warm golden tones"
      style: cinematic

  - skill: ai_insights
"""
    ),
    (
        "Women Fashion Launch",
        """name: "Women Fashion Launch"
description: "Find trending women fashion products, import top picks, generate collection banner."
audience: [women]

steps:
  - skill: scan_trending
    params: { count: 8 }

  - skill: import_trending
    params: { count: 4, min_score: 78 }

  - skill: generate_hero_image
    params:
      prompt: "elegant Indian women fashion collection, ethnic wear, pastel background"
      style: editorial
"""
    ),
    (
        "Kids Store Refresh",
        """name: "Kids Store Refresh"
description: "Weekly refresh of kids section with trending picks and safety-checked imports."
audience: [kids]

steps:
  - skill: scan_trending
    params: { count: 10 }

  - skill: import_trending
    params: { count: 5, min_score: 75 }

  - skill: ai_insights
"""
    ),
    (
        "AI Content Blitz",
        """name: "AI Content Blitz"
description: "Generate a viral script + hero image + AI insights for weekly social push."
audience: [women, girls]

steps:
  - skill: generate_hero_image
    params:
      prompt: "modern Indian lifestyle brand, vibrant colors, young women shopping online"
      style: vibrant

  - skill: ai_insights
"""
    ),
    (
        "Margin Health Check",
        """name: "Margin Health Check"
description: "Audit all products and enforce 40% minimum margin floor across catalog."
audience: []

steps:
  - skill: enforce_margins
    params: { dry_run: false }

  - skill: ai_insights
"""
    ),
    (
        "Weekly Store Intelligence",
        """name: "Weekly Store Intelligence"
description: "Every Monday — scan trends, check margins, generate AI business insights."
audience: [women, girls, kids]

steps:
  - skill: scan_trending
    params: { count: 12 }

  - skill: enforce_margins
    params: { dry_run: true }

  - skill: ai_insights
"""
    ),
]


@router.post('/seed-templates', dependencies=[Depends(get_current_admin)])
async def seed_templates():
    """Seed pre-built campaign stack templates into the DB (skips existing by name)."""
    seeded = []
    skipped = []
    for name, yaml_text in TEMPLATE_YAMLS:
        existing = await db.campaign_stacks.find_one({'name': name})
        if existing:
            skipped.append(name)
            continue
        try:
            data = parse(yaml_text)
        except Exception as e:
            skipped.append(f'{name} (parse error: {e})')
            continue
        sid = str(uuid.uuid4())
        doc = {
            'id': sid,
            'name': name,
            'yaml': yaml_text,
            'parsed': data,
            'admin_id': 'system',
            'is_template': True,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.campaign_stacks.insert_one(doc)
        seeded.append(name)
    return {'seeded': seeded, 'skipped': skipped, 'total': len(TEMPLATE_YAMLS)}
