"""Extras routes — cost tracking, analytics, WooCommerce, quiz, certificates."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from auth import get_current_user, get_current_admin
from db import db
from ai_cost import get_user_usage, get_global_usage
from analytics_advanced import funnel_analysis, retention_cohort, churn_analysis, conversion_metrics
from woo_sync import get_products, get_orders, get_inventory
from learning_extras import (
    create_quiz, submit_quiz, get_user_certificates, verify_certificate,
    create_assignment, submit_assignment, grade_assignment
)

router = APIRouter(prefix='/extras', tags=['extras'])


# ===== Cost Tracking =====
@router.get('/cost/my')
async def my_cost(days: int = 30, user=Depends(get_current_user)):
    return await get_user_usage(user['id'], days)


@router.get('/cost/global')
async def global_cost(days: int = 7, _=Depends(get_current_admin)):
    return await get_global_usage(days)


# ===== Advanced Analytics =====
class FunnelIn(BaseModel):
    steps: List[str]
    days: int = 30


@router.post('/analytics/funnel')
async def funnel(payload: FunnelIn, _=Depends(get_current_admin)):
    return await funnel_analysis(payload.steps, payload.days)


@router.get('/analytics/retention')
async def retention(days: int = 30, _=Depends(get_current_admin)):
    return await retention_cohort(days)


@router.get('/analytics/churn')
async def churn(days: int = 30, _=Depends(get_current_admin)):
    return await churn_analysis(days)


@router.get('/analytics/conversion')
async def conversion(days: int = 30, _=Depends(get_current_admin)):
    return await conversion_metrics(days)


# ===== WooCommerce =====
@router.get('/woo/products')
async def woo_products(page: int = 1, _=Depends(get_current_admin)):
    return await get_products(page)


@router.get('/woo/orders')
async def woo_orders(status: str = 'any', _=Depends(get_current_admin)):
    return await get_orders(status)


@router.get('/woo/inventory')
async def woo_inventory(_=Depends(get_current_admin)):
    return await get_inventory()


# ===== Quiz =====
class QuizCreateIn(BaseModel):
    course_id: str
    questions: List[Dict[str, Any]]
    passing_score: int = 70


class QuizSubmitIn(BaseModel):
    answers: List[int]


@router.post('/quiz/create')
async def quiz_create(payload: QuizCreateIn, _=Depends(get_current_admin)):
    return await create_quiz(payload.course_id, payload.questions, payload.passing_score)


@router.post('/quiz/{quiz_id}/submit')
async def quiz_submit(quiz_id: str, payload: QuizSubmitIn, user=Depends(get_current_user)):
    return await submit_quiz(quiz_id, user['id'], payload.answers)


# ===== Certificates =====
@router.get('/certificates/mine')
async def my_certificates(user=Depends(get_current_user)):
    return {'certificates': await get_user_certificates(user['id'])}


@router.get('/certificates/verify/{cert_id}')
async def cert_verify(cert_id: str, hash: str):
    valid = await verify_certificate(cert_id, hash)
    return {'valid': valid}


# ===== Assignments =====
class AssignmentCreateIn(BaseModel):
    course_id: str
    title: str
    description: str = ''
    due_date: str = ''


class AssignmentSubmitIn(BaseModel):
    content: str


class AssignmentGradeIn(BaseModel):
    grade: str
    feedback: str = ''


@router.post('/assignments/create')
async def assignment_create(payload: AssignmentCreateIn, _=Depends(get_current_admin)):
    return await create_assignment(payload.course_id, payload.title, payload.description, payload.due_date)


@router.post('/assignments/{assignment_id}/submit')
async def assignment_submit(assignment_id: str, payload: AssignmentSubmitIn, user=Depends(get_current_user)):
    return await submit_assignment(assignment_id, user['id'], payload.content)


@router.post('/assignments/{assignment_id}/grade/{submission_id}')
async def assignment_grade(assignment_id: str, submission_id: str, payload: AssignmentGradeIn, _=Depends(get_current_admin)):
    return await grade_assignment(assignment_id, submission_id, payload.grade, payload.feedback)
