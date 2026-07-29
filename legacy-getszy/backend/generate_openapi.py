"""Auto-generate OpenAPI spec from the actual FastAPI app routes."""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "getszy_openapi_gen")
os.environ.setdefault("JWT_SECRET", "openapi-gen-secret-key-32chars-long!!")
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
import yaml

# Generate OpenAPI spec from the FastAPI app
openapi = app.openapi()

# Count endpoints
paths = openapi.get('paths', {})
total = sum(len(methods) for methods in paths.values())
print("Generated OpenAPI spec with %d paths, %d endpoints" % (len(paths), total))

# Write YAML
spec_path = os.path.join(os.path.dirname(__file__), '..', 'lib', 'api-spec', 'openapi.yaml')
os.makedirs(os.path.dirname(spec_path), exist_ok=True)
with open(spec_path, 'w', encoding='utf-8') as f:
    yaml.dump(openapi, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

# Also write JSON for reference
json_path = os.path.join(os.path.dirname(__file__), 'openapi_generated.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(openapi, f, indent=2, default=str)

print("Written to: %s" % spec_path)
print("JSON backup: %s" % json_path)

# Summary by tag
tags = {}
for path, methods in sorted(paths.items()):
    for method, details in methods.items():
        if method in ('get', 'post', 'put', 'delete', 'patch'):
            for tag in details.get('tags', ['untagged']):
                tags[tag] = tags.get(tag, 0) + 1

print("\nEndpoints by tag:")
for tag, count in sorted(tags.items(), key=lambda x: -x[1]):
    print("  %-30s %d" % (tag, count))
