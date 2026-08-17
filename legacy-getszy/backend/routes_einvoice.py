"""GST e-Invoicing endpoints (Tier 3)."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_admin
from db import db
from einvoice import build_einvoice, compute_irn

router = APIRouter(prefix='/admin/einvoice', tags=['einvoice'])


class GenerateIn(BaseModel):
    invoice_number: str
    sandbox: bool = True


@router.post('/generate')
async def generate_einvoice(body: GenerateIn, _=Depends(get_current_admin)):
    inv = await db.gs_invoices.find_one({'invoice_number': body.invoice_number}, {'_id': 0})
    if not inv:
        raise HTTPException(404, 'Invoice not found')
    seller = await db.gs_gst_config.find_one({}, {'_id': 0}) or {}
    payload = build_einvoice(inv, seller)
    doc = {
        'id': uuid.uuid4().hex,
        'invoice_number': body.invoice_number,
        'irn': payload['irn'],
        'payload': payload,
        'sandbox': body.sandbox,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.e_invoices.insert_one(doc)
    return {'ok': True, 'irn': payload['irn'], 'sandbox': body.sandbox, 'payload': payload}


@router.get('/{invoice_number}')
async def get_einvoice(invoice_number: str, _=Depends(get_current_admin)):
    doc = await db.e_invoices.find_one({'invoice_number': invoice_number}, {'_id': 0})
    if not doc:
        raise HTTPException(404, 'E-invoice not found')
    return doc


@router.get('/irn/preview')
async def irn_preview(seller_gstin: str, doc_no: str, doc_type: str = 'INV', _=Depends(get_current_admin)):
    return {'irn': compute_irn(seller_gstin, doc_type, doc_no), 'sandbox': True}
