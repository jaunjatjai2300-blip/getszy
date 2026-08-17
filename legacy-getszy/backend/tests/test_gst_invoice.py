"""Behavioral tests for Tier 3 GST compliance (compute_gst + auto invoice).

Pure logic for CGST/SGST/IGST split + an end-to-end auto-invoice against a
fake DB (no Mongo needed).
Run: python -m pytest tests/test_gst_invoice.py -v
"""
import os

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

import gst_invoice  # noqa: E402


class FakeColl:
    def __init__(self, data=None):
        self.docs = []
        self._data = data or {}

    async def find_one(self, q, p=None):
        return self._data

    async def insert_one(self, doc):
        self.docs.append(doc)
        return None


class FakeDB:
    def __init__(self, cfg):
        self.gs_gst_config = FakeColl(cfg)
        self.gs_invoices = FakeColl()


def test_compute_gst_intrastate_split():
    r = gst_invoice.compute_gst(1000, 18, '27AAAAA0000A1Z5', '27BBBBB0000B1Z2')
    assert r['cgst_amount'] == 90.0 and r['sgst_amount'] == 90.0 and r['igst_amount'] == 0.0


def test_compute_gst_interstate_igst():
    r = gst_invoice.compute_gst(1000, 18, '27AAAAA0000A1Z5', '07CCCC0000C1Z3')
    assert r['igst_amount'] == 180.0 and r['cgst_amount'] == 0.0 and r['sgst_amount'] == 0.0


def test_compute_gst_no_gstin_defaults_intra():
    r = gst_invoice.compute_gst(1000, 18, '27AAAAA0000A1Z5', '')
    assert r['cgst_amount'] == 90.0 and r['sgst_amount'] == 90.0


def test_create_invoice_from_order_stores_split():
    cfg = {'company_gstin': '27AAAAA0000A1Z5', 'company_name': 'Getszy', 'default_rate': 18}
    gst_invoice.db = FakeDB(cfg)
    order = {
        'id': 'o1', 'order_number': 'ORD-1', 'customer_name': 'Neo',
        'customer_email': 'n@x.com', 'subtotal': 1000, 'total': 1049,
        'items': [{'name': 'Widget', 'price': 1000, 'quantity': 1}],
    }
    import asyncio
    doc = asyncio.run(gst_invoice.create_invoice_from_order(order))
    assert doc['invoice_number'].startswith('GST-')
    assert doc['cgst_amount'] == 90.0 and doc['sgst_amount'] == 90.0
    assert doc['gst_amount'] == 180.0
    assert doc['total'] == 1180.0
    assert doc['status'] == 'issued'
    assert doc['seller_gstin'] == '27AAAAA0000A1Z5'
