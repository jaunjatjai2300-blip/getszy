from fastapi import APIRouter, HTTPException, Depends
from db import db
from models import SignupIn, LoginIn, User, UserOut
from auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/signup')
async def signup(body: SignupIn):
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
    return {'token': token, 'user': UserOut(**user.model_dump()).model_dump()}


@router.post('/login')
async def login(body: LoginIn):
    user = await db.users.find_one({'email': body.email.lower()}, {'_id': 0})
    if not user or not verify_password(body.password, user['password_hash']):
        raise HTTPException(401, 'Invalid email or password')
    token = create_token(user['id'], user['role'])
    return {'token': token, 'user': UserOut(**user).model_dump()}


@router.get('/me')
async def me(user=Depends(get_current_user)):
    return UserOut(**user).model_dump()
