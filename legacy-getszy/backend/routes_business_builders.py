import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_admin
from db import db

router = APIRouter(prefix='/admin/business-builders', tags=['business-builders'])


def _now():
    return datetime.now(timezone.utc).isoformat()


def _uid():
    return str(uuid.uuid4())


# ── CRM Pydantic Models ──────────────────────────────────────────

class CRMContactIn(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    tags: List[str] = []
    source: str = 'web'
    status: str = 'lead'
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class CRMDealIn(BaseModel):
    title: str
    value: float
    currency: str = 'USD'
    pipeline_id: Optional[str] = None
    stage: str = 'lead'
    contact_id: Optional[str] = None
    expected_close_date: Optional[str] = None
    probability: int = 10
    notes: Optional[str] = None


class CRMDealMoveIn(BaseModel):
    new_stage: str


class CRMActivityIn(BaseModel):
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    type: str
    subject: str
    description: Optional[str] = None
    date: Optional[str] = None
    outcome: Optional[str] = None


# ── ERP Pydantic Models ──────────────────────────────────────────

class ERPWarehouseIn(BaseModel):
    name: str
    address: Optional[str] = None
    capacity: int = 1000
    manager: Optional[str] = None


class ERPItemIn(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    unit_price: float = 0.0


class ERPPurchaseOrderIn(BaseModel):
    vendor_id: str
    items: List[ERPItemIn]
    expected_date: Optional[str] = None
    status: str = 'draft'


class ERPReceiveIn(BaseModel):
    received_items: List[dict]
    warehouse_id: str


class ERPStockTransferIn(BaseModel):
    product_id: str
    from_warehouse_id: str
    to_warehouse_id: str
    quantity: int
    notes: Optional[str] = None


class ERPVendorIn(BaseModel):
    name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    payment_terms: Optional[str] = None
    lead_time_days: int = 7


# ── HRMS Pydantic Models ─────────────────────────────────────────

class HRMSEmployeeIn(BaseModel):
    name: str
    email: str
    department_id: Optional[str] = None
    position: str
    salary: float
    join_date: str
    manager_id: Optional[str] = None
    status: str = 'active'
    skills: List[str] = []


class HRMSDepartmentIn(BaseModel):
    name: str
    head_id: Optional[str] = None
    budget: float = 0.0
    description: Optional[str] = None


class HRMSAttendanceIn(BaseModel):
    employee_id: str
    date: str
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    status: str = 'present'


class HRMSLeaveRequestIn(BaseModel):
    employee_id: str
    type: str
    start_date: str
    end_date: str
    reason: Optional[str] = None


class HRMSPayrollIn(BaseModel):
    employee_id: str
    month: int
    year: int
    basic: float
    deductions: dict = {}
    allowances: dict = {}
    net_pay: float
    status: str = 'draft'


class HRMSPerformanceIn(BaseModel):
    employee_id: str
    reviewer_id: str
    period: str
    rating: int
    strengths: List[str] = []
    improvements: List[str] = []
    goals: List[str] = []
    comments: Optional[str] = None


# ── Booking Pydantic Models ───────────────────────────────────────

class BookingServiceIn(BaseModel):
    name: str
    duration_minutes: int
    price: float
    description: Optional[str] = None
    category: Optional[str] = None
    max_per_slot: int = 1


class BookingSlotIn(BaseModel):
    service_id: str
    staff_id: Optional[str] = None
    date: str
    start_time: str
    end_time: str
    capacity: int = 1


class BookingAppointmentIn(BaseModel):
    service_id: str
    slot_id: str
    customer_name: str
    customer_email: str
    customer_phone: Optional[str] = None
    notes: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
#  CRM ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

CRM_COLLECTIONS = ['crm_contacts', 'crm_deals', 'crm_activities', 'crm_pipelines']


@router.post('/crm/init')
async def crm_init(_=Depends(get_current_admin)):
    collections_status = {}
    for coll in CRM_COLLECTIONS:
        existing = await db.list_collection_names()
        if coll not in existing:
            await db.create_collection(coll)
        collections_status[coll] = 'ready'

    existing_pipelines = await db.crm_pipelines.count_documents({})
    if existing_pipelines == 0:
        default_pipeline_id = _uid()
        await db.crm_pipelines.insert_one({
            'id': default_pipeline_id,
            'name': 'Default Pipeline',
            'stages': [
                {'name': 'Lead', 'order': 1, 'probability': 10, 'color': '#6366f1'},
                {'name': 'Qualified', 'order': 2, 'probability': 25, 'color': '#8b5cf6'},
                {'name': 'Proposal', 'order': 3, 'probability': 50, 'color': '#f59e0b'},
                {'name': 'Negotiation', 'order': 4, 'probability': 75, 'color': '#f97316'},
                {'name': 'Won', 'order': 5, 'probability': 100, 'color': '#22c55e'},
                {'name': 'Lost', 'order': 6, 'probability': 0, 'color': '#ef4444'},
            ],
            'created_at': _now(),
        })

    return {'status': 'initialized', 'collections': collections_status, 'pipeline_created': existing_pipelines == 0}


@router.post('/crm/contacts')
async def crm_create_contact(body: CRMContactIn, _=Depends(get_current_admin)):
    doc = {
        'id': _uid(),
        **body.model_dump(),
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.crm_contacts.insert_one(doc)
    return doc


@router.get('/crm/contacts')
async def crm_list_contacts(
    search: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    assigned_to: Optional[str] = None,
    sort: str = 'created_at',
    order: int = -1,
    skip: int = 0,
    limit: int = 50,
    _=Depends(get_current_admin),
):
    query = {}
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'email': {'$regex': search, '$options': 'i'}},
            {'company': {'$regex': search, '$options': 'i'}},
        ]
    if status:
        query['status'] = status
    if tag:
        query['tags'] = tag
    if assigned_to:
        query['assigned_to'] = assigned_to

    total = await db.crm_contacts.count_documents(query)
    cursor = db.crm_contacts.find(query, {'_id': 0}).sort(sort, order).skip(skip).limit(limit)
    contacts = await cursor.to_list(limit)
    return {'contacts': contacts, 'total': total, 'skip': skip, 'limit': limit}


@router.put('/crm/contacts/{contact_id}')
async def crm_update_contact(contact_id: str, body: CRMContactIn, _=Depends(get_current_admin)):
    update = body.model_dump()
    update['updated_at'] = _now()
    result = await db.crm_contacts.update_one({'id': contact_id}, {'$set': update})
    if result.matched_count == 0:
        raise HTTPException(404, 'Contact not found')
    contact = await db.crm_contacts.find_one({'id': contact_id}, {'_id': 0})
    return contact


@router.delete('/crm/contacts/{contact_id}')
async def crm_delete_contact(contact_id: str, _=Depends(get_current_admin)):
    result = await db.crm_contacts.delete_one({'id': contact_id})
    if result.deleted_count == 0:
        raise HTTPException(404, 'Contact not found')
    return {'deleted': True}


@router.post('/crm/deals')
async def crm_create_deal(body: CRMDealIn, _=Depends(get_current_admin)):
    doc = {
        'id': _uid(),
        **body.model_dump(),
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.crm_deals.insert_one(doc)
    return doc


@router.get('/crm/deals')
async def crm_list_deals(
    pipeline_id: Optional[str] = None,
    stage: Optional[str] = None,
    contact_id: Optional[str] = None,
    sort: str = 'created_at',
    order: int = -1,
    skip: int = 0,
    limit: int = 50,
    _=Depends(get_current_admin),
):
    query = {}
    if pipeline_id:
        query['pipeline_id'] = pipeline_id
    if stage:
        query['stage'] = stage
    if contact_id:
        query['contact_id'] = contact_id

    total = await db.crm_deals.count_documents(query)
    cursor = db.crm_deals.find(query, {'_id': 0}).sort(sort, order).skip(skip).limit(limit)
    deals = await cursor.to_list(limit)
    return {'deals': deals, 'total': total}


@router.put('/crm/deals/{deal_id}')
async def crm_update_deal(deal_id: str, body: CRMDealIn, _=Depends(get_current_admin)):
    update = body.model_dump()
    update['updated_at'] = _now()
    result = await db.crm_deals.update_one({'id': deal_id}, {'$set': update})
    if result.matched_count == 0:
        raise HTTPException(404, 'Deal not found')
    deal = await db.crm_deals.find_one({'id': deal_id}, {'_id': 0})
    return deal


@router.post('/crm/deals/{deal_id}/move')
async def crm_move_deal(deal_id: str, body: CRMDealMoveIn, _=Depends(get_current_admin)):
    deal = await db.crm_deals.find_one({'id': deal_id}, {'_id': 0})
    if not deal:
        raise HTTPException(404, 'Deal not found')

    old_stage = deal.get('stage', '')
    await db.crm_deals.update_one(
        {'id': deal_id},
        {'$set': {'stage': body.new_stage, 'updated_at': _now()}}
    )

    await db.crm_activities.insert_one({
        'id': _uid(),
        'contact_id': deal.get('contact_id'),
        'deal_id': deal_id,
        'type': 'note',
        'subject': f'Deal moved from {old_stage} to {body.new_stage}',
        'description': f'Stage change: {old_stage} -> {body.new_stage}',
        'date': _now(),
        'outcome': None,
        'created_at': _now(),
    })

    updated = await db.crm_deals.find_one({'id': deal_id}, {'_id': 0})
    return updated


@router.get('/crm/pipeline')
async def crm_pipeline_view(
    pipeline_id: Optional[str] = None,
    _=Depends(get_current_admin),
):
    pipeline_query = {}
    if pipeline_id:
        pipeline_query['id'] = pipeline_id
    pipeline = await db.crm_pipelines.find_one(pipeline_query, {'_id': 0})
    if not pipeline:
        raise HTTPException(404, 'Pipeline not found')

    deal_query = {}
    if pipeline_id:
        deal_query['pipeline_id'] = pipeline_id

    deals = await db.crm_deals.find(deal_query, {'_id': 0}).to_list(10000)

    stages = pipeline.get('stages', [])
    stage_map = {s['name']: s for s in stages}

    pipeline_view = []
    for stage in stages:
        stage_deals = [d for d in deals if d.get('stage') == stage['name']]
        total_value = sum(d.get('value', 0) for d in stage_deals)
        pipeline_view.append({
            'stage': stage['name'],
            'order': stage.get('order', 0),
            'color': stage.get('color', '#3b82f6'),
            'deal_count': len(stage_deals),
            'total_value': total_value,
            'deals': stage_deals,
        })

    total_pipeline_value = sum(d.get('value', 0) for d in deals)

    return {
        'pipeline': pipeline,
        'stages': pipeline_view,
        'total_deals': len(deals),
        'total_pipeline_value': total_pipeline_value,
    }


@router.post('/crm/activities')
async def crm_create_activity(body: CRMActivityIn, _=Depends(get_current_admin)):
    doc = {
        'id': _uid(),
        **body.model_dump(),
        'date': body.date or _now(),
        'created_at': _now(),
    }
    await db.crm_activities.insert_one(doc)
    return doc


@router.get('/crm/activities')
async def crm_list_activities(
    contact_id: Optional[str] = None,
    deal_id: Optional[str] = None,
    type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    _=Depends(get_current_admin),
):
    query = {}
    if contact_id:
        query['contact_id'] = contact_id
    if deal_id:
        query['deal_id'] = deal_id
    if type:
        query['type'] = type

    total = await db.crm_activities.count_documents(query)
    cursor = db.crm_activities.find(query, {'_id': 0}).sort('date', -1).skip(skip).limit(limit)
    activities = await cursor.to_list(limit)
    return {'activities': activities, 'total': total}


@router.get('/crm/dashboard')
async def crm_dashboard(_=Depends(get_current_admin)):
    total_contacts = await db.crm_contacts.count_documents({})
    total_deals = await db.crm_deals.count_documents({})

    pipeline = await db.crm_pipelines.find_one({}, {'_id': 0})
    deals_by_stage = {}
    all_deals = await db.crm_deals.find({}, {'_id': 0}).to_list(10000)
    for deal in all_deals:
        stage = deal.get('stage', 'unknown')
        if stage not in deals_by_stage:
            deals_by_stage[stage] = {'count': 0, 'value': 0}
        deals_by_stage[stage]['count'] += 1
        deals_by_stage[stage]['value'] += deal.get('value', 0)

    total_pipeline_value = sum(d.get('value', 0) for d in all_deals)

    won_deals = [d for d in all_deals if d.get('stage') == 'Won']
    lost_deals = [d for d in all_deals if d.get('stage') == 'Lost']
    closed_count = len(won_deals) + len(lost_deals)
    conversion_rate = (len(won_deals) / closed_count * 100) if closed_count > 0 else 0.0
    avg_deal_size = (total_pipeline_value / total_deals) if total_deals > 0 else 0.0

    now = datetime.now(timezone.utc)
    week_start = now.timestamp() - (7 * 86400)
    activities_all = await db.crm_activities.find({}, {'_id': 0}).to_list(50000)
    activities_this_week = 0
    for act in activities_all:
        try:
            dt = datetime.fromisoformat(act.get('date', act.get('created_at', '')))
            if dt.timestamp() >= week_start:
                activities_this_week += 1
        except Exception:
            pass

    month_start_str = now.strftime('%Y-%m-01')
    deals_closed_this_month = len([
        d for d in won_deals
        if d.get('created_at', '') >= month_start_str
    ])
    revenue_this_month = sum(
        d.get('value', 0) for d in won_deals
        if d.get('created_at', '') >= month_start_str
    )

    return {
        'total_contacts': total_contacts,
        'deals_by_stage': deals_by_stage,
        'total_pipeline_value': total_pipeline_value,
        'conversion_rate': round(conversion_rate, 2),
        'avg_deal_size': round(avg_deal_size, 2),
        'activities_this_week': activities_this_week,
        'deals_closed_this_month': deals_closed_this_month,
        'revenue_this_month': revenue_this_month,
    }


@router.get('/crm/reports')
async def crm_reports(_=Depends(get_current_admin)):
    all_contacts = await db.crm_contacts.find({}, {'_id': 0}).to_list(100000)
    all_deals = await db.crm_deals.find({}, {'_id': 0}).to_list(100000)
    all_activities = await db.crm_activities.find({}, {'_id': 0}).to_list(100000)

    revenue_by_source = {}
    for deal in all_deals:
        contact_id = deal.get('contact_id')
        source = 'unknown'
        for c in all_contacts:
            if c.get('id') == contact_id:
                source = c.get('source', 'unknown')
                break
        if source not in revenue_by_source:
            revenue_by_source[source] = {'total_value': 0, 'deal_count': 0, 'won_value': 0}
        revenue_by_source[source]['total_value'] += deal.get('value', 0)
        revenue_by_source[source]['deal_count'] += 1
        if deal.get('stage') == 'Won':
            revenue_by_source[source]['won_value'] += deal.get('value', 0)

    total_leads = len([d for d in all_deals if d.get('stage') in ('Lead', 'lead')])
    total_qualified = len([d for d in all_deals if d.get('stage') == 'Qualified'])
    total_proposal = len([d for d in all_deals if d.get('stage') == 'Proposal'])
    total_negotiation = len([d for d in all_deals if d.get('stage') == 'Negotiation'])
    total_won = len([d for d in all_deals if d.get('stage') == 'Won'])
    total_lost = len([d for d in all_deals if d.get('stage') == 'Lost'])

    conversion_funnel = {
        'leads': total_leads,
        'qualified': total_qualified,
        'proposal': total_proposal,
        'negotiation': total_negotiation,
        'won': total_won,
        'lost': total_lost,
    }

    activity_heatmap = {}
    for act in all_activities:
        try:
            dt = datetime.fromisoformat(act.get('date', act.get('created_at', '')))
            day_key = dt.strftime('%Y-%m-%d')
            hour_key = str(dt.hour)
            if day_key not in activity_heatmap:
                activity_heatmap[day_key] = {}
            activity_heatmap[day_key][hour_key] = activity_heatmap[day_key].get(hour_key, 0) + 1
        except Exception:
            pass

    deal_owner_stats = {}
    for deal in all_deals:
        owner = deal.get('assigned_to', 'unassigned')
        if owner not in deal_owner_stats:
            deal_owner_stats[owner] = {'total_deals': 0, 'total_value': 0, 'won_deals': 0, 'won_value': 0}
        deal_owner_stats[owner]['total_deals'] += 1
        deal_owner_stats[owner]['total_value'] += deal.get('value', 0)
        if deal.get('stage') == 'Won':
            deal_owner_stats[owner]['won_deals'] += 1
            deal_owner_stats[owner]['won_value'] += deal.get('value', 0)

    return {
        'revenue_by_source': revenue_by_source,
        'conversion_funnel': conversion_funnel,
        'activity_heatmap': activity_heatmap,
        'top_performers': deal_owner_stats,
    }


# ═══════════════════════════════════════════════════════════════════
#  ERP ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

ERP_COLLECTIONS = ['erp_products', 'erp_warehouses', 'erp_purchase_orders', 'erp_stock_movements', 'erp_vendors', 'erp_bom']


@router.post('/erp/init')
async def erp_init(_=Depends(get_current_admin)):
    collections_status = {}
    for coll in ERP_COLLECTIONS:
        existing = await db.list_collection_names()
        if coll not in existing:
            await db.create_collection(coll)
        collections_status[coll] = 'ready'
    return {'status': 'initialized', 'collections': collections_status}


@router.post('/erp/warehouses')
async def erp_create_warehouse(body: ERPWarehouseIn, _=Depends(get_current_admin)):
    doc = {
        'id': _uid(),
        **body.model_dump(),
        'current_stock': 0,
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.erp_warehouses.insert_one(doc)
    return doc


@router.get('/erp/warehouses')
async def erp_list_warehouses(_=Depends(get_current_admin)):
    warehouses = await db.erp_warehouses.find({}, {'_id': 0}).to_list(1000)
    for wh in warehouses:
        stock_count = await db.erp_stock_movements.aggregate([
            {'$match': {'warehouse_id': wh['id']}},
            {'$group': {'_id': '$product_id', 'net': {'$sum': '$quantity'}}},
        ]).to_list(10000)
        wh['stock_levels'] = {s['_id']: s['net'] for s in stock_count}
        wh['current_stock'] = sum(abs(s['net']) for s in stock_count)
    return {'warehouses': warehouses}


@router.post('/erp/purchase-orders')
async def erp_create_po(body: ERPPurchaseOrderIn, _=Depends(get_current_admin)):
    total_amount = sum(item.quantity * item.unit_price for item in body.items)
    doc = {
        'id': _uid(),
        'vendor_id': body.vendor_id,
        'items': [item.model_dump() for item in body.items],
        'total_amount': total_amount,
        'expected_date': body.expected_date,
        'status': body.status,
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.erp_purchase_orders.insert_one(doc)
    return doc


@router.get('/erp/purchase-orders')
async def erp_list_pos(
    status: Optional[str] = None,
    vendor_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    _=Depends(get_current_admin),
):
    query = {}
    if status:
        query['status'] = status
    if vendor_id:
        query['vendor_id'] = vendor_id

    total = await db.erp_purchase_orders.count_documents(query)
    pos = await db.erp_purchase_orders.find(query, {'_id': 0}).sort('created_at', -1).skip(skip).limit(limit).to_list(limit)
    return {'purchase_orders': pos, 'total': total}


@router.put('/erp/purchase-orders/{po_id}')
async def erp_update_po(po_id: str, body: ERPPurchaseOrderIn, _=Depends(get_current_admin)):
    update = body.model_dump()
    update['items'] = [item for item in update.get('items', [])]
    update['total_amount'] = sum(item['quantity'] * item['unit_price'] for item in update.get('items', []))
    update['updated_at'] = _now()
    result = await db.erp_purchase_orders.update_one({'id': po_id}, {'$set': update})
    if result.matched_count == 0:
        raise HTTPException(404, 'Purchase order not found')
    po = await db.erp_purchase_orders.find_one({'id': po_id}, {'_id': 0})
    return po


@router.post('/erp/purchase-orders/{po_id}/receive')
async def erp_receive_po(po_id: str, body: ERPReceiveIn, _=Depends(get_current_admin)):
    po = await db.erp_purchase_orders.find_one({'id': po_id}, {'_id': 0})
    if not po:
        raise HTTPException(404, 'Purchase order not found')

    for item in body.received_items:
        movement = {
            'id': _uid(),
            'product_id': item.get('product_id', ''),
            'product_name': item.get('product_name', ''),
            'warehouse_id': body.warehouse_id,
            'quantity': item.get('quantity', 0),
            'unit_price': item.get('unit_price', 0),
            'type': 'inbound',
            'reference': f'PO-{po_id}',
            'notes': f'Received against PO {po_id}',
            'created_at': _now(),
        }
        await db.erp_stock_movements.insert_one(movement)

        existing_product = await db.erp_products.find_one({'id': item.get('product_id', '')})
        if existing_product:
            new_stock = existing_product.get('stock', 0) + item.get('quantity', 0)
            await db.erp_products.update_one(
                {'id': item.get('product_id', '')},
                {'$set': {'stock': new_stock, 'updated_at': _now()}}
            )
        else:
            await db.erp_products.insert_one({
                'id': _uid(),
                'name': item.get('product_name', ''),
                'sku': item.get('product_id', ''),
                'stock': item.get('quantity', 0),
                'price': item.get('unit_price', 0),
                'created_at': _now(),
                'updated_at': _now(),
            })

    await db.erp_purchase_orders.update_one(
        {'id': po_id},
        {'$set': {'status': 'received', 'updated_at': _now()}}
    )
    return {'status': 'received', 'po_id': po_id, 'items_received': len(body.received_items)}


@router.get('/erp/stock-movements')
async def erp_list_stock_movements(
    product_id: Optional[str] = None,
    warehouse_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    _=Depends(get_current_admin),
):
    query = {}
    if product_id:
        query['product_id'] = product_id
    if warehouse_id:
        query['warehouse_id'] = warehouse_id
    if start_date:
        query.setdefault('created_at', {})['$gte'] = start_date
    if end_date:
        query.setdefault('created_at', {})['$lte'] = end_date

    total = await db.erp_stock_movements.count_documents(query)
    movements = await db.erp_stock_movements.find(query, {'_id': 0}).sort('created_at', -1).skip(skip).limit(limit).to_list(limit)
    return {'movements': movements, 'total': total}


@router.post('/erp/stock-movements/transfer')
async def erp_stock_transfer(body: ERPStockTransferIn, _=Depends(get_current_admin)):
    outbound = {
        'id': _uid(),
        'product_id': body.product_id,
        'warehouse_id': body.from_warehouse_id,
        'quantity': -abs(body.quantity),
        'type': 'transfer_out',
        'reference': f'TRANSFER-{body.to_warehouse_id}',
        'notes': body.notes or f'Transfer to {body.to_warehouse_id}',
        'created_at': _now(),
    }
    inbound = {
        'id': _uid(),
        'product_id': body.product_id,
        'warehouse_id': body.to_warehouse_id,
        'quantity': abs(body.quantity),
        'type': 'transfer_in',
        'reference': f'TRANSFER-{body.from_warehouse_id}',
        'notes': body.notes or f'Transfer from {body.from_warehouse_id}',
        'created_at': _now(),
    }
    await db.erp_stock_movements.insert_many([outbound, inbound])
    return {'status': 'transferred', 'product_id': body.product_id, 'quantity': body.quantity}


@router.get('/erp/stock-levels')
async def erp_stock_levels(_=Depends(get_current_admin)):
    products = await db.erp_products.find({}, {'_id': 0}).to_list(10000)
    warehouses = await db.erp_warehouses.find({}, {'_id': 0}).to_list(1000)

    stock_levels = []
    for product in products:
        wh_stock = {}
        for wh in warehouses:
            movements = await db.erp_stock_movements.find({
                'product_id': product.get('id', product.get('sku', '')),
                'warehouse_id': wh['id'],
            }, {'_id': 0}).to_list(10000)
            net = sum(m.get('quantity', 0) for m in movements)
            if net > 0:
                wh_stock[wh['id']] = {'name': wh['name'], 'quantity': net}

        total_stock = sum(s['quantity'] for s in wh_stock.values())
        stock_levels.append({
            'product_id': product.get('id', ''),
            'product_name': product.get('name', ''),
            'sku': product.get('sku', ''),
            'total_stock': total_stock,
            'warehouse_breakdown': wh_stock,
        })

    return {'stock_levels': stock_levels}


@router.get('/erp/low-stock')
async def erp_low_stock(_=Depends(get_current_admin)):
    products = await db.erp_products.find({}, {'_id': 0}).to_list(10000)
    low_stock = []
    for product in products:
        reorder_point = product.get('reorder_point', 10)
        current_stock = product.get('stock', 0)
        if current_stock <= reorder_point:
            low_stock.append({
                'product_id': product.get('id', ''),
                'product_name': product.get('name', ''),
                'sku': product.get('sku', ''),
                'current_stock': current_stock,
                'reorder_point': reorder_point,
                'deficit': reorder_point - current_stock,
            })
    return {'low_stock_products': low_stock, 'count': len(low_stock)}


@router.post('/erp/vendors')
async def erp_create_vendor(body: ERPVendorIn, _=Depends(get_current_admin)):
    doc = {
        'id': _uid(),
        **body.model_dump(),
        'rating': 0.0,
        'total_orders': 0,
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.erp_vendors.insert_one(doc)
    return doc


@router.get('/erp/vendors')
async def erp_list_vendors(_=Depends(get_current_admin)):
    vendors = await db.erp_vendors.find({}, {'_id': 0}).to_list(1000)
    return {'vendors': vendors}


@router.get('/erp/dashboard')
async def erp_dashboard(_=Depends(get_current_admin)):
    products = await db.erp_products.find({}, {'_id': 0}).to_list(10000)
    total_inventory_value = sum(p.get('stock', 0) * p.get('price', 0) for p in products)

    pending_pos = await db.erp_purchase_orders.count_documents({'status': {'$in': ['draft', 'sent']}})

    low_stock_count = len([p for p in products if p.get('stock', 0) <= p.get('reorder_point', 10)])

    vendors = await db.erp_vendors.find({}, {'_id': 0}).to_list(1000)
    vendor_performance = {}
    for v in vendors:
        vendor_performance[v.get('name', v.get('id', ''))] = {
            'total_orders': v.get('total_orders', 0),
            'rating': v.get('rating', 0),
            'lead_time_days': v.get('lead_time_days', 0),
        }

    lead_times = [v.get('lead_time_days', 0) for v in vendors if v.get('lead_time_days', 0) > 0]
    lead_time_avg = sum(lead_times) / len(lead_times) if lead_times else 0

    return {
        'total_inventory_value': round(total_inventory_value, 2),
        'pending_POs': pending_pos,
        'stock_alerts': low_stock_count,
        'vendor_performance': vendor_performance,
        'lead_time_avg': round(lead_time_avg, 1),
    }


# ═══════════════════════════════════════════════════════════════════
#  HRMS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

HRMS_COLLECTIONS = ['hrms_employees', 'hrms_departments', 'hrms_attendance', 'hrms_leave_requests', 'hrms_payroll', 'hrms_performance']


@router.post('/hrms/init')
async def hrms_init(_=Depends(get_current_admin)):
    collections_status = {}
    for coll in HRMS_COLLECTIONS:
        existing = await db.list_collection_names()
        if coll not in existing:
            await db.create_collection(coll)
        collections_status[coll] = 'ready'
    return {'status': 'initialized', 'collections': collections_status}


@router.post('/hrms/employees')
async def hrms_create_employee(body: HRMSEmployeeIn, _=Depends(get_current_admin)):
    doc = {
        'id': _uid(),
        **body.model_dump(),
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.hrms_employees.insert_one(doc)
    return doc


@router.get('/hrms/employees')
async def hrms_list_employees(
    department_id: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    _=Depends(get_current_admin),
):
    query = {}
    if department_id:
        query['department_id'] = department_id
    if status:
        query['status'] = status
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'email': {'$regex': search, '$options': 'i'}},
            {'position': {'$regex': search, '$options': 'i'}},
        ]

    total = await db.hrms_employees.count_documents(query)
    employees = await db.hrms_employees.find(query, {'_id': 0}).sort('created_at', -1).skip(skip).limit(limit).to_list(limit)
    return {'employees': employees, 'total': total}


@router.put('/hrms/employees/{employee_id}')
async def hrms_update_employee(employee_id: str, body: HRMSEmployeeIn, _=Depends(get_current_admin)):
    update = body.model_dump()
    update['updated_at'] = _now()
    result = await db.hrms_employees.update_one({'id': employee_id}, {'$set': update})
    if result.matched_count == 0:
        raise HTTPException(404, 'Employee not found')
    emp = await db.hrms_employees.find_one({'id': employee_id}, {'_id': 0})
    return emp


@router.post('/hrms/departments')
async def hrms_create_department(body: HRMSDepartmentIn, _=Depends(get_current_admin)):
    doc = {
        'id': _uid(),
        **body.model_dump(),
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.hrms_departments.insert_one(doc)
    return doc


@router.get('/hrms/departments')
async def hrms_list_departments(_=Depends(get_current_admin)):
    departments = await db.hrms_departments.find({}, {'_id': 0}).to_list(1000)
    for dept in departments:
        head_count = await db.hrms_employees.count_documents({'department_id': dept['id']})
        dept['head_count'] = head_count
    return {'departments': departments}


@router.post('/hrms/attendance')
async def hrms_mark_attendance(body: HRMSAttendanceIn, _=Depends(get_current_admin)):
    existing = await db.hrms_attendance.find_one({
        'employee_id': body.employee_id,
        'date': body.date,
    })
    if existing:
        update = body.model_dump()
        update['updated_at'] = _now()
        await db.hrms_attendance.update_one(
            {'employee_id': body.employee_id, 'date': body.date},
            {'$set': update}
        )
        updated = await db.hrms_attendance.find_one({'employee_id': body.employee_id, 'date': body.date}, {'_id': 0})
        return updated

    doc = {
        'id': _uid(),
        **body.model_dump(),
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.hrms_attendance.insert_one(doc)
    return doc


@router.get('/hrms/attendance')
async def hrms_list_attendance(
    employee_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    _=Depends(get_current_admin),
):
    query = {}
    if employee_id:
        query['employee_id'] = employee_id
    if status:
        query['status'] = status
    if start_date:
        query.setdefault('date', {})['$gte'] = start_date
    if end_date:
        query.setdefault('date', {})['$lte'] = end_date

    total = await db.hrms_attendance.count_documents(query)
    records = await db.hrms_attendance.find(query, {'_id': 0}).sort('date', -1).skip(skip).limit(limit).to_list(limit)
    return {'attendance': records, 'total': total}


@router.get('/hrms/attendance/summary/{employee_id}')
async def hrms_attendance_summary(employee_id: str, month: Optional[int] = None, year: Optional[int] = None, _=Depends(get_current_admin)):
    now = datetime.now(timezone.utc)
    target_month = month or now.month
    target_year = year or now.year

    start_date = f'{target_year}-{target_month:02d}-01'
    if target_month == 12:
        end_date = f'{target_year + 1}-01-01'
    else:
        end_date = f'{target_year}-{target_month + 1:02d}-01'

    records = await db.hrms_attendance.find({
        'employee_id': employee_id,
        'date': {'$gte': start_date, '$lt': end_date},
    }, {'_id': 0}).to_list(100)

    summary = {'present': 0, 'absent': 0, 'half_day': 0, 'remote': 0, 'leave': 0, 'total_days': len(records)}
    for rec in records:
        status = rec.get('status', 'absent')
        if status in summary:
            summary[status] += 1

    return {'employee_id': employee_id, 'month': target_month, 'year': target_year, 'summary': summary}


@router.post('/hrms/leave-requests')
async def hrms_create_leave(body: HRMSLeaveRequestIn, _=Depends(get_current_admin)):
    doc = {
        'id': _uid(),
        **body.model_dump(),
        'status': 'pending',
        'approved_by': None,
        'rejection_reason': None,
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.hrms_leave_requests.insert_one(doc)
    return doc


@router.put('/hrms/leave-requests/{leave_id}/approve')
async def hrms_approve_leave(leave_id: str, _=Depends(get_current_admin)):
    leave = await db.hrms_leave_requests.find_one({'id': leave_id}, {'_id': 0})
    if not leave:
        raise HTTPException(404, 'Leave request not found')

    await db.hrms_leave_requests.update_one(
        {'id': leave_id},
        {'$set': {'status': 'approved', 'updated_at': _now()}}
    )

    start = leave.get('start_date', '')
    end = leave.get('end_date', '')
    employee_id = leave.get('employee_id', '')
    if start and end and employee_id:
        current = datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
        while current <= end_dt:
            date_str = current.strftime('%Y-%m-%d')
            existing = await db.hrms_attendance.find_one({'employee_id': employee_id, 'date': date_str})
            if existing:
                await db.hrms_attendance.update_one(
                    {'employee_id': employee_id, 'date': date_str},
                    {'$set': {'status': 'leave', 'updated_at': _now()}}
                )
            else:
                await db.hrms_attendance.insert_one({
                    'id': _uid(),
                    'employee_id': employee_id,
                    'date': date_str,
                    'check_in': None,
                    'check_out': None,
                    'status': 'leave',
                    'created_at': _now(),
                    'updated_at': _now(),
                })
            current = datetime.fromisoformat(current.strftime('%Y-%m-%d')).replace(tzinfo=None)
            current = datetime(current.year, current.month, current.day + 1) if current.day < 28 else current.replace(day=1, month=current.month + 1 if current.month < 12 else 1, year=current.year + 1 if current.month == 12 else current.year)

    return {'status': 'approved', 'leave_id': leave_id}


@router.put('/hrms/leave-requests/{leave_id}/reject')
async def hrms_reject_leave(leave_id: str, reason: Optional[str] = None, _=Depends(get_current_admin)):
    leave = await db.hrms_leave_requests.find_one({'id': leave_id}, {'_id': 0})
    if not leave:
        raise HTTPException(404, 'Leave request not found')

    await db.hrms_leave_requests.update_one(
        {'id': leave_id},
        {'$set': {'status': 'rejected', 'rejection_reason': reason, 'updated_at': _now()}}
    )
    return {'status': 'rejected', 'leave_id': leave_id}


@router.get('/hrms/leave-requests')
async def hrms_list_leaves(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    _=Depends(get_current_admin),
):
    query = {}
    if employee_id:
        query['employee_id'] = employee_id
    if status:
        query['status'] = status

    total = await db.hrms_leave_requests.count_documents(query)
    leaves = await db.hrms_leave_requests.find(query, {'_id': 0}).sort('created_at', -1).skip(skip).limit(limit).to_list(limit)
    return {'leave_requests': leaves, 'total': total}


@router.post('/hrms/payroll')
async def hrms_generate_payroll(body: HRMSPayrollIn, _=Depends(get_current_admin)):
    doc = {
        'id': _uid(),
        **body.model_dump(),
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.hrms_payroll.insert_one(doc)
    return doc


@router.get('/hrms/payroll')
async def hrms_list_payroll(
    employee_id: Optional[str] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    _=Depends(get_current_admin),
):
    query = {}
    if employee_id:
        query['employee_id'] = employee_id
    if month:
        query['month'] = month
    if year:
        query['year'] = year
    if status:
        query['status'] = status

    total = await db.hrms_payroll.count_documents(query)
    records = await db.hrms_payroll.find(query, {'_id': 0}).sort('created_at', -1).skip(skip).limit(limit).to_list(limit)
    return {'payroll': records, 'total': total}


@router.post('/hrms/performance')
async def hrms_add_performance(body: HRMSPerformanceIn, _=Depends(get_current_admin)):
    doc = {
        'id': _uid(),
        **body.model_dump(),
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.hrms_performance.insert_one(doc)
    return doc


@router.get('/hrms/performance/{employee_id}')
async def hrms_performance_history(employee_id: str, _=Depends(get_current_admin)):
    reviews = await db.hrms_performance.find({'employee_id': employee_id}, {'_id': 0}).sort('created_at', -1).to_list(100)
    return {'employee_id': employee_id, 'reviews': reviews}


@router.get('/hrms/dashboard')
async def hrms_dashboard(_=Depends(get_current_admin)):
    total_employees = await db.hrms_employees.count_documents({})

    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    attendance_today = await db.hrms_attendance.count_documents({'date': today_str, 'status': {'$ne': 'absent'}})

    pending_leaves = await db.hrms_leave_requests.count_documents({'status': 'pending'})

    now = datetime.now(timezone.utc)
    payroll_this_month = await db.hrms_payroll.count_documents({'month': now.month, 'year': now.year})
    payroll_total = 0
    if payroll_this_month > 0:
        payroll_records = await db.hrms_payroll.find({'month': now.month, 'year': now.year}, {'_id': 0}).to_list(10000)
        payroll_total = sum(r.get('net_pay', 0) for r in payroll_records)

    perf_reviews = await db.hrms_performance.find({}, {'_id': 0}).to_list(10000)
    avg_performance = 0.0
    if perf_reviews:
        ratings = [r.get('rating', 0) for r in perf_reviews if r.get('rating', 0) > 0]
        avg_performance = sum(ratings) / len(ratings) if ratings else 0.0

    departments = await db.hrms_departments.find({}, {'_id': 0}).to_list(1000)
    department_distribution = {}
    for dept in departments:
        count = await db.hrms_employees.count_documents({'department_id': dept['id']})
        department_distribution[dept['name']] = count

    return {
        'total_employees': total_employees,
        'attendance_today': attendance_today,
        'pending_leaves': pending_leaves,
        'payroll_this_month': payroll_this_month,
        'payroll_total_this_month': payroll_total,
        'avg_performance': round(avg_performance, 2),
        'department_distribution': department_distribution,
    }


# ═══════════════════════════════════════════════════════════════════
#  BOOKING ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

BOOKING_COLLECTIONS = ['booking_services', 'booking_slots', 'booking_appointments', 'booking_staff']


@router.post('/booking/init')
async def booking_init(_=Depends(get_current_admin)):
    collections_status = {}
    for coll in BOOKING_COLLECTIONS:
        existing = await db.list_collection_names()
        if coll not in existing:
            await db.create_collection(coll)
        collections_status[coll] = 'ready'
    return {'status': 'initialized', 'collections': collections_status}


@router.post('/booking/services')
async def booking_create_service(body: BookingServiceIn, _=Depends(get_current_admin)):
    doc = {
        'id': _uid(),
        **body.model_dump(),
        'is_active': True,
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.booking_services.insert_one(doc)
    return doc


@router.get('/booking/services')
async def booking_list_services(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    _=Depends(get_current_admin),
):
    query = {}
    if category:
        query['category'] = category
    if is_active is not None:
        query['is_active'] = is_active

    services = await db.booking_services.find(query, {'_id': 0}).sort('created_at', -1).to_list(1000)
    return {'services': services}


@router.post('/booking/slots')
async def booking_create_slot(body: BookingSlotIn, _=Depends(get_current_admin)):
    doc = {
        'id': _uid(),
        **body.model_dump(),
        'booked_count': 0,
        'is_available': True,
        'created_at': _now(),
    }
    await db.booking_slots.insert_one(doc)
    return doc


@router.get('/booking/slots')
async def booking_list_slots(
    service_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    date: Optional[str] = None,
    available_only: bool = False,
    _=Depends(get_current_admin),
):
    query = {}
    if service_id:
        query['service_id'] = service_id
    if staff_id:
        query['staff_id'] = staff_id
    if date:
        query['date'] = date
    if available_only:
        query['is_available'] = True

    slots = await db.booking_slots.find(query, {'_id': 0}).sort('date', 1).sort('start_time', 1).to_list(1000)
    return {'slots': slots}


@router.post('/booking/appointments')
async def booking_create_appointment(body: BookingAppointmentIn, _=Depends(get_current_admin)):
    slot = await db.booking_slots.find_one({'id': body.slot_id}, {'_id': 0})
    if not slot:
        raise HTTPException(404, 'Slot not found')

    service = await db.booking_services.find_one({'id': body.service_id}, {'_id': 0})
    max_per_slot = service.get('max_per_slot', 1) if service else 1
    booked_count = slot.get('booked_count', 0)

    if booked_count >= max_per_slot:
        raise HTTPException(400, 'Slot is fully booked')

    doc = {
        'id': _uid(),
        **body.model_dump(),
        'staff_id': slot.get('staff_id'),
        'date': slot.get('date'),
        'start_time': slot.get('start_time'),
        'end_time': slot.get('end_time'),
        'status': 'confirmed',
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.booking_appointments.insert_one(doc)

    new_count = booked_count + 1
    await db.booking_slots.update_one(
        {'id': body.slot_id},
        {'$set': {'booked_count': new_count, 'is_available': new_count < max_per_slot}}
    )

    return doc


@router.get('/booking/appointments')
async def booking_list_appointments(
    date: Optional[str] = None,
    status: Optional[str] = None,
    service_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    _=Depends(get_current_admin),
):
    query = {}
    if date:
        query['date'] = date
    if status:
        query['status'] = status
    if service_id:
        query['service_id'] = service_id

    total = await db.booking_appointments.count_documents(query)
    appointments = await db.booking_appointments.find(query, {'_id': 0}).sort('date', -1).skip(skip).limit(limit).to_list(limit)
    return {'appointments': appointments, 'total': total}


@router.put('/booking/appointments/{appointment_id}/confirm')
async def booking_confirm_appointment(appointment_id: str, _=Depends(get_current_admin)):
    result = await db.booking_appointments.update_one(
        {'id': appointment_id},
        {'$set': {'status': 'confirmed', 'updated_at': _now()}}
    )
    if result.matched_count == 0:
        raise HTTPException(404, 'Appointment not found')
    appt = await db.booking_appointments.find_one({'id': appointment_id}, {'_id': 0})
    return appt


@router.put('/booking/appointments/{appointment_id}/cancel')
async def booking_cancel_appointment(appointment_id: str, _=Depends(get_current_admin)):
    appt = await db.booking_appointments.find_one({'id': appointment_id}, {'_id': 0})
    if not appt:
        raise HTTPException(404, 'Appointment not found')

    await db.booking_appointments.update_one(
        {'id': appointment_id},
        {'$set': {'status': 'cancelled', 'updated_at': _now()}}
    )

    slot_id = appt.get('slot_id')
    if slot_id:
        slot = await db.booking_slots.find_one({'id': slot_id}, {'_id': 0})
        if slot:
            new_count = max(0, slot.get('booked_count', 1) - 1)
            service = await db.booking_services.find_one({'id': appt.get('service_id', '')}, {'_id': 0})
            max_per_slot = service.get('max_per_slot', 1) if service else 1
            await db.booking_slots.update_one(
                {'id': slot_id},
                {'$set': {'booked_count': new_count, 'is_available': True}}
            )

    return {'status': 'cancelled', 'appointment_id': appointment_id}


@router.get('/booking/calendar')
async def booking_calendar(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    _=Depends(get_current_admin),
):
    query = {'status': {'$ne': 'cancelled'}}
    if start_date:
        query.setdefault('date', {})['$gte'] = start_date
    if end_date:
        query.setdefault('date', {})['$lte'] = end_date

    appointments = await db.booking_appointments.find(query, {'_id': 0}).sort('date', 1).to_list(5000)

    calendar = {}
    for appt in appointments:
        date = appt.get('date', 'unknown')
        if date not in calendar:
            calendar[date] = []
        calendar[date].append(appt)

    return {'calendar': calendar, 'total_appointments': len(appointments)}


@router.get('/booking/dashboard')
async def booking_dashboard(_=Depends(get_current_admin)):
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')

    today_appointments = await db.booking_appointments.count_documents({
        'date': today_str,
        'status': {'$ne': 'cancelled'},
    })

    upcoming = await db.booking_appointments.count_documents({
        'date': {'$gte': today_str},
        'status': {'$ne': 'cancelled'},
    })

    services = await db.booking_services.find({}, {'_id': 0}).to_list(1000)
    slots_today = await db.booking_slots.find({'date': today_str}, {'_id': 0}).to_list(1000)
    total_capacity = sum(s.get('capacity', 1) for s in slots_today)
    total_booked = sum(s.get('booked_count', 0) for s in slots_today)
    utilization_rate = (total_booked / total_capacity * 100) if total_capacity > 0 else 0.0

    appointments_today = await db.booking_appointments.find({
        'date': today_str,
        'status': {'$ne': 'cancelled'},
    }, {'_id': 0}).to_list(1000)
    revenue_today = 0.0
    for appt in appointments_today:
        service = await db.booking_services.find_one({'id': appt.get('service_id', '')}, {'_id': 0})
        if service:
            revenue_today += service.get('price', 0)

    service_counts = {}
    all_appts = await db.booking_appointments.find({'status': {'$ne': 'cancelled'}}, {'_id': 0}).to_list(10000)
    for appt in all_appts:
        sid = appt.get('service_id', 'unknown')
        service_counts[sid] = service_counts.get(sid, 0) + 1

    popular_service = max(service_counts, key=service_counts.get) if service_counts else None
    if popular_service:
        svc = await db.booking_services.find_one({'id': popular_service}, {'_id': 0})
        popular_service = svc.get('name', popular_service) if svc else popular_service

    return {
        'today_appointments': today_appointments,
        'upcoming': upcoming,
        'utilization_rate': round(utilization_rate, 2),
        'revenue_today': round(revenue_today, 2),
        'popular_service': popular_service,
    }
