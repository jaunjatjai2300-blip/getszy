"""Automation rules CRUD (Tier 2 #11)."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Optional

from auth import get_current_admin
from db import db
from automation_engine import match_rule, evaluate_condition

router = APIRouter(prefix='/admin/automations', tags=['automations'])

AVAILABLE_TRIGGERS = [
    'order_created', 'refund_issued', 'user_signup', 'failed_login',
    'ip_blocked', 'low_stock',
]
AVAILABLE_ACTIONS = ['notify', 'webhook', 'tag', 'log']


class ConditionIn(BaseModel):
    field: str
    op: str = '=='
    value: Any = ''


class ActionIn(BaseModel):
    type: str
    title: Optional[str] = None
    message: Optional[str] = None
    target_user: Optional[str] = None
    type_notif: Optional[str] = None
    url: Optional[str] = None
    tag: Optional[str] = None
    note: Optional[str] = None


class RuleIn(BaseModel):
    name: str
    trigger: str
    enabled: bool = True
    match: str = 'all'
    conditions: list[ConditionIn] = []
    actions: list[ActionIn] = []


@router.get('/triggers')
async def triggers(_=Depends(get_current_admin)):
    return {'triggers': AVAILABLE_TRIGGERS, 'actions': AVAILABLE_ACTIONS}


@router.get('/logs')
async def automation_logs(limit: int = 50, _=Depends(get_current_admin)):
    cur = db.automation_logs.find({}, {'_id': 0}).sort('ts', -1).limit(limit)
    items = [l async for l in cur]
    return {'items': items}


@router.get('/')
async def list_rules(_=Depends(get_current_admin)):
    cur = db.automations.find({}, {'_id': 0}).sort('created_at', -1)
    items = [r async for r in cur]
    return {'items': items, 'total': len(items)}


@router.post('/')
async def create_rule(body: RuleIn, _=Depends(get_current_admin)):
    if body.trigger not in AVAILABLE_TRIGGERS:
        raise HTTPException(400, f"Unknown trigger '{body.trigger}'")
    doc = body.model_dump()
    doc['id'] = __import__('uuid').uuid4().hex
    doc['created_at'] = datetime.now(timezone.utc).isoformat()
    await db.automations.insert_one(doc)
    doc.pop('_id', None)
    return {'ok': True, 'rule': doc}


@router.put('/{rule_id}')
async def update_rule(rule_id: str, body: RuleIn, _=Depends(get_current_admin)):
    update = body.model_dump()
    update['updated_at'] = datetime.now(timezone.utc).isoformat()
    res = await db.automations.update_one({'id': rule_id}, {'$set': update})
    if res.matched_count == 0:
        raise HTTPException(404, 'Rule not found')
    return {'ok': True}


@router.delete('/{rule_id}')
async def delete_rule(rule_id: str, _=Depends(get_current_admin)):
    await db.automations.delete_one({'id': rule_id})
    return {'ok': True}


@router.post('/test')
async def test_rule(body: RuleIn, _=Depends(get_current_admin)):
    """Dry-run: show whether a sample payload would match (no actions run)."""
    sample = body.model_dump()
    sample_payload = {
        'order_number': 'ORD-TEST', 'total': 9999, 'amount': 500,
        'email': 'test@example.com', 'ip': '1.2.3.4', 'name': 'Test',
        'customer': 'Test',
    }
    rule = body.model_dump()
    rule['id'] = 'test'
    matched = match_rule(rule, body.trigger, sample_payload)
    cond_eval = [
        {**c, 'matched': evaluate_condition(c, sample_payload)}
        for c in body.conditions
    ]
    return {'would_match': matched, 'condition_eval': cond_eval}
