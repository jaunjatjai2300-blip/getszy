import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from auth import get_current_user, get_current_admin
from db import db, serialize_doc

router = APIRouter(prefix='/admin/marketplace', tags=['marketplace'])


def _now():
    return datetime.now(timezone.utc).isoformat()


class ListingIn(BaseModel):
    title: str
    description: str
    category: str
    price: float = 0
    tags: List[str] = []
    tech_stack: List[str] = []
    preview_images: List[str] = []
    download_url: str = ''
    author_id: str
    author_name: str
    version: str = '1.0.0'
    compatibility: str = ''


class ReviewIn(BaseModel):
    user_id: str
    rating: int
    comment: str
    verified_purchase: bool = False


class InstallIn(BaseModel):
    user_id: str


class ReportIn(BaseModel):
    reason: str
    description: str = ''


class PayoutIn(BaseModel):
    amount: float
    payment_method: str
    account_details: dict = {}


@router.get('/listings')
async def list_listings(
    category: Optional[str] = None,
    sort: str = 'newest',
    price_range: str = 'all',
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    _=Depends(get_current_admin),
):
    q: dict = {}
    if category:
        q['category'] = category
    if price_range == 'free':
        q['price'] = 0
    elif price_range == 'paid':
        q['price'] = {'$gt': 0}
    if search:
        q['$or'] = [
            {'title': {'$regex': search, '$options': 'i'}},
            {'description': {'$regex': search, '$options': 'i'}},
            {'tags': {'$regex': search, '$options': 'i'}},
        ]
    sort_field = 'created_at'
    sort_dir = -1
    if sort == 'popular':
        sort_field = 'install_count'
        sort_dir = -1
    elif sort == 'rating':
        sort_field = 'avg_rating'
        sort_dir = -1
    elif sort == 'price':
        sort_field = 'price'
        sort_dir = 1
    total = await db.marketplace_listings.count_documents(q)
    items = await db.marketplace_listings.find(q, {'_id': 0}).sort(sort_field, sort_dir).skip(offset).limit(limit).to_list(limit)
    return {'total': total, 'items': items, 'limit': limit, 'offset': offset}


