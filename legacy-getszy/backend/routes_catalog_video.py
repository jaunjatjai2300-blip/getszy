"""Catalog-to-Video Auto-Sync.

Watches db.products via a MongoDB change stream and auto-dispatches a short
video generation job whenever a product is created OR its stock drops to <=5
(low-stock alert video). Generated with the same text_to_video pipeline.

Graceful: change streams require a replica set; on a standalone mongod the
watcher logs and stops without crashing the app. A manual trigger endpoint is
also provided for environments without change streams.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from auth import get_current_admin
from db import db

logger = logging.getLogger('getszy.catalog_video')
router = APIRouter(prefix='/catalog-video', tags=['catalog-video'])

WATCH_RUNNING = False


class _CatalogPayload:
    def __init__(self, topic, style='ad', scenes=5, language='hinglish'):
        self.topic = topic
        self.style = style
        self.scenes = scenes
        self.language = language


async def _dispatch(product: dict) -> str:
    title = product.get('title') or product.get('name') or 'New product'
    desc = product.get('description') or product.get('short_description') or ''
    topic = f"{title}. {desc}"[:300]
    owner = product.get('owner_id') or 'system'
    proj_id = str(uuid.uuid4())
    await db.video_projects.insert_one({
        'id': proj_id, 'user_id': owner, 'kind': 'catalog',
        'status': 'queued_from_catalog', 'topic': topic,
        'product_id': product.get('id') or str(product.get('_id')),
        'created_at': datetime.now(timezone.utc).isoformat(),
    })
    try:
        from routes_video_tools import _run_text_to_video
        asyncio.create_task(_run_text_to_video(proj_id, _CatalogPayload(topic), owner, True))
    except Exception as e:
        logger.warning('catalog dispatch failed: %s', e)
        await db.video_projects.update_one({'id': proj_id}, {'$set': {'status': 'failed', 'error': str(e)}})
    return proj_id


async def start_catalog_watcher():
    global WATCH_RUNNING
    if WATCH_RUNNING:
        return
    WATCH_RUNNING = True
    try:
        pipeline = [{'$match': {'operationType': {'$in': ['insert', 'update']}}}]
        async with db.products.watch(pipeline) as stream:
            logger.info('catalog-video change stream started')
            async for change in stream:
                doc = change.get('fullDocument') or {}
                stock = doc.get('stock', doc.get('inventory'))
                if change['operationType'] == 'insert' or (isinstance(stock, int) and stock <= 5):
                    await _dispatch(doc)
    except Exception as e:
        logger.warning('catalog-video watcher stopped (change streams need a replica set?): %s', e)
        WATCH_RUNNING = False


@router.get('/status')
async def catalog_status(_=Depends(get_current_admin)):
    return {'watching': WATCH_RUNNING}


@router.post('/start')
async def catalog_start(_=Depends(get_current_admin)):
    asyncio.create_task(start_catalog_watcher())
    return {'ok': True, 'watching': WATCH_RUNNING}


@router.post('/sync')
async def catalog_sync(_=Depends(get_current_admin)):
    """Manual sweep: dispatch videos for all products currently low on stock."""
    count = 0
    async for p in db.products.find({'stock': {'$lte': 5}}, {'_id': 0, 'title': 1, 'name': 1,
                                                            'description': 1, 'short_description': 1,
                                                            'owner_id': 1, 'id': 1, 'stock': 1}):
        await _dispatch(p)
        count += 1
    return {'ok': True, 'dispatched': count}
