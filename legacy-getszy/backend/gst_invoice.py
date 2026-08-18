"""GST invoice helpers (Tier 3 — Indian compliance).

Computes CGST/SGST (intra-state) vs IGST (inter-state) split from GSTIN
state codes and generates invoice documents. Used by the manual invoice
generator and by auto-invoice-on-order.
"""
import re
import uuid
from datetime import datetime, timezone

from db import db


def _id():
    return uuid.uuid4().hex


def _iso():
    return datetime.now(timezone.utc).isoformat()


# ── GSTIN / PAN validation (Indian compliance) ────────────────────────────────
# A GSTIN is 15 chars: 2-digit state code + 10-char PAN + 1 entity digit +
# literal 'Z' + 1 checksum char (ISO 7064 MOD-36-2 over the first 14 chars).
_GSTIN_RE = re.compile(r'^\d{2}[A-Z]{5}\d{4}[A-Z]\dZ[0-9A-Z]$')
_PAN_RE = re.compile(r'^[A-Z]{5}\d{4}[A-Z]$')
_B36 = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'


def validate_pan(pan: str) -> bool:
    if not pan:
        return False
    return bool(_PAN_RE.match(pan.strip().upper()))


def _gstin_check_digit(body14: str) -> str:
    """Compute the ISO 7064 MOD-36-2 check character for the first 14 GSTIN chars."""
    total = 0
    factor = 1
    for ch in body14:
        val = _B36.index(ch)
        prod = val * factor
        total += sum(int(d) for d in str(prod))
        factor = 2 if factor == 1 else 1
    rem = total % 36
    check = 36 - rem if rem != 0 else 0
    return _B36[check]


def validate_gstin(gstin: str) -> bool:
    """True only for a structurally and checksum-valid GSTIN."""
    if not gstin:
        return False
    g = gstin.strip().upper()
    if not _GSTIN_RE.match(g):
        return False
    if not validate_pan(g[2:12]):
        return False
    if not (1 <= int(g[:2]) <= 37):  # valid state/UT code range
        return False
    try:
        if _gstin_check_digit(g[:14]) != g[14]:
            return False
    except Exception:
        return False
    return True


def normalize_gstin(gstin: str):
    """Return an upper-cased valid GSTIN, or '' if missing/invalid (so downstream
    logic treats an invalid customer GSTIN as B2C rather than mis-routing IGST)."""
    if not gstin:
        return ''
    g = gstin.strip().upper()
    return g if validate_gstin(g) else ''


def state_code(gstin: str):
    g = normalize_gstin(gstin)
    if g and len(g) >= 2:
        return g[:2]
    return None


def compute_gst(subtotal: float, gst_rate: float, seller_gstin: str = None, customer_gstin: str = None):
    """Return CGST/SGST/IGST amounts for a subtotal + GST rate. GSTINs are
    normalized first so malformed values degrade to B2C (intra-state) safely."""
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
    seller_gstin = normalize_gstin(cfg.get('company_gstin'))
    customer_gstin = normalize_gstin(order.get('customer_gstin'))
    split = compute_gst(subtotal, gst_rate, seller_gstin, customer_gstin)
    gst_amount = round(split['cgst_amount'] + split['sgst_amount'] + split['igst_amount'], 2)
    doc = {
        'id': _id(),
        'invoice_number': f"GST-{datetime.now().strftime('%Y%m')}-{_id()[:6].upper()}",
        'order_id': order.get('id'),
        'order_number': order.get('order_number'),
        'customer_name': order.get('customer_name', ''),
        'customer_email': order.get('customer_email', ''),
        'customer_gstin': customer_gstin,
        'seller_name': cfg.get('company_name', ''),
        'seller_gstin': seller_gstin,
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
