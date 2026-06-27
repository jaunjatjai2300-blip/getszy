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
from llm_provider import provider_info

app = FastAPI(title='getszy API')
api_router = APIRouter(prefix='/api')


@api_router.get('/')
async def root():
    return {'message': 'getszy API live', 'version': '2.0.0', 'llm': provider_info()}


@api_router.get('/health')
async def health():
    try:
        await db.command('ping')
        return {'status': 'ok', 'llm': provider_info()}
    except Exception as e:
        return {'status': 'error', 'detail': str(e)}


api_router.include_router(auth_router)
api_router.include_router(catalog_router)
api_router.include_router(cart_router)
api_router.include_router(admin_router)
api_router.include_router(learning_router)
api_router.include_router(builder_router)

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
    logger.info(f'getszy backend starting... LLM provider: {provider_info()}')
    from seed import seed_if_empty, seed_courses_if_empty
    await seed_if_empty()
    await seed_courses_if_empty()


@app.on_event('shutdown')
async def shutdown_db():
    client.close()
