"""Smoke test: proves the previously-missing admin endpoints are registered.

This does NOT require a live server, DB, or credentials — it imports the
router modules and asserts every gap route exists with the right HTTP method.
Run with: python -m pytest tests/test_admin_gap_routes.py -v
"""
import os

os.environ.setdefault('MONGO_URL', 'mongodb://localhost:27017')
os.environ.setdefault('JWT_SECRET', 'test-secret-for-tests')

import routes_enterprise_security  # noqa: E402
import routes_admin  # noqa: E402
import routes_growth  # noqa: E402
import routes_learning_platform  # noqa: E402
import routes_operations  # noqa: E402
import routes_cart_orders  # noqa: E402
import routes_saas_builder  # noqa: E402
import routes_credits  # noqa: E402
import routes_extras  # noqa: E402
import routes_ai_platform  # noqa: E402
import routes_api_builder  # noqa: E402
import routes_commerce_extra  # noqa: E402
import routes_avatar  # noqa: E402
import routes_neo_ops  # noqa: E402


def _routes(router):
    out = []
    for r in router.routes:
        methods = getattr(r, 'methods', None) or set()
        for m in methods:
            out.append((m, r.path))
    return out


CHECKS = [
    (routes_enterprise_security.router, 'GET', '/admin/enterprise-security/threats'),
    (routes_admin.router, 'GET', '/admin/env-health'),
    (routes_growth.router, 'GET', '/admin/growth/referral-leaderboard'),
    (routes_learning_platform.router, 'GET', '/admin/learning-platform/modules'),
    (routes_operations.router, 'GET', '/admin/ops/request-logs'),
    (routes_cart_orders.router, 'GET', '/admin/orders/refunds'),
    (routes_saas_builder.router, 'GET', '/admin/saas-builder/projects'),
    (routes_credits.router, 'GET', '/credits/admin/transactions'),
    (routes_extras.router, 'GET', '/extras/quiz/list'),
    (routes_extras.router, 'GET', '/extras/certificates/list'),
    (routes_ai_platform.router, 'POST', '/admin/ai-platform/playground'),
    (routes_api_builder.router, 'POST', '/admin/api-builder/generate'),
    (routes_commerce_extra.router, 'POST', '/admin/settings/gst'),
    (routes_avatar.router, 'POST', '/avatar/generate-image'),
    (routes_avatar.router, 'POST', '/avatar/clone-voice'),
    (routes_avatar.router, 'POST', '/avatar/talking-head'),
    (routes_cart_orders.router, 'POST', '/admin/orders/refund'),
    (routes_neo_ops.router, 'POST', '/admin/neo/insight'),
    (routes_neo_ops.router, 'POST', '/admin/neo/draft'),
]


def test_all_gap_routes_registered():
    missing = []
    for mod, method, path in CHECKS:
        if (method, path) not in _routes(mod):
            missing.append(f'{method} {path}')
    assert not missing, f'Missing routes: {missing}'
