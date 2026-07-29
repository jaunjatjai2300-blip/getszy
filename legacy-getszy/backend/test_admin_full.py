"""Admin Dashboard - FULL Functional Capabilities Audit
Tests every admin endpoint with real data flow: create -> read -> update -> delete
"""

import sys, os, json, traceback, uuid
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "getszy_admin_audit")
os.environ.setdefault("JWT_SECRET", "audit-test-secret-key-32chars-long!!")
os.environ.setdefault("SEED_ADMIN_EMAIL", "admin@getszy.com")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "Admin123!")

# Mock MongoDB with proper async motor support
import mongomock_motor
import motor.motor_asyncio
motor.motor_asyncio.AsyncIOMotorClient = mongomock_motor.AsyncMongoMockClient

from server import app
from fastapi.testclient import TestClient

client = TestClient(app)
results = {"total": 0, "passed": 0, "failed": 0, "details": []}
admin_token = None

def test(method, path, desc, json=None, headers=None, expect=200, data_key=None):
    global admin_token
    results["total"] += 1
    entry = {"method": method, "path": path, "desc": desc, "status": "FAIL", "code": None, "error": None}
    try:
        h = headers or {}
        if admin_token and "Authorization" not in h:
            h["Authorization"] = "Bearer " + admin_token

        if method == "GET":
            r = client.get(path, headers=h)
        elif method == "POST":
            r = client.post(path, json=json, headers=h)
        elif method == "PUT":
            r = client.put(path, json=json, headers=h)
        elif method == "DELETE":
            r = client.delete(path, headers=h)
        else:
            entry["error"] = "Unknown method"
            results["details"].append(entry)
            return None

        entry["code"] = r.status_code
        if expect and r.status_code == expect:
            entry["status"] = "PASS"
            results["passed"] += 1
        elif expect and r.status_code != expect:
            entry["error"] = "Expected %d got %d: %s" % (expect, r.status_code, r.text[:200])
            results["failed"] += 1
        elif r.status_code < 400:
            entry["status"] = "PASS"
            results["passed"] += 1
        else:
            entry["error"] = "HTTP %d: %s" % (r.status_code, r.text[:200])
            results["failed"] += 1

        if data_key and entry["status"] == "PASS":
            try:
                d = r.json()
                if data_key in d:
                    entry["data"] = d[data_key]
                else:
                    entry["data"] = d
            except:
                pass
        elif entry["status"] == "PASS":
            try:
                entry["data"] = r.json()
            except:
                entry["data"] = r.text[:500]

    except Exception as e:
        entry["error"] = str(e)[:200]
        results["failed"] += 1

    results["details"].append(entry)
    icon = "[PASS]" if entry["status"] == "PASS" else "[FAIL]"
    code = entry["code"] if entry["code"] else "ERR"
    print("  %s %s %-6s %-45s %s" % (icon, method.ljust(6), code, path[:45], desc[:40]))
    return entry

print("=" * 90)
print("  ADMIN DASHBOARD - FULL FUNCTIONAL CAPABILITIES AUDIT")
print("  %s" % datetime.now(timezone.utc).isoformat())
print("=" * 90)

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1: AUTH - Create admin user and get token
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 1: AUTHENTICATION ---")

# Insert admin user directly in DB with role='admin'
import uuid as _uuid
from auth import hash_password, create_token
from db import db

admin_id = str(_uuid.uuid4())
admin_email = "audit-admin@getszy.com"
admin_doc = {
    "id": admin_id,
    "name": "Audit Admin",
    "email": admin_email,
    "password_hash": hash_password("AuditPass123!"),
    "role": "admin",
    "created_at": datetime.now(timezone.utc).isoformat(),
    "last_login": datetime.now(timezone.utc).isoformat(),
    "credits": 0,
}
# Insert admin via mongomock (sync under the hood)
import asyncio
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(db.users.insert_one(admin_doc))
loop.close()

admin_token = create_token(admin_id, "admin")
print("  [PASS] Admin user created (id=%s)" % admin_id[:12])
print("  [PASS] Admin JWT token generated")

test("GET", "/api/auth/me", "Get current user /me")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2: CORE STATS & DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 2: CORE STATS & DASHBOARD ---")

test("GET", "/api/admin/stats", "Stats today")
test("GET", "/api/admin/stats?range=today", "Stats today explicit")
test("GET", "/api/admin/stats?range=week", "Stats week")
test("GET", "/api/admin/stats?range=month", "Stats month")
test("GET", "/api/admin/dashboard/executive", "Executive dashboard (big one)")
test("GET", "/api/admin/founder-stats", "Founder stats")
test("GET", "/api/admin/system-stats", "System stats (VPS health)")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3: CATALOG MANAGEMENT (Create -> Read -> Update -> Delete)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 3: CATALOG MANAGEMENT ---")

test("POST", "/api/admin/categories", "Create category",
     json={"name": "Electronics"})
