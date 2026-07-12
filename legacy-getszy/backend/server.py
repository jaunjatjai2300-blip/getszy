from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from db import db, client
from middleware import RateLimitMiddleware, SecurityHeadersMiddleware, RequestLoggingMiddleware
from redis_cache import get_redis

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('getszy')


@asynccontextmanager
async def lifespan(app):
    logger.info('Getszy backend starting')
    redis = await get_redis()
    logger.info('Redis connected')
    from seed import seed_if_empty, seed_courses_if_empty
    await seed_if_empty()
    await seed_courses_if_empty()
    flag = await db.system.find_one({'_id': 'video_branding_v1'})
    if not flag:
        res = await db.lessons.update_many(
            {'video_url': {'$regex': 'youtube|youtu.be|vimeo', '$options': 'i'}},
            {'$set': {'video_url': ''}},
        )
        await db.system.insert_one({'_id': 'video_branding_v1', 'modified_lessons': res.modified_count})
        logger.info(f'video migration: cleared {res.modified_count} external video URLs')
    await db.courses.update_many({'level': 'Advanced'}, {'$set': {'is_premium': True}})
    await db.courses.update_many({'level': {'$in': ['Beginner', 'Intermediate']}}, {'$set': {'is_premium': False}})
    await db.billing_processed_payments.create_index('payment_id', unique=True)
    logger.info('Getszy backend ready')
    yield
    logger.info('Getszy backend shutting down')
    redis = await get_redis()
    await redis.close()
    client.close()

from routes_auth import router as auth_router
from routes_catalog import router as catalog_router
from routes_cart_orders import router as cart_router
from routes_admin import router as admin_router
from routes_learning import router as learning_router
from routes_builder import router as builder_router
from routes_subscription import router as sub_router
from routes_ai_ops import router as ai_ops_router
from routes_sourcing import router as sourcing_router
from routes_media import router as media_router
from routes_deploy import router as deploy_router
from routes_skills import router as skills_router
from routes_stacks import router as stacks_router
from routes_copilot import router as copilot_router
from routes_waitlist import router as waitlist_router
from routes_creator import router as creator_router
from routes_video import router as video_router
from routes_publishing import router as publishing_router
from routes_workforce import router as workforce_router
from routes_chat_builder import router as chat_builder_router
from routes_workspace import router as workspace_router
from routes_hosting import router as hosting_router, host_router
from routes_razorpay import router as razorpay_router
from routes_legal import router as legal_router
from routes_support import router as support_router
from routes_video_factory import router as video_factory_router
from routes_credits import router as credits_router
from routes_social import router as social_router
from routes_workflows import router as workflows_router
from routes_avatar import router as avatar_router
from routes_projects import router as projects_router
from routes_commerce_extra import router as commerce_extra_router
from routes_ai_platform import router as ai_platform_router
import skills.creator_skills  # noqa: F401 - register creator skills
from routes_ws import router as ws_router
from routes_images import router as images_router
from routes_voice import router as voice_router
from routes_audit import router as audit_router
from routes_queue import router as queue_router
from routes_git import router as git_router
from routes_notifications import router as notifications_router
from routes_extras import cost_router, analytics_router, woo_router, quiz_router, cert_router

app = FastAPI(
    title='Getszy API',
    description='AI Founder Operating System - Backend API',
    version='2.0.0',
    docs_url='/api/docs' if os.environ.get('ENABLE_DOCS') == '1' else None,
    redoc_url=None,
    lifespan=lifespan,
)
api_router = APIRouter(prefix='/api')


@api_router.get('/')
async def root():
    return {'message': 'Getszy API live', 'version': '2.0.0', 'ai': 'Getszy AI'}


@api_router.get('/health')
async def health():
    try:
        await db.command('ping')
        mongo_status = 'ok'
    except Exception as e:
        mongo_status = f'error: {e}'
    return {
        'status': 'ok' if mongo_status == 'ok' else 'degraded',
        'mongo': mongo_status,
        'version': '2.0.0',
    }


api_router.include_router(auth_router)
api_router.include_router(catalog_router)
api_router.include_router(cart_router)
api_router.include_router(admin_router)
api_router.include_router(learning_router)
api_router.include_router(builder_router)
api_router.include_router(sub_router)
api_router.include_router(ai_ops_router)
api_router.include_router(sourcing_router)
api_router.include_router(media_router)
api_router.include_router(deploy_router)
api_router.include_router(skills_router)
api_router.include_router(stacks_router)
api_router.include_router(copilot_router)
api_router.include_router(waitlist_router)
api_router.include_router(creator_router)
api_router.include_router(video_router)
api_router.include_router(publishing_router)
api_router.include_router(workforce_router)
api_router.include_router(chat_builder_router)
api_router.include_router(workspace_router)
api_router.include_router(hosting_router)
api_router.include_router(host_router)
api_router.include_router(razorpay_router)
api_router.include_router(legal_router)
api_router.include_router(support_router)
api_router.include_router(video_factory_router)
api_router.include_router(credits_router)
api_router.include_router(social_router)
api_router.include_router(workflows_router)
api_router.include_router(avatar_router)
api_router.include_router(projects_router)
api_router.include_router(commerce_extra_router)
api_router.include_router(ai_platform_router)
api_router.include_router(images_router)
api_router.include_router(voice_router)
api_router.include_router(audit_router)
api_router.include_router(queue_router)
api_router.include_router(git_router)
api_router.include_router(notifications_router)
api_router.include_router(cost_router)
api_router.include_router(analytics_router)
api_router.include_router(woo_router)
api_router.include_router(quiz_router)
api_router.include_router(cert_router)

app.include_router(api_router)
app.include_router(ws_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=['*'],
    allow_headers=['*'],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f'Unhandled error: {request.method} {request.url.path} - {exc}', exc_info=True)
    return JSONResponse(
        status_code=500,
        content={'detail': 'Internal server error'},
    )
