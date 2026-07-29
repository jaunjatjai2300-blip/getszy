import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "getszy_test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-audit-only-12345678901234567890")
os.environ.setdefault("SEED_ADMIN_EMAIL", "admin@getszy.com")
os.environ.setdefault("SEED_ADMIN_PASSWORD", "Admin123!")
import mongomock, pymongo
pymongo.MongoClient = mongomock.MongoClient
import motor.motor_asyncio
class MockAsyncMotorClient:
    def __init__(self, *a, **k):
        self._client = mongomock.MongoClient()
    def __getitem__(self, name):
        return self._client[name]
    def close(self):
        self._client.close()
    def command(self, *a, **k):
        return {"ok": 1}
motor.motor_asyncio.AsyncIOMotorClient = MockAsyncMotorClient

from server import app
from fastapi.testclient import TestClient

c = TestClient(app)

r = c.get("/api/healthz")
print("GET /api/healthz -> %d %s" % (r.status_code, r.json()))

r2 = c.get("/api/health")
print("GET /api/health  -> %d %s" % (r2.status_code, r2.json()))

if r.status_code == 200 and r2.status_code == 200:
    print("\n[OK] Both health endpoints working")
else:
    print("\n[FAIL] One or both health endpoints broken")
