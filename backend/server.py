from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from db import db, client
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

app = FastAPI(title='getszy API')
api_router = APIRouter(prefix='/api')


@api_router.get('/')
async def root():
    return {'message': 'getszy API live', 'version': '2.0.0', 'ai': 'Getszy AI'}


@api_router.get('/health')
async def health():
    try:
        await db.command('ping')
        return {'status': 'ok', 'ai': 'Getszy AI'}
    except Exception as e:
        return {'status': 'error', 'detail': str(e)}


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

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=['*'],
    allow_headers=['*'],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('getszy')


@app.on_event('startup')
async def startup():
    logger.info('getszy backend starting')
    from seed import seed_if_empty, seed_courses_if_empty
    await seed_if_empty()
    await seed_courses_if_empty()
    # One-time migration: clear external video URLs in favour of branded placeholders
    flag = await db.system.find_one({'_id': 'video_branding_v1'})
    if not flag:
        res = await db.lessons.update_many(
            {'video_url': {'$regex': 'youtube|youtu.be|vimeo', '$options': 'i'}},
            {'$set': {'video_url': ''}},
        )
        await db.system.insert_one({'_id': 'video_branding_v1', 'modified_lessons': res.modified_count})
        logger.info(f'video migration: cleared {res.modified_count} external video URLs')
    # Ensure all premium-level courses are flagged
    await db.courses.update_many({'level': 'Advanced'}, {'$set': {'is_premium': True}})
    await db.courses.update_many({'level': {'$in': ['Beginner', 'Intermediate']}}, {'$set': {'is_premium': False}})


@app.on_event('shutdown')
async def shutdown_db():
    client.close()
