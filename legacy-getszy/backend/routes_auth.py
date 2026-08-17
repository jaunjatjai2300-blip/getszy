import re
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from db import db
from models import SignupIn, LoginIn, User, UserOut
from auth import hash_password, verify_password, create_token, get_current_user
from live_events import broadcast_admin_event

router = APIRouter(prefix='/auth', tags=['auth'])


def _validate_password(password: str):
    if len(password) < 8:
        raise HTTPException(400, 'Password must be at least 8 characters')
    if not re.search(r'[A-Z]', password):
        raise HTTPException(400, 'Password must contain at least one uppercase letter')
    if not re.search(r'[a-z]', password):
        raise HTTPException(400, 'Password must contain at least one lowercase letter')
    if not re.search(r'[0-9]', password):
        raise HTTPException(400, 'Password must contain at least one digit')


@router.post('/signup')
async def signup(body: SignupIn):
    _validate_password(body.password)
    existing = await db.users.find_one({'email': body.email.lower()})
    if existing:
        raise HTTPException(400, 'Email already registered')
    user = User(
        name=body.name,
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        phone=body.phone,
        role='customer',
    )
    await db.users.insert_one(user.model_dump())
    token = create_token(user.id, user.role)
    try:
        broadcast_admin_event('user_signup', {'email': body.email, 'name': body.name})
    except Exception:
        pass
    return {'token': token, 'user': UserOut(**user.model_dump()).model_dump()}


@router.post('/login')
async def login(body: LoginIn, request: Request = None):
    user = await db.users.find_one({'email': body.email.lower()}, {'_id': 0})
    if not user or not verify_password(body.password, user['password_hash']):
        ip = request.client.host if request and request.client else 'unknown'
        try:
            await db.audit_logs.insert_one({
                'id': uuid.uuid4().hex,
                'action': 'failed_login',
                'email': body.email,
                'ip': ip,
                'source': ip,
                'detail': 'Invalid email or password',
                'ts': datetime.now(timezone.utc).isoformat(),
            })
            broadcast_admin_event('failed_login', {'email': body.email, 'ip': ip})
        except Exception:
            pass
        raise HTTPException(401, 'Invalid email or password')
    token = create_token(user['id'], user['role'])
    return {'token': token, 'user': UserOut(**user).model_dump()}


@router.get('/me')
async def me(user=Depends(get_current_user)):
    from subscription import effective_subscription, plan_features
    sub = await effective_subscription(user)
    out = UserOut(**user).model_dump()
    out['subscription'] = {**sub, 'quota': plan_features(sub['plan'])}
    out['credits'] = int(user.get('credits', 0) or 0)
    return out
