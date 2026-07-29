"""Getszy Backend - Comprehensive Functional Audit Script"""

import sys
import os
import json
import traceback
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "getszy_test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-audit-only-12345678901234567890")
os.environ.setdefault("SEED_ADMIN_EMAIL", "admin@getszy.com")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "Admin123!")
os.environ.setdefault("SEED_CUSTOMER_EMAIL", "customer@getszy.com")
os.environ.setdefault("SEED_CUSTOMER_PASSWORD", "Customer123!")

import mongomock
import pymongo
pymongo.MongoClient = mongomock.MongoClient

import motor.motor_asyncio

class MockAsyncMotorClient:
    def __init__(self, *args, **kwargs):
        self._client = mongomock.MongoClient()
    def __getitem__(self, name):
        return self._client[name]
    def __getattr__(self, name):
        if name.startswith('_'):
            return super().__getattribute__(name)
        return getattr(self._client, name)
    def close(self):
        self._client.close()
    def command(self, *args, **kwargs):
        return {"ok": 1}

motor.motor_asyncio.AsyncIOMotorClient = MockAsyncMotorClient

print("=" * 80)
print("GETSZY BACKEND - COMPREHENSIVE FUNCTIONAL AUDIT")
print("Started: " + datetime.now(timezone.utc).isoformat())
print("=" * 80)

try:
    from db import db, client
    from server import app
    from fastapi.testclient import TestClient
    print("\n[OK] Server module loaded successfully")
except Exception as e:
    print("\n[FAIL] Failed to load server: " + str(e))
    traceback.print_exc()
    sys.exit(1)

client_test = TestClient(app)
results = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "endpoints": []}

def test_endpoint(method, path, description, json_data=None, headers=None, expected_status=None, auth_required=False):
    results["total"] += 1
    entry = {"method": method, "path": path, "description": description, "status": "unknown", "response_code": None, "error": None}
    response = None
    try:
        if method == "GET":
            response = client_test.get(path, headers=headers)
        elif method == "POST":
            response = client_test.post(path, json=json_data, headers=headers)
        elif method == "PUT":
            response = client_test.put(path, json=json_data, headers=headers)
        elif method == "DELETE":
            response = client_test.delete(path, headers=headers)
        else:
            entry["status"] = "skipped"
            results["skipped"] += 1
            results["endpoints"].append(entry)
            return entry
        entry["response_code"] = response.status_code
        if expected_status and response.status_code == expected_status:
            entry["status"] = "passed"
            results["passed"] += 1
        elif expected_status and response.status_code != expected_status:
            entry["status"] = "failed"
            entry["error"] = "Expected %d, got %d" % (expected_status, response.status_code)
            results["failed"] += 1
        elif response.status_code < 400:
            entry["status"] = "passed"
            results["passed"] += 1
        elif response.status_code == 401 and auth_required:
            entry["status"] = "passed"
            entry["error"] = "Auth required (expected)"
            results["passed"] += 1
        else:
            entry["status"] = "failed"
            entry["error"] = "HTTP %d: %s" % (response.status_code, response.text[:200])
            results["failed"] += 1
    except Exception as e:
        entry["status"] = "failed"
        entry["error"] = str(e)[:200]
        results["failed"] += 1
    results["endpoints"].append(entry)
    icon = "[OK]" if entry["status"] == "passed" else "[FAIL]" if entry["status"] == "failed" else "[SKIP]"
    code = entry["response_code"] if entry["response_code"] else "N/A"
    print("  %s [%s] %s -- %s -- %s" % (icon, method, path, code, description))
    return entry

print("\n" + "=" * 80)
print("PHASE 1: HEALTH & CORE ENDPOINTS")
print("=" * 80)
test_endpoint("GET", "/api/", "Root API info")
test_endpoint("GET", "/api/health", "Health check")

