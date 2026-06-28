"""Waitlist capture for Reels Studio (and any other future launches)."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional

from db import db

router = APIRouter(prefix='/waitlist', tags=['waitlist'])


class WaitlistIn(BaseModel):
    email: str
    interest: Optional[str] = 'general'
    source: Optional[str] = None


@router.post('')
async def join(payload: WaitlistIn):
    email = (payload.email or '').strip().lower()
    if '@' not in email or len(email) < 5:
        raise HTTPException(status_code=400, detail='Invalid email')
    existing = await db.waitlist.find_one({'email': email, 'interest': payload.interest}, {'_id': 0})
    if existing:
        return {'ok': True, 'status': 'already_subscribed', 'id': existing.get('id')}
    doc = {
        'id': str(uuid.uuid4()),
        'email': email,
        'interest': payload.interest or 'general',
        'source': payload.source,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.waitlist.insert_one(doc)
    return {'ok': True, 'status': 'subscribed', 'id': doc['id']}


@router.get('/count')
async def count(interest: Optional[str] = None):
    q = {'interest': interest} if interest else {}
    n = await db.waitlist.count_documents(q)
    return {'count': n, 'interest': interest or 'all'}
