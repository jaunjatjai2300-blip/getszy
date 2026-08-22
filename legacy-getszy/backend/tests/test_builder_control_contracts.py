import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:27017')
os.environ.setdefault('JWT_SECRET', 'test-only-builder-control-contract-secret')

from models import BuilderEvidenceItem, BuilderEvidenceUpdateIn, BuilderReleaseReviewIn, BuilderVersionIn
from routes_builder import router


def test_builder_control_models_validate_customer_review_data():
    item = BuilderEvidenceItem(claim='Starting at ₹999', source='Approved catalog', status='approved')
    body = BuilderEvidenceUpdateIn(items=[item])

    assert body.items[0].claim == 'Starting at ₹999'
    assert BuilderVersionIn(label='Approved mobile revision').label == 'Approved mobile revision'
    assert BuilderReleaseReviewIn(confirm_evidence_review=True).confirm_evidence_review is True


def test_builder_control_routes_are_registered_before_dynamic_project_route():
    paths = [route.path for route in router.routes]

    assert '/builder/projects/{pid}/controls' in paths
    assert '/builder/projects/{pid}/evidence' in paths
    assert '/builder/projects/{pid}/versions' in paths
    assert '/builder/projects/{pid}/release-review' in paths
    assert paths.index('/builder/projects/{pid}/controls') < paths.index('/builder/projects/{pid}')