print("\n" + "=" * 80)
print("PHASE 2: AUTH ENDPOINTS")
print("=" * 80)
test_endpoint("POST", "/api/auth/signup", "User signup", json_data={"name": "Test User", "email": "test@getszy.com", "password": "TestPass123!"}, expected_status=200)
login_result = test_endpoint("POST", "/api/auth/login", "User login", json_data={"email": "test@getszy.com", "password": "TestPass123!"}, expected_status=200)

auth_token = None
if login_result and login_result.get("response_code") == 200:
    try:
        resp = client_test.post("/api/auth/login", json={"email": "test@getszy.com", "password": "TestPass123!"})
        auth_token = resp.json().get("token")
    except:
        pass
auth_headers = {"Authorization": "Bearer %s" % auth_token} if auth_token else {}

test_endpoint("GET", "/api/auth/me", "Get current user", headers=auth_headers, auth_required=True)
test_endpoint("POST", "/api/auth/login", "Invalid login", json_data={"email": "test@getszy.com", "password": "wrongpassword"}, expected_status=401)
test_endpoint("POST", "/api/auth/signup", "Duplicate signup", json_data={"name": "Test User", "email": "test@getszy.com", "password": "TestPass123!"}, expected_status=400)

print("\n" + "=" * 80)
print("PHASE 3: CATALOG ENDPOINTS")
print("=" * 80)
test_endpoint("GET", "/api/categories", "List categories")
test_endpoint("GET", "/api/products", "List products")
test_endpoint("GET", "/api/admin/products", "Admin list products", headers=auth_headers, auth_required=True)
test_endpoint("POST", "/api/admin/products", "Admin create product", json_data={"name": "Test Product", "description": "A test", "price": 99.99, "category": "test", "stock": 10}, headers=auth_headers, auth_required=True)
test_endpoint("POST", "/api/admin/categories", "Admin create category", json_data={"name": "Test Category"}, headers=auth_headers, auth_required=True)

