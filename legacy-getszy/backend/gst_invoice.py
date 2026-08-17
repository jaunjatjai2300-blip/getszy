"""GST invoice helpers (Tier 3 — Indian compliance).

Computes CGST/SGST (intra-state) vs IGST (inter-state) split from GSTIN
state codes and generates invoice documents. Used by the manual invoice
generator and by auto-invoice-on-order.
"""
import uuid
from datetime import datetime, timezone

from db import db


def _id():
    return uuid.uuid4().hex


def _iso():
    return datetime.now(timezone.utc).isoformat()


def state_code(gstin: str):
    if gstin and len(gstin) >= 2 and gstin[:2].isdigit():
        return gstin[:2]
    return None


def compute_gst(subtotal: float, gst_rate: float, seller_gstin: str = None, customer_gstin: str = None):
    """Return CGST/SGST/IGST amounts for a subtotal + GST rate."""
    gst_amount = round(float(subtotal) * float(gst_rate) / 100, 2)
    seller_state = state_code(seller_gstin)
    cust_state = state_code(customer_gstin)
    if seller_state and cust_state and seller_state != cust_state:
        return {'cgst_amount': 0.0, 'sgst_amount': 0.0, 'igst_amount': gst_amount}
    half = round(gst_amount / 2, 2)
    return {'cgst_amount': half, 'sgst_amount': half, 'igst_amount': 0.0}


async def create_invoice_from_order(order: dict):
    """Auto-generate a GST invoice when an order is placed."""
    cfg = await db.gs_gst_config.find_one({}, {'_id': 0}) or {}
    gst_rate = cfg.get('default_rate', 18)
    subtotal = order.get('subtotal', order.get('total', 0)) or 0
    split = compute_gst(subtotal, gst_rate, cfg.get('company_gstin'), order.get('customer_gstin'))
    gst_amount = round(split['cgst_amount'] + split['sgst_amount'] + split['igst_amount'], 2)
    doc = {
        'id': _id(),
        'invoice_number': f"GST-{datetime.now().strftime('%Y%m')}-{_id()[:6].upper()}",
        'order_id': order.get('id'),
        'order_number': order.get('order_number'),
        'customer_name': order.get('customer_name', ''),
        'customer_email': order.get('customer_email', ''),
        'customer_gstin': order.get('customer_gstin', ''),
        'seller_name': cfg.get('company_name', ''),
        'seller_gstin': cfg.get('company_gstin', ''),
        'seller_address': cfg.get('company_address', ''),
        'items': order.get('items', []),
        'subtotal': subtotal,
        'gst_rate': gst_rate,
        'cgst_amount': split['cgst_amount'],
        'sgst_amount': split['sgst_amount'],
        'igst_amount': split['igst_amount'],
        'gst_amount': gst_amount,
        'total': round(subtotal + gst_amount, 2),
        'status': 'issued',
        'created_at': _iso(),
        'notes': 'Auto-generated from order',
        'auto': True,
    }
    await db.gs_invoices.insert_one(doc)
    return doc
