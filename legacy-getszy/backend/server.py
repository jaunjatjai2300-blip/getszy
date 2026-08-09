from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import os
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from db import db, client
from app.router_registry import load_all_routers
from monitoring import init_monitoring

app = FastAPI(title='getszy API')
api_router = APIRouter(prefix='/api')


@api_router.get('/')
async def root():
    return {'message': 'getszy API live', 'version': '2.0.0', 'ai': 'Getszy AI'}


@api_router.get('/health')
@api_router.get('/healthz')
async def health():
    try:
        await db.command('ping')
        return {'status': 'ok', 'ai': 'Getszy AI'}
    except Exception as e:
        return {'status': 'error', 'detail': str(e)}


# ===== Load all routers via registry =====
registered_router = load_all_routers()
api_router.include_router(registered_router)

app.include_router(api_router)

# ===== Security middleware =====
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get(
        'CORS_ORIGINS',
        'https://getszy.com,https://www.getszy.com,http://localhost:3000,http://localhost:5173'
    ).split(',') if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allow_headers=['Authorization', 'Content-Type'],
)

from middleware import RateLimitMiddleware, SecurityHeadersMiddleware, RequestLoggingMiddleware
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('getszy')


@app.on_event('startup')
async def startup():
    logger.info('getszy backend starting')
    init_monitoring()
    from seed import seed_if_empty, seed_courses_if_empty
    await seed_if_empty()
    await seed_courses_if_empty()
    # Migration: restore video URLs that were accidentally blanked
    flag = await db.system.find_one({'_id': 'video_restore_v1'})
    if not flag:
        VIDEO_URLS = {
            'welcome-why-ai-matters-for-women': 'https://www.youtube.com/embed/2ePf9rue1Ao',
            'what-is-ai-in-simple-terms': 'https://www.youtube.com/embed/ad79nYk2keg',
            'machine-learning-vs-deep-learning': 'https://www.youtube.com/embed/zjkBMFhNj_g',
            'how-chatgpt-actually-works': 'https://www.youtube.com/embed/w65p_IIp6JY',
            'your-first-ai-powered-task': 'https://www.youtube.com/embed/Yq0QkCxoTHM',
            'anatomy-of-a-great-prompt': 'https://www.youtube.com/embed/jC4v5AS4RIM',
            'role-context-task-framework': 'https://www.youtube.com/embed/dOxUroR57xs',
            'chain-of-thought-prompting': 'https://www.youtube.com/embed/H4olM_mExl8',
            'writing-content-that-converts': 'https://www.youtube.com/embed/aircAruvnKk',
            'building-a-research-assistant': 'https://www.youtube.com/embed/IHZwWFHWa-w',
            'custom-gpts-and-personas': 'https://www.youtube.com/embed/J0Aq44Pze-w',
            'ai-income-landscape-2026': 'https://www.youtube.com/embed/m_d3kI23wlw',
            'niche-selection-your-unfair-advantage': 'https://www.youtube.com/embed/H9M3n90gqdQ',
            'ai-content-creation-as-a-service': 'https://www.youtube.com/embed/JTxsNm9IdYU',
            'designing-digital-products-with-ai': 'https://www.youtube.com/embed/8jLOx1hD3_o',
            'ai-virtual-assistant-business': 'https://www.youtube.com/embed/iAyJG-pYS9I',
            'marketing-yourself-online': 'https://www.youtube.com/embed/1aA1WGON49E',
            'pricing-payments-and-scaling': 'https://www.youtube.com/embed/u3rqe6jbAQc',
            'ai-career-paths-for-women-2026': 'https://www.youtube.com/embed/3yPBVii7Ct0',
            'deep-dive-prompt-engineering': 'https://www.youtube.com/embed/p09yRj47kNM',
            'ai-tools-every-pro-must-know': 'https://www.youtube.com/embed/eyTtAheVm9w',
            'building-an-ai-portfolio': 'https://www.youtube.com/embed/dPq7DDjBfnE',
            'networking-personal-branding': 'https://www.youtube.com/embed/wOdmiOAYjQ4',
            'consultancy-charge-50k-per-project': 'https://www.youtube.com/embed/JBoT_pEwiP0',
            'interview-prep-for-ai-roles': 'https://www.youtube.com/embed/o42Cb1pTNVk',
            'your-90-day-action-plan': 'https://www.youtube.com/embed/qXcUkN2x8KM',
        }
        restored = 0
        for slug, url in VIDEO_URLS.items():
            title_pattern = slug.replace('-', ' ')
            res = await db.lessons.update_many(
                {'title': {'$regex': title_pattern.split()[0], '$options': 'i'}, 'video_url': ''},
                {'$set': {'video_url': url}}
            )
            restored += res.modified_count
        await db.system.insert_one({'_id': 'video_restore_v1', 'restored_lessons': restored})
        logger.info(f'video restore migration: restored {restored} lesson video URLs')
    # Ensure all premium-level courses are flagged
    await db.courses.update_many({'level': 'Advanced'}, {'$set': {'is_premium': True}})
    await db.courses.update_many({'level': {'$in': ['Beginner', 'Intermediate']}}, {'$set': {'is_premium': False}})
    # Unique index so a Razorpay payment_id can only ever grant credits once
    await db.billing_processed_payments.create_index('payment_id', unique=True)
    # Production indexes
    await db.users.create_index('email', unique=True)
    await db.users.create_index('id', unique=True)
    await db.products.create_index('slug')
    await db.products.create_index('category')
    await db.products.create_index('is_active')
    await db.orders.create_index('user_id')
    await db.orders.create_index('created_at')
    await db.orders.create_index('order_number', unique=True)
    await db.carts.create_index('user_id', unique=True)
    await db.notifications.create_index([('user_id', 1), ('created_at', -1)])
    await db.video_jobs.create_index('user_id')
    await db.request_logs.create_index('timestamp', expireAfterSeconds=604800)
    logger.info('indexes ensured')


@app.on_event('shutdown')
async def shutdown_db():
    client.close()
