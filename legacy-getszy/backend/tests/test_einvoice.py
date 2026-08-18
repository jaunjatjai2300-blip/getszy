"""Tests for GST e-Invoicing (Tier 3) — IRN + payload assembly (no NIC call)."""
import os
import asyncio

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

import einvoice  # noqa: E402
import routes_einvoice  # noqa: E402


def test_compute_irn_is_deterministic_and_64_hex():
    a = einvoice.compute_irn('27AAAAA0000A1ZC', 'INV', 'GST-2025-ABC')
    b = einvoice.compute_irn('27AAAAA0000A1ZC', 'INV', 'GST-2025-ABC')
    assert a == b
    assert len(a) == 64
    int(a, 16)  # valid hex


def test_build_einvoice_payload_shape():
    inv = {
        'invoice_number': 'GST-2025-ABC', 'customer_name': 'Neo', 'customer_gstin': '07BBBBB0000B1Z5',
        'total': 1180.0, 'gst_amount': 180.0, 'cgst_amount': 90.0, 'sgst_amount': 90.0, 'igst_amount': 0.0,
        'gst_rate': 18, 'items': [{'description': 'Widget', 'qty': 1, 'rate': 1000, 'amount': 1000}],
        'created_at': '2025-06-15T10:00:00+00:00',
    }
    seller = {'company_gstin': '27AAAAA0000A1ZC', 'company_name': 'Getszy', 'company_address': 'Mumbai'}
    p = einvoice.build_einvoice(inv, seller)
    assert p['irn']
    assert p['DocDtls']['No'] == 'GST-2025-ABC'
    assert p['ValDtls']['TotInvVal'] == 1180.0
    assert p['ValDtls']['AssVal'] == 1000.0
    assert p['SellerDtls']['Gstin'] == '27AAAAA0000A1ZC'
    assert p['BuyerDtls']['Gstin'] == '07BBBBB0000B1Z5'
    assert p['TranDtls']['SupTyp'] == 'B2B'
    assert p['ItemList'][0]['HsnCd'] == '999999'  # default HSN for unspecified items


def test_build_einvoice_uses_item_hsn_when_provided():
    inv = {
        'invoice_number': 'GST-2025-HSN', 'customer_gstin': '07BBBBB0000B1Z5',
        'total': 1180.0, 'gst_amount': 180.0, 'cgst_amount': 90.0, 'sgst_amount': 90.0, 'igst_amount': 0.0,
        'gst_rate': 18, 'items': [{'description': 'Course', 'hsn': '999293', 'qty': 1, 'rate': 1000, 'amount': 1000}],
        'created_at': '2025-06-15T10:00:00+00:00',
    }
    seller = {'company_gstin': '27AAAAA0000A1ZC', 'company_name': 'Getszy'}
    p = einvoice.build_einvoice(inv, seller)
    assert p['ItemList'][0]['HsnCd'] == '999293'


class FakeColl:
    def __init__(self, data=None):
        self._data = data
        self.inserted = []

    async def find_one(self, q, p=None):
        return self._data

    async def insert_one(self, doc):
        self.inserted.append(doc)
        return None


class FakeDB:
    def __init__(self, inv, seller):
        self.gs_invoices = FakeColl(inv)
        self.gs_gst_config = FakeColl(seller)
        self.e_invoices = FakeColl()


def test_generate_einvoice_stores_record():
    inv = {'invoice_number': 'GST-2025-ABC', 'customer_name': 'Neo', 'gst_rate': 18,
           'total': 1180.0, 'gst_amount': 180.0, 'cgst_amount': 90.0, 'sgst_amount': 90.0, 'igst_amount': 0.0,
           'items': [{'description': 'Widget', 'qty': 1, 'rate': 1000, 'amount': 1000}], 'created_at': '2025-06-15T10:00:00+00:00'}
    seller = {'company_gstin': '27AAAAA0000A1ZC', 'company_name': 'Getszy'}
    routes_einvoice.db = FakeDB(inv, seller)
    res = asyncio.run(routes_einvoice.generate_einvoice(
        routes_einvoice.GenerateIn(invoice_number='GST-2025-ABC'), {'email': 'a@admin'}))
    assert res['ok'] is True
    assert res['irn']
    assert len(routes_einvoice.db.e_invoices.inserted) == 1