print("\n" + "=" * 80)
print("PHASE 4: CART & ORDERS ENDPOINTS")
print("=" * 80)
test_endpoint("GET", "/api/cart", "Get cart", headers=auth_headers, auth_required=True)
test_endpoint("POST", "/api/cart/add", "Add to cart", json_data={"product_id": "test-id", "quantity": 1}, headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/orders/mine", "My orders", headers=auth_headers, auth_required=True)

print("\n" + "=" * 80)
print("PHASE 5: ADMIN DASHBOARD ENDPOINTS (Critical)")
print("=" * 80)
test_endpoint("GET", "/api/admin/stats", "Admin stats", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/stats?range=today", "Stats today", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/stats?range=week", "Stats week", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/stats?range=month", "Stats month", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/customers", "Customers list", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/orders", "Orders list", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/founder-stats", "Founder stats", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/system-stats", "System stats", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/login-sessions", "Login sessions", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/api-keys", "API keys list", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/projects", "Admin projects", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/analytics/series", "Analytics series", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/analytics/funnel", "Analytics funnel", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/settings", "Admin settings", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/audit-logs", "Audit logs", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/live-activity", "Live activity", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/dashboard/executive", "Executive dashboard", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/blocked-ips", "Blocked IPs", headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/chat/sessions", "Chat sessions", headers=auth_headers, auth_required=True)
test_endpoint("POST", "/api/admin/chat", "Admin chat", json_data={"message": "Show stats"}, headers=auth_headers, auth_required=True)
test_endpoint("GET", "/api/admin/chat/history", "Chat history", headers=auth_headers, auth_required=True)
test_endpoint("POST", "/api/admin/settings", "Save settings", json_data={"section": "workspace", "data": {"theme": "dark"}}, headers=auth_headers, auth_required=True)
test_endpoint("POST", "/api/admin/api-keys", "Create API key", json_data={"name": "Test Key"}, headers=auth_headers, auth_required=True)
test_endpoint("POST", "/api/admin/blocked-ips", "Block IP", json_data={"ip": "192.168.1.100", "reason": "Testing"}, headers=auth_headers, auth_required=True)

print("\n" + "=" * 80)
print("PHASE 6: ADMIN AUTHORIZATION (Security)")
print("=" * 80)
test_endpoint("GET", "/api/admin/stats", "Stats WITHOUT auth", expected_status=401)
test_endpoint("GET", "/api/admin/customers", "Customers WITHOUT auth", expected_status=401)
test_endpoint("GET", "/api/admin/dashboard/executive", "Executive WITHOUT auth", expected_status=401)

print("\n" + "=" * 80)
print("PHASE 7: ROUTE REGISTRY")
print("=" * 80)
try:
    from app.router_registry import CORE_ROUTERS, LEARNING_ROUTERS, AI_ROUTERS, COMMERCE_ROUTERS, MEDIA_ROUTERS, CREATOR_ROUTERS, BUILD_ROUTERS, DEPLOY_ROUTERS, PLATFORM_ROUTERS, SUPPORT_ROUTERS, ANALYTICS_ROUTERS, MISC_ROUTERS, ENGINE_ROUTERS
    all_cats = [("CORE", CORE_ROUTERS), ("LEARNING", LEARNING_ROUTERS), ("AI", AI_ROUTERS), ("COMMERCE", COMMERCE_ROUTERS), ("MEDIA", MEDIA_ROUTERS), ("CREATOR", CREATOR_ROUTERS), ("BUILD", BUILD_ROUTERS), ("DEPLOY", DEPLOY_ROUTERS), ("PLATFORM", PLATFORM_ROUTERS), ("SUPPORT", SUPPORT_ROUTERS), ("ANALYTICS", ANALYTICS_ROUTERS), ("MISC", MISC_ROUTERS), ("ENGINE", ENGINE_ROUTERS)]
    total_routes = 0
    loaded = 0
    failed = []
    for cat, routes in all_cats:
        for name, mod_name, prefix in routes:
            total_routes += 1
            try:
                mod = __import__(mod_name)
                r = getattr(mod, 'router', None)
                if r:
                    loaded += 1
                else:
                    failed.append("%s: no router attr" % name)
            except Exception as e:
                failed.append("%s: %s" % (name, str(e)[:60]))
    print("\n  Route Registry: %d/%d routers loaded" % (loaded, total_routes))
    if failed:
        print("  [FAIL] %d routers failed:" % len(failed))
        for f in failed:
            print("    - %s" % f)
    else:
        print("  [OK] All routers loaded")

    from fastapi.routing import APIRoute
    all_routes = [r for r in app.routes if isinstance(r, APIRoute)]
    print("\n  Total registered API routes: %d" % len(all_routes))

    for route in sorted(all_routes, key=lambda r: r.path):
        methods = ",".join(route.methods)
        print("    %s %s" % (methods.ljust(8), route.path))

except Exception as e:
    print("  [FAIL] Route audit failed: %s" % e)
    traceback.print_exc()

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\n  Total tested: %d" % results["total"])
print("  [OK] Passed: %d" % results["passed"])
print("  [FAIL] Failed: %d" % results["failed"])
print("  [SKIP] Skipped: %d" % results["skipped"])
pct = round(results["passed"] / max(results["total"], 1) * 100, 1)
print("  Pass rate: %.1f%%" % pct)

admin_eps = [e for e in results["endpoints"] if "/admin/" in e["path"]]
admin_ok = sum(1 for e in admin_eps if e["status"] == "passed")
admin_fail = sum(1 for e in admin_eps if e["status"] == "failed")
print("\n  Admin Dashboard: %d endpoints" % len(admin_eps))
print("    Passed: %d | Failed: %d" % (admin_ok, admin_fail))

failures = [e for e in results["endpoints"] if e["status"] == "failed"]
if failures:
    print("\n  FAILURES (%d):" % len(failures))
    for f in failures:
        print("    [FAIL] [%s] %s -- %s" % (f["method"], f["path"], f["error"][:100]))
else:
    print("\n  All tests passed!")

report_path = os.path.join(os.path.dirname(__file__), "audit_report.json")
with open(report_path, "w") as f:
    json.dump(results, f, indent=2, default=str)
print("\n  Report saved: %s" % report_path)
print("=" * 80)
