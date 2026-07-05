"""Admin Sourcing routes - trending products, supplier integrations."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

from auth import get_current_admin
from db import db, serialize_doc
from sourcing.trending import scan_trending, last_scan
from sourcing.markup import enforce_price, compute_margin
from sourcing import cj as cj_module
from sourcing import shiprocket as sr_module

router = APIRouter(prefix='/admin/sourcing', tags=['sourcing'])


class ImportItemIn(BaseModel):
    title: str
    cost_price: float
    suggested_price: float
    category: str
    hero_image: str
    audience: Optional[str] = ''
    niche: Optional[str] = ''
    supplier: Optional[str] = 'Getszy Source'


class MarkupCheckIn(BaseModel):
    cost_price: float
    is_digital: bool = False
    custom_markup: Optional[float] = None


@router.get('/status')
async def status(_=Depends(get_current_admin)):
    return {
        'getszy_source': {'enabled': True, 'label': 'Getszy Source · India', 'supplier_count': 4, 'avg_delivery_days': '5-7'},
        'cj_dropshipping': {'enabled': cj_module.is_configured(), 'label': 'CJ Dropshipping', 'avg_delivery_days': '7-12'},
        'shiprocket': {'enabled': sr_module.is_configured(), 'label': 'Shiprocket', 'avg_delivery_days': '5-6'},
        'last_scan': last_scan(),
    }


@router.post('/trending/scan')
async def trigger_scan(limit: int = 12, _=Depends(get_current_admin)):
    items = await scan_trending(limit=limit)
    # Persist a scan record
    await db.sourcing_scans.insert_one({
        'id': str(uuid.uuid4()),
        'at': datetime.now(timezone.utc).isoformat(),
        'count': len(items),
    })
    return {'count': len(items), 'items': items}


@router.get('/trending')
async def get_trending(_=Depends(get_current_admin)):
    snap = last_scan()
    if not snap['items']:
        items = await scan_trending(limit=12)
        snap = last_scan()
    return snap


@router.post('/import')
async def import_product(payload: ImportItemIn, _=Depends(get_current_admin)):
    # Enforce the 40% physical margin floor
    safe_price = enforce_price(payload.cost_price, is_digital=False, custom_markup=payload.suggested_price / payload.cost_price if payload.cost_price else None)
    margin = compute_margin(payload.cost_price, safe_price)
    if margin['margin_pct'] < 40:
        safe_price = enforce_price(payload.cost_price, is_digital=False)
        margin = compute_margin(payload.cost_price, safe_price)

    pid = str(uuid.uuid4())
    slug = payload.title.lower().replace(' ', '-')[:80] + '-' + pid[:6]
    doc = {
        'id': pid,
        'name': payload.title,
        'slug': slug,
        'description': f'Trending pick from {payload.supplier}. Curated for the {payload.audience} audience.',
        'images': [payload.hero_image] if payload.hero_image else [],
        'price': safe_price,
        'cost_price': payload.cost_price,
        'stock': 50,
        'category': payload.category,
        'supplier': payload.supplier,
        'is_digital': False,
        'is_featured': True,
        'is_active': True,
        'sourcing': {
            'niche': payload.niche,
            'audience': payload.audience,
            'imported_at': datetime.now(timezone.utc).isoformat(),
            'margin_pct': margin['margin_pct'],
            'profit_per_unit': margin['profit'],
        },
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.products.insert_one(doc)
    out = await db.products.find_one({'id': pid}, {'_id': 0})
    return {'status': 'imported', 'product': out, 'margin': margin}


@router.post('/markup/check')
async def markup_check(payload: MarkupCheckIn, _=Depends(get_current_admin)):
    sell = enforce_price(payload.cost_price, is_digital=payload.is_digital, custom_markup=payload.custom_markup)
    return {'suggested_price': sell, **compute_margin(payload.cost_price, sell)}


# ===== CJ Dropshipping =====
@router.get('/cj/status')
async def cj_status(_=Depends(get_current_admin)):
    return {'configured': cj_module.is_configured()}


@router.get('/cj/search')
async def cj_search(keyword: str = 'kids', page: int = 1, _=Depends(get_current_admin)):
    return await cj_module.search_products(keyword=keyword, page=page)


# ===== Shiprocket =====
@router.get('/shiprocket/status')
async def sr_status(_=Depends(get_current_admin)):
    return {'configured': sr_module.is_configured()}
