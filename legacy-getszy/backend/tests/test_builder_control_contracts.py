import os
import sys
import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:27017')
os.environ.setdefault('JWT_SECRET', 'test-only-builder-control-contract-secret')

from models import BuilderEvidenceItem, BuilderEvidenceUpdateIn, BuilderReleaseReviewIn, BuilderVersionIn, BuilderProjectIn
import routes_builder as builder_routes
from routes_builder import router, create_project


def test_builder_control_models_validate_customer_review_data():
    item = BuilderEvidenceItem(claim='Starting at ₹999', source='Approved catalog', status='approved')
    body = BuilderEvidenceUpdateIn(items=[item])

    assert body.items[0].claim == 'Starting at ₹999'
    assert BuilderVersionIn(label='Approved mobile revision').label == 'Approved mobile revision'
    assert BuilderReleaseReviewIn(confirm_evidence_review=True).confirm_evidence_review is True


class _ProjectCollection:
    def __init__(self):
        self.saved = []

    async def insert_one(self, document):
        self.saved.append(document)


class _BuilderDB:
    def __init__(self):
        self.builder_projects = _ProjectCollection()


@pytest.mark.asyncio
async def test_new_page_uses_managed_composition_and_saves_private_draft(monkeypatch):
    fake_db = _BuilderDB()
    charges = []

    async def fake_deduct(*args, **kwargs):
        charges.append((args, kwargs))
        return True, '', 75

    async def fake_compose(*args, **kwargs):
        return "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width'><title>Beauty Studio</title><meta name='description' content='Beauty appointments'></head><body><header><a>Book now</a></header><main><section><h1>Beauty Studio</h1></section><section><p>How it works</p></section><section><button>Book now</button></section></main><footer></footer><style>@media (max-width:600px){body{padding:1rem}} .hero{background:linear-gradient(#123,#456)}</style></body></html>"

    monkeypatch.setattr(builder_routes, 'db', fake_db)
    monkeypatch.setattr(builder_routes, 'deduct', fake_deduct)
    monkeypatch.setattr(builder_routes, 'compose_site_fast', fake_compose)
    result = await create_project(
        BuilderProjectIn(prompt='Build a beauty studio website', brief={'primary_goal': 'Book appointments', 'primary_cta': 'Book now'}),
        user={'id': 'customer-test', 'role': 'customer', 'credits': 100},
    )

    assert charges and charges[0][0][1] == 'builder_website'
    assert result['template_id'] is None
    assert fake_db.builder_projects.saved[0]['html_content'].startswith('<!DOCTYPE html>')


@pytest.mark.asyncio
async def test_failed_composition_refunds_customer_credit(monkeypatch):
    refunds = []

    async def fake_deduct(*args, **kwargs):
        return True, '', 75

    async def fail_compose(*args, **kwargs):
        raise builder_routes.ProfessionalCompositionError('quality failure')

    async def fake_refund(*args, **kwargs):
        refunds.append((args, kwargs))
        return 100

    monkeypatch.setattr(builder_routes, 'deduct', fake_deduct)
    monkeypatch.setattr(builder_routes, 'compose_site_fast', fail_compose)
    monkeypatch.setattr(builder_routes, 'refund', fake_refund)

    with pytest.raises(HTTPException) as exc:
        await create_project(BuilderProjectIn(prompt='Build a beauty studio website'), user={'id': 'customer-test', 'role': 'customer', 'credits': 100})

    assert exc.value.status_code == 422
    assert refunds and refunds[0][1]['reason'] == 'professional_composition_quality_failed'


def test_builder_control_routes_are_registered_before_dynamic_project_route():
    paths = [route.path for route in router.routes]

    assert '/builder/projects/{pid}/controls' in paths
    assert '/builder/projects/{pid}/evidence' in paths
    assert '/builder/projects/{pid}/versions' in paths
    assert '/builder/projects/{pid}/release-review' in paths
    assert paths.index('/builder/projects/{pid}/controls') < paths.index('/builder/projects/{pid}')