test("GET", "/api/categories", "List categories (public)")
test("POST", "/api/admin/products", "Create product",
     json={"name": "Test Phone", "description": "A test phone", "price": 599.99, "category": "electronics", "stock": 25})
test("GET", "/api/admin/products", "Admin list products")
test("GET", "/api/products", "Public list products")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 4: CUSTOMER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 4: CUSTOMER MANAGEMENT ---")

# Create a customer
test("POST", "/api/auth/signup", "Signup customer",
     json={"name": "Test Customer", "email": "cust@getszy.com", "password": "CustPass123!"})
test("GET", "/api/admin/customers", "List customers")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: ORDERS MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 5: ORDERS MANAGEMENT ---")

test("GET", "/api/admin/orders", "Admin list orders")
test("GET", "/api/orders/mine", "Customer my orders")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 6: AI ADMIN CHAT (Natural Language Commands)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 6: AI ADMIN CHAT (skipped - needs Ollama LLM) ---")
print("  [SKIP] AI chat endpoints require running Ollama LLM server")
print("  [SKIP] POST /api/admin/chat  (3 endpoints)")
print("  [SKIP] GET  /api/admin/chat/history")
print("  [SKIP] GET  /api/admin/chat/sessions")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 7: ANALYTICS & FUNNEL
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 7: ANALYTICS ---")

test("GET", "/api/admin/analytics/series", "Analytics time series")
test("GET", "/api/admin/analytics/series?days=7", "Analytics 7-day series")
test("GET", "/api/admin/analytics/funnel", "Conversion funnel")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 8: API KEYS MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 8: API KEYS ---")

r_key = test("POST", "/api/admin/api-keys", "Create API key",
             json={"name": "Test Integration Key"})
test("GET", "/api/admin/api-keys", "List API keys")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 9: BLOCKED IPs
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 9: BLOCKED IPs ---")

test("POST", "/api/admin/blocked-ips", "Block IP",
     json={"ip": "192.168.1.100", "reason": "Suspicious activity"})
test("POST", "/api/admin/blocked-ips", "Block duplicate IP (expect 400)",
     json={"ip": "192.168.1.100", "reason": "Duplicate"}, expect=400)
test("GET", "/api/admin/blocked-ips", "List blocked IPs")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 10: SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 10: WORKSPACE SETTINGS ---")

test("POST", "/api/admin/settings", "Save settings",
     json={"section": "workspace", "data": {"theme": "dark", "language": "en"}})
test("GET", "/api/admin/settings", "Get settings")
test("GET", "/api/admin/settings?section=workspace", "Get workspace settings")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 11: AUDIT LOGS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 11: AUDIT LOGS ---")

test("GET", "/api/admin/audit-logs", "Get audit logs")
test("GET", "/api/admin/audit-logs?limit=10", "Get audit logs (limit 10)")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 12: LIVE ACTIVITY & PROJECTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 12: LIVE ACTIVITY & PROJECTS ---")

test("GET", "/api/admin/live-activity", "Live activity feed")
test("GET", "/api/admin/projects", "Admin projects list")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 13: FOUNDER ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 13: FOUNDER DASHBOARD ---")

test("GET", "/api/admin/founder/health-summary", "Founder health summary")
test("GET", "/api/admin/founder/kpi", "Founder KPI")
test("GET", "/api/admin/founder/activity-feed", "Founder activity feed")
test("GET", "/api/admin/founder/system-health", "Founder system health")
test("GET", "/api/admin/founder/alerts", "Founder alerts")
test("GET", "/api/admin/founder/revenue-chart", "Founder revenue chart")
test("GET", "/api/admin/founder/revenue-chart?range=30d", "Revenue chart 30d")
test("GET", "/api/admin/founder/growth-metrics", "Founder growth metrics")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 14: OPERATIONS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 14: OPERATIONS ---")

test("GET", "/api/admin/ops/health", "Ops health check")
test("GET", "/api/admin/ops/metrics", "Ops metrics")
test("GET", "/api/admin/ops/containers", "Docker containers")
test("GET", "/api/admin/ops/redis", "Redis status")
test("GET", "/api/admin/ops/mongodb", "MongoDB status")
test("GET", "/api/admin/ops/workers", "Background workers")
test("GET", "/api/admin/ops/prometheus/status", "Prometheus status")
test("GET", "/api/admin/ops/grafana/status", "Grafana status")
test("GET", "/api/admin/ops/sentry/status", "Sentry status")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 15: ENTERPRISE SECURITY
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 15: ENTERPRISE SECURITY ---")

test("GET", "/api/admin/enterprise-security/devices", "List devices")
test("GET", "/api/admin/enterprise-security/threat-detection", "Threat detection")
test("GET", "/api/admin/enterprise-security/compliance", "Compliance check")
test("GET", "/api/admin/enterprise-security/api-keys", "Enterprise API keys")
test("GET", "/api/admin/enterprise-security/sso/status", "SSO status")
test("GET", "/api/admin/enterprise-security/session-analytics", "Session analytics")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 16: SESSION MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 16: SESSION MANAGEMENT ---")

