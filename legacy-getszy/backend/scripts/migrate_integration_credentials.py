#!/usr/bin/env python3
"""Migrate legacy user_integrations.credentials values to credentials_encrypted.

Run with --dry-run first. Requires MONGO_URL, DB_NAME, and the stable
INTEGRATION_ENCRYPTION_KEY configured for the production deployment.
"""

import argparse
import asyncio
import base64
import hashlib
import json
import os
import sys

from cryptography.fernet import Fernet
from motor.motor_asyncio import AsyncIOMotorClient


def cipher() -> Fernet:
    secret = os.environ.get("INTEGRATION_ENCRYPTION_KEY", "")
    if not secret or secret in {"change-me", "secret", "dev-secret"}:
        raise RuntimeError("INTEGRATION_ENCRYPTION_KEY must be set to a secure stable value")
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


async def migrate(dry_run: bool) -> int:
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME", "getszy_db")
    if not mongo_url:
        raise RuntimeError("MONGO_URL is required")

    client = AsyncIOMotorClient(mongo_url)
    collection = client[db_name].user_integrations
    crypt = cipher()
    migrated = skipped = 0

    try:
        cursor = collection.find({"credentials": {"$exists": True}})
        async for document in cursor:
            credentials = document.get("credentials")
            if not isinstance(credentials, dict) or not credentials:
                skipped += 1
                print(f"SKIP {document.get('_id')}: credentials is empty or not an object")
                continue

            clean = {
                str(key): str(value).strip()
                for key, value in credentials.items()
                if str(value).strip()
            }
            if not clean:
                skipped += 1
                print(f"SKIP {document.get('_id')}: no non-empty credentials")
                continue

            encrypted = crypt.encrypt(
                json.dumps(clean, separators=(",", ":"), ensure_ascii=True).encode()
            ).decode()
            print(f"{'DRY-RUN ' if dry_run else ''}MIGRATE {document.get('_id')}")
            if not dry_run:
                await collection.update_one(
                    {"_id": document["_id"]},
                    {
                        "$set": {
                            "credentials_encrypted": encrypted,
                            "credential_encryption_version": 1,
                        },
                        "$unset": {"credentials": ""},
                    },
                )
            migrated += 1
    finally:
        client.close()

    print(f"Done. migrated={migrated} skipped={skipped} dry_run={dry_run}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Report candidates without changing MongoDB")
    args = parser.parse_args()
    try:
        return asyncio.run(migrate(args.dry_run))
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
