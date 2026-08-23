import os
import uuid
import asyncio
import bcrypt
import jwt
import math
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from db import db, serialize_doc
from redis_client import redis

# ── Secret strength validation ────────────────────────────────────────────────
# Guards every security-critical secret this app reads from the environment
# (JWT signing key, integration-credential encryption key, ...) against the
# single most common way these leak: an operator copies `.env.example` and
# never replaces the placeholder. The previous version of this check only
# rejected generic words like 'change-me' and missed the actual placeholder
# shipped in `.env.example` (`CHANGE_ME_TO_RANDOM_64_CHAR_STRING`) — meaning
# the app would boot silently with a secret that is public in the repo.
_KNOWN_PLACEHOLDER_SECRETS = {
    'change-me', 'changeme', 'change_me',
    'change_me_to_random_64_char_string',   # the actual .env.example placeholder
    'change-this-to-a-random-string',
    'secret', 'dev-secret', 'default', 'password', 'test', 'xxx',
}
_MIN_SECRET_LENGTH = 32
_MIN_SECRET_BITS_PER_CHAR = 3.0  # rejects repeated/low-diversity strings;
                                  # real random secrets (openssl rand) score ~4.5-6.0


def _shannon_bits_per_char(value: str) -> float:
    counts: dict[str, int] = {}
    for ch in value:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(value)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def require_strong_secret(name: str, value: str | None) -> str:
    """Fail loudly at startup/first-use if `value` is missing, a known
    placeholder, too short, or too low-entropy to plausibly be a real secret.

    Order matters: the exact-match placeholder check runs first because a
    fixed placeholder string can score deceptively well on the entropy check
    below (it just means the string has many distinct characters, not that
    it's unpredictable) — length/entropy are a secondary net for *other*
    weak secrets, not a substitute for rejecting known placeholders by name.
    """
    if not value:
        raise RuntimeError(f'{name} env var is required and must be set')
    if value.strip().lower() in _KNOWN_PLACEHOLDER_SECRETS:
        raise RuntimeError(
            f'{name} env var is set to a known placeholder value from .env.example; '
            f'generate a real secret, e.g. `openssl rand -base64 48`'
        )
    if len(value) < _MIN_SECRET_LENGTH:
        raise RuntimeError(
            f'{name} env var is too short ({len(value)} chars); need at least {_MIN_SECRET_LENGTH}'
        )
    if _shannon_bits_per_char(value) < _MIN_SECRET_BITS_PER_CHAR:
        raise RuntimeError(
            f'{name} env var does not look random enough (low character diversity); '
            f'generate it with e.g. `openssl rand -base64 48`'
        )
    return value


JWT_SECRET = require_strong_secret('JWT_SECRET', os.environ.get('JWT_SECRET'))
JWT_ALG = 'HS256'
JWT_EXP_DAYS = 7
JWT_REFRESH_EXP_DAYS = 30
PREVIEW_TOKEN_EXP_MINUTES = 10

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
        'jti': uuid.uuid4().hex,
        'exp': datetime.now(timezone.utc) + timedelta(days=JWT_EXP_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def create_preview_token(user_id: str, project_id: str) -> str:
    """Create a short-lived token valid only for one customer builder preview."""
    payload = {
        'sub': user_id,
        'project_id': project_id,
        'type': 'builder_preview',
        'jti': uuid.uuid4().hex,
        'exp': datetime.now(timezone.utc) + timedelta(minutes=PREVIEW_TOKEN_EXP_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def verify_preview_token(token: str, project_id: str) -> str:
    """Return owner ID only when the token is valid and bound to this project."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid or expired preview token')
    if payload.get('type') != 'builder_preview' or payload.get('project_id') != project_id or not payload.get('sub'):
        raise HTTPException(status_code=403, detail='Preview token does not authorize this project')
    return str(payload['sub'])


def create_refresh_token(user_id: str) -> str:
    rti = uuid.uuid4().hex
    payload = {
        'sub': user_id,
        'jti': rti,
        'type': 'refresh',
        'exp': datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_EXP_DAYS),
    }
    try:
        if redis:
            asyncio.ensure_future(redis.set(f'rt:{user_id}:{rti}', '1', ex=JWT_REFRESH_EXP_DAYS * 86400))
    except Exception:
        pass
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def revoke_refresh_token(user_id: str, rti: str) -> None:
    try:
        if redis:
            await redis.delete(f'rt:{user_id}:{rti}')
    except Exception:
        pass


async def is_refresh_token_valid(user_id: str, rti: str) -> bool:
    try:
        if not redis:
            return True
        return bool(await redis.exists(f'rt:{user_id}:{rti}'))
    except Exception:
        return False


# ── Token revocation (logout / password change) ──────────────────────────────
# Stateless JWTs otherwise stay valid until expiry. We keep a short-lived Redis
# blocklist keyed by the token's `jti`, with a TTL equal to the token's remaining
# lifetime so the blocklist self-cleans. Tokens issued before this feature exist
# have no `jti` and are simply never revocable (treated as valid).
async def revoke_token(jti: str, exp: int) -> None:
    if not jti or redis is None:
        return
    try:
        ttl = max(1, int(exp - datetime.now(timezone.utc).timestamp()))
        await redis.set(f'jwt:revoked:{jti}', '1', ex=ttl)
    except Exception:
        # If Redis is unavailable we cannot persist the revocation. Fail open to
        # avoid bricking auth entirely; the token still expires naturally.
        pass


async def is_token_revoked(jti: str) -> bool:
    if not jti or redis is None:
        return False
    try:
        return bool(await redis.exists(f'jwt:revoked:{jti}'))
    except Exception:
        return False


async def _assert_not_revoked(payload: dict) -> None:
    jti = payload.get('jti')
    if jti and await is_token_revoked(jti):
        raise HTTPException(status_code=401, detail='Token revoked. Please sign in again.')


async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    if not creds:
        raise HTTPException(status_code=401, detail='Not authenticated')
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid or expired token')
    await _assert_not_revoked(payload)
    user = await db.users.find_one({'id': payload['sub']}, {'_id': 0})
    if not user:
        raise HTTPException(status_code=401, detail='User not found')
    return user


async def get_current_user_optional(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    """Like get_current_user but returns None instead of 401 when unauthenticated."""
    if not creds:
        return None
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        return None
    if await is_token_revoked(payload.get('jti', '')):
        return None
    user = await db.users.find_one({'id': payload['sub']}, {'_id': 0})
    return user or None


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
    if await is_token_revoked(payload.get('jti', '')):
        return None
    return await db.users.find_one({'id': payload['sub']}, {'_id': 0})
