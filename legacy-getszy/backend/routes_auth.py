import re
import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Request
from db import db
from models import SignupIn, LoginIn, User, UserOut, ProfileUpdate, PasswordChange
from auth import hash_password, verify_password, create_token, get_current_user
from live_events import broadcast_admin_event
from anomaly import record_login_failure

router = APIRouter(prefix='/auth', tags=['auth'])

REFERRAL_REWARD = int(os.getenv('REFERRAL_REWARD_CREDITS', '50'))
FRONTEND_URL = os.getenv('FRONTEND_URL', 'https://getszy.com')


def _gen_referral_code(name: str) -> str:
    base = re.sub(r'[^a-zA-Z0-9]', '', (name or 'user'))[:5].upper() or 'USER'
    return f"GS{base}{uuid.uuid4().hex[:4].upper()}"


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
        referral_code=_gen_referral_code(body.name),
    )
    # Attribute referral (real reward credited to referrer)
    referrer = None
    if body.ref:
        ref_code = body.ref.strip().upper()
        if ref_code:
            referrer = await db.users.find_one({'referral_code': ref_code}, {'_id': 0})
            if referrer and referrer['id'] != user.id:
                user.referred_by = referrer['id']
                await db.users.update_one(
                    {'id': referrer['id']},
                    {'$inc': {'credits': REFERRAL_REWARD, 'referral_rewards': REFERRAL_REWARD}},
                )
                try:
                    await db.referrals.insert_one({
                        'id': uuid.uuid4().hex,
                        'referrer_id': referrer['id'],
                        'referred_user_id': user.id,
                        'code': ref_code,
                        'reward_credits': REFERRAL_REWARD,
                        'status': 'credited',
                        'created_at': datetime.now(timezone.utc).isoformat(),
                    })
                except Exception:
                    pass
    await db.users.insert_one(user.model_dump())
    token = create_token(user.id, user.role)
    try:
        broadcast_admin_event('user_signup', {'email': body.email, 'name': body.name})
    except Exception:
        pass
    return {'token': token, 'user': UserOut(**user.model_dump()).model_dump()}


@router.get('/referrals')
async def my_referrals(user=Depends(get_current_user)):
    """Self-serve referral dashboard for the logged-in user."""
    code = user.get('referral_code')
    if not code:
        code = _gen_referral_code(user.get('name', 'user'))
        try:
            await db.users.update_one({'id': user['id']}, {'$set': {'referral_code': code}})
        except Exception:
            pass
    referred = []
    total = 0
    rewards = 0
    try:
        cur = db.referrals.find({'referrer_id': user['id']}, {'_id': 0}).sort('created_at', -1)
        async for r in cur:
            total += 1
            rewards += int(r.get('reward_credits', 0) or 0)
            referred_user = await db.users.find_one({'id': r.get('referred_user_id')}, {'_id': 0, 'name': 1, 'email': 1, 'created_at': 1})
            referred.append({
                'name': (referred_user or {}).get('name', 'New member'),
                'email': (referred_user or {}).get('email', ''),
                'reward_credits': r.get('reward_credits', 0),
                'status': r.get('status', 'credited'),
                'created_at': r.get('created_at'),
            })
    except Exception:
        pass
    return {
        'referral_code': code,
        'referral_link': f"{FRONTEND_URL}/signup?ref={code}",
        'total_referred': total,
        'rewards_earned': rewards or int(user.get('referral_rewards', 0) or 0),
        'referred': referred,
    }


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
            await record_login_failure(ip, body.email)
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


@router.put('/me')
async def update_me(body: ProfileUpdate, user=Depends(get_current_user)):
    update = {}
    if body.name is not None and body.name.strip():
        update['name'] = body.name.strip()
    if body.phone is not None:
        update['phone'] = body.phone
    if not update:
        raise HTTPException(status_code=400, detail='Nothing to update')
    await db.users.update_one({'id': user['id']}, {'$set': update})
    updated = await db.users.find_one({'id': user['id']})
    return await me(updated)


@router.post('/me/password')
async def change_password(body: PasswordChange, user=Depends(get_current_user)):
    if not verify_password(body.current_password, user['password_hash']):
        raise HTTPException(status_code=400, detail='Current password is incorrect')
    _validate_password(body.new_password)
    await db.users.update_one(
        {'id': user['id']},
        {'$set': {'password_hash': hash_password(body.new_password)}},
    )
    return {'ok': True}