@router.post('/listings')
async def create_listing(body: ListingIn, _=Depends(get_current_admin)):
    listing_id = str(uuid.uuid4())
    doc = {
        'id': listing_id,
        **body.model_dump(),
        'status': 'draft',
        'install_count': 0,
        'avg_rating': 0,
        'review_count': 0,
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.marketplace_listings.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.get('/listings/{listing_id}')
async def get_listing(listing_id: str, _=Depends(get_current_admin)):
    listing = await db.marketplace_listings.find_one({'id': listing_id}, {'_id': 0})
    if not listing:
        raise HTTPException(404, 'Listing not found')
    reviews = await db.marketplace_reviews.find({'listing_id': listing_id}, {'_id': 0}).sort('created_at', -1).to_list(100)
    listing['reviews'] = reviews
    return listing


@router.put('/listings/{listing_id}')
async def update_listing(listing_id: str, body: dict, _=Depends(get_current_admin)):
    body.pop('id', None)
    body.pop('created_at', None)
    body['updated_at'] = _now()
    await db.marketplace_listings.update_one({'id': listing_id}, {'$set': body})
    listing = await db.marketplace_listings.find_one({'id': listing_id}, {'_id': 0})
    if not listing:
        raise HTTPException(404, 'Listing not found')
    return listing


@router.delete('/listings/{listing_id}')
async def delete_listing(listing_id: str, _=Depends(get_current_admin)):
    result = await db.marketplace_listings.delete_one({'id': listing_id})
    if result.deleted_count == 0:
        raise HTTPException(404, 'Listing not found')
    await db.marketplace_reviews.delete_many({'listing_id': listing_id})
    await db.marketplace_installs.delete_many({'listing_id': listing_id})
    return {'deleted': True}


@router.post('/listings/{listing_id}/publish')
async def publish_listing(listing_id: str, _=Depends(get_current_admin)):
    listing = await db.marketplace_listings.find_one({'id': listing_id}, {'_id': 0})
    if not listing:
        raise HTTPException(404, 'Listing not found')
    await db.marketplace_listings.update_one({'id': listing_id}, {'$set': {'status': 'published', 'published_at': _now(), 'updated_at': _now()}})
    return {'status': 'published'}


@router.post('/listings/{listing_id}/unpublish')
async def unpublish_listing(listing_id: str, _=Depends(get_current_admin)):
    listing = await db.marketplace_listings.find_one({'id': listing_id}, {'_id': 0})
    if not listing:
        raise HTTPException(404, 'Listing not found')
    await db.marketplace_listings.update_one({'id': listing_id}, {'$set': {'status': 'draft', 'updated_at': _now()}})
    return {'status': 'draft'}


@router.post('/listings/{listing_id}/reviews')
async def add_review(listing_id: str, body: ReviewIn, _=Depends(get_current_admin)):
    listing = await db.marketplace_listings.find_one({'id': listing_id}, {'_id': 0})
    if not listing:
        raise HTTPException(404, 'Listing not found')
    if body.rating < 1 or body.rating > 5:
        raise HTTPException(400, 'Rating must be between 1 and 5')
    review_id = str(uuid.uuid4())
    doc = {
        'id': review_id,
        'listing_id': listing_id,
        **body.model_dump(),
        'created_at': _now(),
    }
    await db.marketplace_reviews.insert_one(doc)
    pipeline = [
        {'$match': {'listing_id': listing_id}},
        {'$group': {'_id': None, 'avg': {'$avg': '$rating'}, 'count': {'$sum': 1}}},
    ]
    result = await db.marketplace_reviews.aggregate(pipeline).to_list(1)
    if result:
        avg_rating = round(result[0]['avg'], 2)
        review_count = result[0]['count']
    else:
        avg_rating = 0
        review_count = 0
    await db.marketplace_listings.update_one({'id': listing_id}, {'$set': {'avg_rating': avg_rating, 'review_count': review_count, 'updated_at': _now()}})
    doc.pop('_id', None)
    return doc


@router.get('/listings/{listing_id}/reviews')
async def list_reviews(listing_id: str, _=Depends(get_current_admin)):
    listing = await db.marketplace_listings.find_one({'id': listing_id}, {'_id': 0})
    if not listing:
        raise HTTPException(404, 'Listing not found')
    reviews = await db.marketplace_reviews.find({'listing_id': listing_id}, {'_id': 0}).sort('created_at', -1).to_list(200)
    pipeline = [
        {'$match': {'listing_id': listing_id}},
        {'$group': {'_id': None, 'avg': {'$avg': '$rating'}, 'count': {'$sum': 1}}},
    ]
    agg = await db.marketplace_reviews.aggregate(pipeline).to_list(1)
    avg_rating = round(agg[0]['avg'], 2) if agg else 0
    review_count = agg[0]['count'] if agg else 0
    return {'reviews': reviews, 'avg_rating': avg_rating, 'review_count': review_count}


@router.post('/listings/{listing_id}/install')
async def install_listing(listing_id: str, body: InstallIn, _=Depends(get_current_admin)):
    listing = await db.marketplace_listings.find_one({'id': listing_id}, {'_id': 0})
    if not listing:
        raise HTTPException(404, 'Listing not found')
    existing = await db.marketplace_installs.find_one({'user_id': body.user_id, 'listing_id': listing_id}, {'_id': 0})
    if existing:
        return existing
    install_id = str(uuid.uuid4())
    doc = {
        'id': install_id,
        'user_id': body.user_id,
        'listing_id': listing_id,
        'installed_at': _now(),
        'version': listing.get('version', '1.0.0'),
    }
    await db.marketplace_installs.insert_one(doc)
    await db.marketplace_listings.update_one({'id': listing_id}, {'$inc': {'install_count': 1}})
    doc.pop('_id', None)
    return doc


@router.get('/installs')
async def list_installs(user_id: Optional[str] = None, _=Depends(get_current_admin)):
    q: dict = {}
    if user_id:
        q['user_id'] = user_id
    installs = await db.marketplace_installs.find(q, {'_id': 0}).sort('installed_at', -1).to_list(200)
    for inst in installs:
        listing = await db.marketplace_listings.find_one({'id': inst['listing_id']}, {'_id': 0})
        inst['listing'] = listing
    return installs


@router.post('/installs/{install_id}/uninstall')
async def uninstall_item(install_id: str, _=Depends(get_current_admin)):
    install = await db.marketplace_installs.find_one({'id': install_id}, {'_id': 0})
    if not install:
        raise HTTPException(404, 'Install record not found')
    await db.marketplace_installs.delete_one({'id': install_id})
    await db.marketplace_listings.update_one({'id': install['listing_id']}, {'$inc': {'install_count': -1}})
    return {'uninstalled': True}


@router.post('/installs/{install_id}/update')
async def update_install(install_id: str, _=Depends(get_current_admin)):
    install = await db.marketplace_installs.find_one({'id': install_id}, {'_id': 0})
    if not install:
        raise HTTPException(404, 'Install record not found')
    listing = await db.marketplace_listings.find_one({'id': install['listing_id']}, {'_id': 0})
    if not listing:
        raise HTTPException(404, 'Listing not found')
    await db.marketplace_installs.update_one({'id': install_id}, {'$set': {'version': listing.get('version', '1.0.0'), 'updated_at': _now()}})
    return {'updated_to': listing.get('version', '1.0.0')}


@router.get('/categories')
async def get_categories(_=Depends(get_current_admin)):
    pipeline = [
        {'$group': {'_id': '$category', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
    ]
    results = await db.marketplace_listings.aggregate(pipeline).to_list(50)
    categories = [{'name': r['_id'], 'count': r['count']} for r in results if r['_id']]
    return {'categories': categories}


@router.get('/featured')
async def get_featured(limit: int = 10, _=Depends(get_current_admin)):
    featured = await db.marketplace_listings.find({'status': 'published'}, {'_id': 0}).sort([('install_count', -1), ('avg_rating', -1)]).limit(limit).to_list(limit)
    return {'featured': featured}


@router.post('/listings/{listing_id}/report')
async def report_listing(listing_id: str, body: ReportIn, _=Depends(get_current_admin)):
    listing = await db.marketplace_listings.find_one({'id': listing_id}, {'_id': 0})
    if not listing:
        raise HTTPException(404, 'Listing not found')
    report_id = str(uuid.uuid4())
    doc = {
        'id': report_id,
        'listing_id': listing_id,
        'listing_title': listing.get('title', ''),
        **body.model_dump(),
        'status': 'pending',
        'created_at': _now(),
    }
    await db.marketplace_reports.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.get('/reports')
async def list_reports(status: Optional[str] = None, _=Depends(get_current_admin)):
    q: dict = {}
    if status:
        q['status'] = status
    reports = await db.marketplace_reports.find(q, {'_id': 0}).sort('created_at', -1).to_list(200)
    return reports


@router.get('/earnings')
async def get_earnings(author_id: Optional[str] = None, _=Depends(get_current_admin)):
    q: dict = {}
    if author_id:
        q['author_id'] = author_id
    listings = await db.marketplace_listings.find(q, {'_id': 0}).to_list(500)
    total_installs = sum(l.get('install_count', 0) for l in listings)
    total_revenue = sum(l.get('install_count', 0) * l.get('price', 0) for l in listings)
    by_listing = [
        {
            'listing_id': l['id'],
            'title': l.get('title', ''),
            'installs': l.get('install_count', 0),
            'revenue': l.get('install_count', 0) * l.get('price', 0),
        }
        for l in listings
    ]
    pending_payouts = await db.marketplace_payouts.find({'status': 'pending'}, {'_id': 0}).to_list(100)
    pending_total = sum(p.get('amount', 0) for p in pending_payouts)
    return {
        'total_installs': total_installs,
        'total_revenue': total_revenue,
        'by_listing': by_listing,
        'pending_payouts': pending_total,
    }


@router.post('/payouts')
async def request_payout(body: PayoutIn, _=Depends(get_current_admin)):
    if body.amount <= 0:
        raise HTTPException(400, 'Amount must be positive')
    payout_id = str(uuid.uuid4())
    doc = {
        'id': payout_id,
        **body.model_dump(),
        'status': 'pending',
        'requested_at': _now(),
    }
    await db.marketplace_payouts.insert_one(doc)
    doc.pop('_id', None)
    return doc
