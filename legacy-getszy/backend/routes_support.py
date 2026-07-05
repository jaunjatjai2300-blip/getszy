"""Support & Feedback: FAQ (static), Contact tickets, Feature request voting."""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth import get_current_user, get_current_admin
from db import db

router = APIRouter(prefix='/support', tags=['support'])


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- FAQ (static) ----------
FAQ = [
    {'q': 'Neo kaise use karun?', 'a': 'Bas /dashboard pe jao aur ek plain-language request bhejo, jaise "write a reel script on AI tools" ya "build a landing page for a bakery". Neo automatic decide karega ki kaunsa tool use karna hai.'},
    {'q': 'Free plan mein kya milta hai?', 'a': 'Beginner + Intermediate Academy courses, AI Tutor, storefront browsing, aur Neo chat ka read-only preview. Studio builds ke liye Pro chahiye.'},
    {'q': 'Kya mera data safe hai?', 'a': 'Haan. Sab data India ke DPDP Act 2023 compliance ke saath store hota hai. Aap kabhi bhi Account → Data Export se apna sab data ZIP mein download kar sakte ho.'},
    {'q': 'Videos kitne time mein banti hain?', 'a': 'Faceless videos ~60-120 seconds mein render hoti hain (topic + voice + visuals). Batch mode mein 10 videos ek saath queue hote hain.'},
    {'q': 'Kya webapp deploy hoke live jata hai?', 'a': 'Haan. Workspace → Deploy tab se `<slug>.getszy.com` par one-click hosting available hai. Custom domain support jaldi aa raha hai.'},
    {'q': 'Payment kaise hoga?', 'a': 'Razorpay ke through — UPI, cards, netbanking, wallets sab support hain. GST invoice available hai on request.'},
    {'q': 'Cancel kaise karun?', 'a': 'Account → Billing → Cancel Subscription. Aap current period ke end tak use kar sakte ho, phir automatic free plan pe move ho jayenge.'},
    {'q': 'Neo galti kar gaya to?', 'a': 'Har asset ke Workspace → Versions tab se aap snapshot kar sakte ho. Support ticket bhi bhej sakte ho — Feature Requests aur Bug Reports dono welcome hain.'},
]


@router.get('/faq')
async def faq():
    return {'items': FAQ}


# ---------- Support tickets ----------
class TicketIn(BaseModel):
    subject: str = Field(..., min_length=3, max_length=200)
    category: str = 'general'  # general | bug | billing | feature | other
    body: str = Field(..., min_length=8, max_length=4000)


@router.post('/ticket')
async def create_ticket(body: TicketIn, user=Depends(get_current_user)):
    doc = {
        'id': str(uuid.uuid4()),
        'user_id': user['id'],
        'user_email': user.get('email'),
        'subject': body.subject.strip(),
        'category': body.category,
        'body': body.body.strip(),
        'status': 'open',
        'created_at': _iso(),
        'updated_at': _iso(),
    }
    await db.support_tickets.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.get('/tickets')
async def my_tickets(user=Depends(get_current_user)):
    items = [t async for t in db.support_tickets.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(50)]
    return {'items': items}


# Admin-only: view all tickets + update status
@router.get('/tickets/all')
async def all_tickets(status: Optional[str] = None, _=Depends(get_current_admin)):
    q = {}
    if status:
        q['status'] = status
    items = [t async for t in db.support_tickets.find(q, {'_id': 0}).sort('created_at', -1).limit(200)]
    return {'items': items}


class TicketPatch(BaseModel):
    status: Optional[str] = None  # open | in_progress | resolved | closed
    reply: Optional[str] = None


@router.patch('/tickets/{ticket_id}')
async def update_ticket(ticket_id: str, body: TicketPatch, _=Depends(get_current_admin)):
    upd = {'updated_at': _iso()}
    if body.status:
        upd['status'] = body.status
    if body.reply:
        upd['admin_reply'] = body.reply
        upd['replied_at'] = _iso()
    r = await db.support_tickets.update_one({'id': ticket_id}, {'$set': upd})
    if r.matched_count == 0:
        raise HTTPException(404, 'ticket not found')
    doc = await db.support_tickets.find_one({'id': ticket_id}, {'_id': 0})
    return doc


# ---------- Feature Requests (like Canny) ----------
class FeatureIn(BaseModel):
    title: str = Field(..., min_length=4, max_length=180)
    description: Optional[str] = Field(None, max_length=2000)


@router.post('/features')
async def create_feature(body: FeatureIn, user=Depends(get_current_user)):
    doc = {
        'id': str(uuid.uuid4()),
        'user_id': user['id'],
        'author_name': user.get('name'),
        'title': body.title.strip(),
        'description': (body.description or '').strip(),
        'status': 'open',  # open | planned | in_progress | shipped | declined
        'vote_count': 1,
        'voters': [user['id']],
        'created_at': _iso(),
        'updated_at': _iso(),
    }
    await db.feature_requests.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.get('/features')
async def list_features(
    status: Optional[str] = None,
    sort: str = Query('votes', pattern='^(votes|new)$'),
):
    q = {}
    if status:
        q['status'] = status
    sort_key = 'vote_count' if sort == 'votes' else 'created_at'
    items = [f async for f in db.feature_requests.find(q, {'_id': 0, 'voters': 0}).sort(sort_key, -1).limit(100)]
    return {'items': items}


@router.post('/features/{feature_id}/vote')
async def vote_feature(feature_id: str, user=Depends(get_current_user)):
    doc = await db.feature_requests.find_one({'id': feature_id}, {'_id': 0, 'voters': 1})
    if not doc:
        raise HTTPException(404, 'not found')
    voters = doc.get('voters') or []
    already = user['id'] in voters
    if already:
        await db.feature_requests.update_one({'id': feature_id}, {'$pull': {'voters': user['id']}, '$inc': {'vote_count': -1}, '$set': {'updated_at': _iso()}})
        return {'voted': False, 'delta': -1}
    else:
        await db.feature_requests.update_one({'id': feature_id}, {'$addToSet': {'voters': user['id']}, '$inc': {'vote_count': 1}, '$set': {'updated_at': _iso()}})
        return {'voted': True, 'delta': +1}


class FeaturePatch(BaseModel):
    status: Optional[str] = None
    admin_note: Optional[str] = None


@router.patch('/features/{feature_id}')
async def admin_update_feature(feature_id: str, body: FeaturePatch, _=Depends(get_current_admin)):
    upd = {'updated_at': _iso()}
    if body.status:
        upd['status'] = body.status
    if body.admin_note:
        upd['admin_note'] = body.admin_note
    r = await db.feature_requests.update_one({'id': feature_id}, {'$set': upd})
    if r.matched_count == 0:
        raise HTTPException(404, 'not found')
    doc = await db.feature_requests.find_one({'id': feature_id}, {'_id': 0, 'voters': 0})
    return doc
