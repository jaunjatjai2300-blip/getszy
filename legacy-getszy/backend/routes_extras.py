"""Advanced analytics + commerce + learning routes."""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from auth import get_current_admin, get_current_user
from ai_cost import get_ai_usage_stats
from analytics_advanced import get_funnel_analytics, get_retention_analysis, get_churn_analysis, get_conversion_metrics
from woo_sync import check_connection, sync_products, sync_orders
from learning_extras import (
    create_quiz, get_quiz, submit_quiz,
    generate_certificate, get_user_certificates, verify_certificate,
)
from pydantic import BaseModel, Field

# ── AI Cost Routes ───────────────────────────────────────────────────────────
cost_router = APIRouter(prefix='/admin/ai-cost', tags=['ai-cost'])

@cost_router.get('/stats', dependencies=[Depends(get_current_admin)])
async def ai_cost_stats(days: int = Query(30, ge=1, le=365)):
    return await get_ai_usage_stats(days)


# ── Analytics Routes ─────────────────────────────────────────────────────────
analytics_router = APIRouter(prefix='/admin/analytics', tags=['analytics'])

@analytics_router.get('/funnels', dependencies=[Depends(get_current_admin)])
async def funnels(days: int = Query(30, ge=1, le=365)):
    return await get_funnel_analytics(days)

@analytics_router.get('/retention', dependencies=[Depends(get_current_admin)])
async def retention(days: int = Query(30, ge=1, le=365)):
    return await get_retention_analysis(days)

@analytics_router.get('/churn', dependencies=[Depends(get_current_admin)])
async def churn(days: int = Query(30, ge=1, le=365)):
    return await get_churn_analysis(days)

@analytics_router.get('/conversion', dependencies=[Depends(get_current_admin)])
async def conversion(days: int = Query(30, ge=1, le=365)):
    return await get_conversion_metrics(days)


# ── WooCommerce Routes ───────────────────────────────────────────────────────
woo_router = APIRouter(prefix='/admin/woo', tags=['woocommerce'])

@woo_router.get('/status', dependencies=[Depends(get_current_admin)])
async def woo_status():
    return await check_connection()

@woo_router.get('/products', dependencies=[Depends(get_current_admin)])
async def woo_products(page: int = 1):
    return await sync_products(page=page)

@woo_router.get('/orders', dependencies=[Depends(get_current_admin)])
async def woo_orders():
    return await sync_orders()


# ── Quiz Routes ──────────────────────────────────────────────────────────────
quiz_router = APIRouter(prefix='/learning/quiz', tags=['quiz'])

class QuizCreateIn(BaseModel):
    course_slug: str
    title: str
    questions: list
    time_limit_min: int = 30

class QuizSubmitIn(BaseModel):
    answers: list[int]

@quiz_router.post('/create', dependencies=[Depends(get_current_admin)])
async def create(body: QuizCreateIn):
    return await create_quiz(body.course_slug, body.title, body.questions, body.time_limit_min)

@quiz_router.get('/get/{quiz_id}')
async def get_quiz_route(quiz_id: str):
    return await get_quiz(quiz_id)

@quiz_router.post('/submit/{quiz_id}')
async def submit(quiz_id: str, body: QuizSubmitIn, user=Depends(get_current_user)):
    return await submit_quiz(quiz_id, user['id'], body.answers)


# ── Certificate Routes ───────────────────────────────────────────────────────
cert_router = APIRouter(prefix='/learning/certificates', tags=['certificates'])

class CertGenIn(BaseModel):
    course_slug: str
    course_title: str

@cert_router.post('/generate')
async def gen_cert(body: CertGenIn, user=Depends(get_current_user)):
    return await generate_certificate(user['id'], body.course_slug, user.get('name', ''), body.course_title)

@cert_router.get('/my')
async def my_certs(user=Depends(get_current_user)):
    return await get_user_certificates(user['id'])

@cert_router.get('/verify/{code}')
async def verify(code: str):
    return await verify_certificate(code)