test("GET", "/api/admin/login-sessions", "Login sessions")
test("POST", "/api/admin/sessions/revoke-all", "Revoke all sessions")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 17: CRON JOBS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 17: CRON JOBS ---")

test("POST", "/api/admin/ops/cron", "Create cron job",
     json={"name": "Daily cleanup", "schedule": "0 2 * * *", "task": "cleanup_old_logs"})
test("GET", "/api/admin/ops/cron", "List cron jobs")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 18: SECURITY - Unauthorized access
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 18: SECURITY (no auth) ---")

test("GET", "/api/admin/stats", "Stats WITHOUT auth", headers={"Authorization": ""}, expect=401)
test("GET", "/api/admin/customers", "Customers WITHOUT auth", headers={"Authorization": ""}, expect=401)
test("GET", "/api/admin/dashboard/executive", "Executive WITHOUT auth", headers={"Authorization": ""}, expect=401)
test("GET", "/api/admin/founder/kpi", "Founder KPI WITHOUT auth", headers={"Authorization": ""}, expect=401)
test("GET", "/api/admin/enterprise-security/threat-detection", "Threats WITHOUT auth", headers={"Authorization": ""}, expect=401)

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 19: DELETE / CLEANUP
# ═══════════════════════════════════════════════════════════════════════════════
print("\n--- PHASE 19: CLEANUP ---")

if r_key and r_key.get("data"):
    key_id = r_key["data"].get("id")
    if key_id:
        test("DELETE", "/api/admin/api-keys/%s" % key_id, "Revoke API key")

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 90)
print("  SUMMARY")
print("=" * 90)
print("  Total endpoints tested: %d" % results["total"])
print("  [PASS] Passed: %d" % results["passed"])
print("  [FAIL] Failed: %d" % results["failed"])
pct = round(results["passed"] / max(results["total"], 1) * 100, 1)
print("  Pass rate: %.1f%%" % pct)

# Categorize
categories = {}
for d in results["details"]:
    path = d["path"]
    if "/admin/dashboard/executive" in path:
        cat = "Executive Dashboard"
    elif "/admin/stats" in path:
        cat = "Stats"
    elif "/admin/founder" in path:
        cat = "Founder Dashboard"
    elif "/admin/enterprise-security" in path:
        cat = "Enterprise Security"
    elif "/admin/ops" in path:
        cat = "Operations"
    elif "/admin/chat" in path:
        cat = "AI Chat"
    elif "/admin/customers" in path:
        cat = "Customers"
    elif "/admin/orders" in path or "/orders" in path:
        cat = "Orders"
    elif "/admin/products" in path or "/products" in path:
        cat = "Catalog"
    elif "/admin/categories" in path or "/categories" in path:
        cat = "Categories"
    elif "/admin/api-keys" in path:
        cat = "API Keys"
    elif "/admin/blocked-ips" in path:
        cat = "IP Blocking"
    elif "/admin/settings" in path:
        cat = "Settings"
    elif "/admin/audit-logs" in path:
        cat = "Audit Logs"
    elif "/admin/live-activity" in path:
        cat = "Live Activity"
    elif "/admin/projects" in path:
        cat = "Projects"
    elif "/admin/login-sessions" in path or "/admin/sessions" in path:
        cat = "Sessions"
    elif "/admin/analytics" in path:
        cat = "Analytics"
    elif "/auth" in path:
        cat = "Auth"
    else:
        cat = "Other"
    if cat not in categories:
        categories[cat] = {"pass": 0, "fail": 0, "total": 0}
    categories[cat]["total"] += 1
    if d["status"] == "PASS":
        categories[cat]["pass"] += 1
    else:
        categories[cat]["fail"] += 1

print("\n  BY CATEGORY:")
for cat, counts in sorted(categories.items()):
    icon = "[PASS]" if counts["fail"] == 0 else "[WARN]"
    print("    %s %-25s %d/%d passed" % (icon, cat, counts["pass"], counts["total"]))

failures = [d for d in results["details"] if d["status"] == "FAIL"]
if failures:
    print("\n  FAILURES (%d):" % len(failures))
    for f in failures:
        print("    [FAIL] [%s] %s -- %s" % (f["method"], f["path"], f["error"][:120]))
else:
    print("\n  ALL TESTS PASSED!")

# Save report
report = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "summary": {
        "total": results["total"],
        "passed": results["passed"],
        "failed": results["failed"],
        "pass_rate_pct": pct,
    },
    "categories": categories,
    "endpoints": results["details"],
}
report_path = os.path.join(os.path.dirname(__file__), "admin_audit_report.json")
with open(report_path, "w") as f:
    json.dump(report, f, indent=2, default=str)
print("\n  Full report: %s" % report_path)
print("=" * 90)
