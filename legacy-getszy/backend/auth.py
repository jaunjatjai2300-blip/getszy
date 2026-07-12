import os
import secrets
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from db import db, serialize_doc

JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET or JWT_SECRET == 'change-me':
    JWT_SECRET = secrets.token_hex(32)
JWT_ALG = 'HS256'
JWT_EXP_DAYS = 30

bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def create_token(user_id: str, role: str) -> str:
    payload = {
        'sub': user_id,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(days=JWT_EXP_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if not creds:
        raise HTTPException(status_code=401, detail='Not authenticated')
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid or expired token')
    user = await db.users.find_one({'id': payload['sub']}, {'_id': 0})
    if not user:
        raise HTTPException(status_code=401, detail='User not found')
    return user


async def get_current_admin(user=Depends(get_current_user)):
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Admin only')
    return user


# ------------------------------------------------------------
# Role hierarchy (Phase 18 \u2014 Neo as Platform OS)
# visitor < customer < founder < admin
# Any role has all abilities of the lower roles.
# ------------------------------------------------------------
ROLE_LEVEL = {'visitor': 0, 'customer': 1, 'founder': 2, 'admin': 3}


def role_level(user: dict | None) -> int:
    return ROLE_LEVEL.get((user or {}).get('role', 'visitor'), 0)


def user_has_role(user: dict | None, min_role: str) -> bool:
    return role_level(user) >= ROLE_LEVEL.get(min_role, 0)


async def get_current_founder(user=Depends(get_current_user)):
    if not user_has_role(user, 'founder'):
        raise HTTPException(status_code=403, detail='Founder or admin only')
    return user


async def get_current_customer(user=Depends(get_current_user)):
    if not user_has_role(user, 'customer'):
        raise HTTPException(status_code=403, detail='Sign up required')
    return user


async def get_optional_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if not creds:
        return None
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        return None
    return await db.users.find_one({'id': payload['sub']}, {'_id': 0})
