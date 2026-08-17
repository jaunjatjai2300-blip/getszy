"""GST e-Invoicing engine (Tier 3 — Indian compliance, "universal" for Bharat).

Computes a deterministic IRN from the invoice identity and assembles a
NIC v1.03-shaped e-invoice payload. Sandbox mode (no live NIC call) so it
works out-of-the-box; wire real NIC credentials later via config.
"""
import hashlib
import re
from datetime import datetime, timezone


def _parse_date(d):
    if not d:
        return datetime.now(timezone.utc)
    if isinstance(d, datetime):
        return d
    try:
        return datetime.fromisoformat(str(d).replace('Z', '+00:00'))
    except Exception:
        return datetime.now(timezone.utc)


def financial_year(doc_date=None):
    d = _parse_date(doc_date)
    fy_start = d.year if d.month >= 4 else d.year - 1
    return f"{str(fy_start)[2:]}{str(fy_start + 1)[2:]}"


def compute_irn(seller_gstin: str, doc_type: str, doc_no: str, doc_date=None):
    """Deterministic IRN candidate (sha256 of the NIC identity string)."""
    fy = financial_year(doc_date)
    raw = f"{seller_gstin or ''}|{fy}|{doc_type}|{doc_no or ''}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest().upper()


def _gstin_state(code: str):
    m = re.match(r'^(\d{2})', code or '')
    return m.group(1) if m else '00'


def build_einvoice(invoice: dict, seller: dict, buyer: dict = None):
    """Assemble a NIC v1.03-shaped e-invoice payload from stored documents."""
    doc_no = invoice.get('invoice_number') or invoice.get('order_number') or ''
    doc_date = _parse_date(invoice.get('created_at') or invoice.get('doc_date'))
    doc_type = 'INV'
    seller_gstin = (seller or {}).get('company_gstin', '')
    irn = compute_irn(seller_gstin, doc_type, doc_no, doc_date)

    total = float(invoice.get('total', 0) or 0)
    gst = float(invoice.get('gst_amount', 0) or 0)
    taxable = round(total - gst, 2)
    cgst = float(invoice.get('cgst_amount', 0) or 0)
    sgst = float(invoice.get('sgst_amount', 0) or 0)
    igst = float(invoice.get('igst_amount', 0) or 0)

    buyer = buyer or {}
    buyer_gstin = invoice.get('customer_gstin', '') or buyer.get('gstin', '')

    payload = {
        'Version': '1.03',
        'TranDtls': {
            'TaxSch': 'GST',
            'SupTyp': 'B2B' if buyer_gstin else 'B2C',
            'RegRev': 'N',
            'EcmGstin': None,
        },
        'DocDtls': {'Typ': doc_type, 'No': doc_no, 'Dt': doc_date.strftime('%d-%m-%Y')},
        'SellerDtls': {
            'Gstin': seller_gstin,
            'LglNm': (seller or {}).get('company_name', 'Getszy'),
            'Addr1': (seller or {}).get('company_address', ''),
            'Stcd': _gstin_state(seller_gstin),
        },
        'BuyerDtls': {
            'Gstin': buyer_gstin or None,
            'LglNm': invoice.get('customer_name', '') or buyer.get('name', ''),
            'Addr1': invoice.get('customer_email', ''),
            'Stcd': _gstin_state(buyer_gstin) if buyer_gstin else '00',
        },
        'ItemList': [
            {
                'SlNo': str(i + 1),
                'PrdDesc': it.get('description', it.get('name', 'Item')),
                'Qty': float(it.get('qty', it.get('quantity', 1)) or 1),
                'UnitPrice': round(float(it.get('rate', it.get('price', 0)) or 0), 2),
                'TotAmt': round(float(it.get('amount', 0) or 0), 2),
                'GstRt': float(invoice.get('gst_rate', 18) or 18),
            }
            for i, it in enumerate(invoice.get('items', []) or [])
        ],
        'ValDtls': {
            'AssVal': taxable,
            'CgstVal': cgst,
            'SgstVal': sgst,
            'IgstVal': igst,
            'TotInvVal': total,
        },
        'irn': irn,
        'sandbox': True,
    }
    return payload
