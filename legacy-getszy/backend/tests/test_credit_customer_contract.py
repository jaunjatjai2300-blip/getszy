import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:27017')
os.environ.setdefault('JWT_SECRET', 'test-only-credit-contract-secret')

from routes_credits import _credit_status, router


def test_customer_credit_routes_are_registered_without_admin_access():
    routes = {route.path: route for route in router.routes}

    assert '/credits/me' in routes
    assert '/credits/me/transactions' in routes
    assert '/credits/admin/transactions/{user_email}' in routes
    assert routes['/credits/me/transactions'].methods == {'GET'}


def test_credit_status_policy_has_explicit_low_balance_thresholds():
    assert _credit_status(100, False) == 'healthy'
    assert _credit_status(20, False) == 'low'
    assert _credit_status(5, False) == 'critical'
    assert _credit_status(0, False) == 'empty'
    assert _credit_status(0, True) == 'exempt'
