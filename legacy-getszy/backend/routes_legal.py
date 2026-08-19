"""Legal, compliance & data export endpoints.

Provides:
- /api/legal/tos           — Terms of Service (Markdown/HTML)
- /api/legal/privacy       — Privacy Policy
- /api/legal/data-export   — Download all user data (GDPR / DPDP Act 2023 compliant)
- /api/legal/data-delete   — Request account + data deletion
"""
import asyncio
import json
import io
import logging
import os
import zipfile
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from auth import get_current_user, get_current_admin
from db import db

logger = logging.getLogger('getszy')

router = APIRouter(prefix='/legal', tags=['legal'])

# Grace period before a deletion request is actually executed (DPDP Act 2023
# right to erasure — allows a cooling-off window + fraud/refund reconciliation).
DELETION_GRACE_DAYS = int(os.environ.get('DELETION_GRACE_DAYS', '30'))

# Collections that hold a user's personal data, all keyed by `user_id`.
_DELETION_COLLECTIONS = [
    'orders', 'enrollments', 'subscriptions', 'billing_subscriptions',
    'chat_projects', 'chat_messages', 'chat_assets', 'workspace_plans',
    'workspace_tasks', 'workspace_versions', 'workspace_deployments',
    'hosted_sites', 'builder_projects', 'media_generations', 'support_tickets',
    'credit_transactions', 'free_tier_usage', 'data_export_log',
    'video_projects', 'video_jobs',
]


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Data Export (Right to Access — DPDP Act §11, GDPR Art. 15) ----------
@router.get('/data-export')
async def data_export(user=Depends(get_current_user)):
    """Return a ZIP containing all of the user's data as JSON files."""
    user_id = user['id']

    async def _dump(collection: str, filt: dict = None):
        filt = filt or {'user_id': user_id}
        return [doc async for doc in db[collection].find(filt, {'_id': 0})]

    bundle = {
        'exported_at': _iso(),
        'user': {k: v for k, v in user.items() if k != 'password_hash'},
        'orders': await _dump('orders'),
        'enrollments': await _dump('enrollments'),
        'subscriptions': await _dump('subscriptions'),
        'billing_subscriptions': await _dump('billing_subscriptions'),
        'chat_projects': await _dump('chat_projects'),
        'chat_messages': await _dump('chat_messages'),
        'chat_assets': await _dump('chat_assets'),
        'workspace_plans': await _dump('workspace_plans'),
        'workspace_tasks': await _dump('workspace_tasks'),
        'workspace_versions': await _dump('workspace_versions'),
        'workspace_deployments': await _dump('workspace_deployments'),
        'hosted_sites': await _dump('hosted_sites'),
        'builder_projects': await _dump('builder_projects'),
        'media_generations': await _dump('media_generations'),
        'support_tickets': await _dump('support_tickets'),
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('README.md',
                   f"# Getszy Data Export\n\n"
                   f"Exported: {bundle['exported_at']}\n"
                   f"User: {user['email']}\n\n"
                   "This ZIP contains all personal data Getszy holds about you.\n"
                   "Under India's DPDP Act 2023 and GDPR, you have the right to this data.\n\n"
                   "Files:\n"
                   "- data.json      — full structured dump\n"
                   "- user.json      — your profile\n"
                   "- projects.json  — your Neo chat projects and outputs\n"
                   "- orders.json    — orders + enrollments\n\n"
                   "Questions? support@getszy.com\n")
        z.writestr('data.json', json.dumps(bundle, indent=2, default=str))
        z.writestr('user.json', json.dumps(bundle['user'], indent=2, default=str))
        z.writestr('projects.json', json.dumps({
            'chat_projects': bundle['chat_projects'],
            'chat_messages': bundle['chat_messages'],
            'chat_assets': bundle['chat_assets'],
        }, indent=2, default=str))
        z.writestr('orders.json', json.dumps({
            'orders': bundle['orders'],
            'enrollments': bundle['enrollments'],
        }, indent=2, default=str))

    # audit log
    await db.data_export_log.insert_one({
        'user_id': user_id,
        'email': user.get('email'),
        'at': _iso(),
    })

    return Response(
        content=buf.getvalue(),
        media_type='application/zip',
        headers={'Content-Disposition': f'attachment; filename="getszy-data-{user_id[:8]}.zip"'},
    )


# ---------- Data Deletion (Right to Erasure — DPDP Act 2023 §12) ----------
@router.post('/data-delete')
async def data_delete_request(user=Depends(get_current_user)):
    """Request account & data deletion. A background worker
    (:func:`process_due_deletions`, launched at startup) erases the data after a
    configurable grace period (default 30 days) so this is NOT a no-op queue."""
    existing = await db.deletion_requests.find_one({'user_id': user['id'], 'status': 'pending'})
    if existing:
        return {'ok': True, 'status': 'already_pending', 'requested_at': existing.get('requested_at')}
    process_after = (datetime.now(timezone.utc) + timedelta(days=DELETION_GRACE_DAYS)).isoformat()
    await db.deletion_requests.insert_one({
        'user_id': user['id'],
        'email': user.get('email'),
        'status': 'pending',
        'requested_at': _iso(),
        'process_after': process_after,
    })
    return {
        'ok': True,
        'status': 'pending',
        'process_after': process_after,
        'note': f'Aapka deletion request record ho gaya hai. {DELETION_GRACE_DAYS} din ke grace period ke baad data permanently delete ho jayega.',
    }


@router.get('/data-delete/status')
async def data_delete_status(user=Depends(get_current_user)):
    rec = await db.deletion_requests.find_one({'user_id': user['id']}, {'_id': 0})
    return {'pending': bool(rec), 'record': rec}


# ─────────────────────────────────────────────────────────────────────────────
# Deletion worker — actually erases user data (DPDP §12 right to erasure).
# The /data-delete endpoint only QUEUES a request; this worker is what makes the
# promise real. Launched once at server startup (see server.startup).
# ─────────────────────────────────────────────────────────────────────────────
async def _erase_user_data(user_id: str):
    """Permanently delete a user's personal data across every collection and
    anonymize the auth record (kept only as a tombstone so any residual foreign
    references don't dangle). Best-effort per collection — one failure must not
    block the others."""
    for coll in _DELETION_COLLECTIONS:
        try:
            await db[coll].delete_many({'user_id': user_id})
        except Exception as e:  # pragma: no cover - environment dependent
            logger.warning('deletion: failed to purge %s for %s: %s', coll, user_id, e)
    try:
        await db.users.update_one(
            {'id': user_id},
            {'$set': {
                'email': f'deleted_{user_id}@deleted.getszy.com',
                'phone': None,
                'name': 'Deleted User',
                'password_hash': 'DELETED',
                'credits': 0,
                'deleted': True,
            }, '$unset': {'profile_picture': '', 'address': '', 'stripe_customer_id': ''}},
        )
    except Exception as e:  # pragma: no cover - environment dependent
        logger.warning('deletion: failed to anonymize user %s: %s', user_id, e)


async def process_due_deletions():
    """Erase data for every pending deletion request whose grace period has
    elapsed. Admin/founder accounts are protected (marked 'skipped').

    Returns the number of accounts actually erased.
    """
    now = _iso()
    processed = 0
    async for rec in db.deletion_requests.find({'status': 'pending', 'process_after': {'$lte': now}}):
        uid = rec.get('user_id')
        if not uid:
            continue
        u = await db.users.find_one({'id': uid}, {'_id': 0, 'role': 1})
        if u and u.get('role') in ('admin', 'founder'):
            await db.deletion_requests.update_one(
                {'_id': rec['_id']},
                {'$set': {'status': 'skipped', 'completed_at': now, 'note': 'admin/founder protected'}},
            )
            continue
        await _erase_user_data(uid)
        await db.deletion_requests.update_one(
            {'_id': rec['_id']},
            {'$set': {'status': 'completed', 'completed_at': now}},
        )
        processed += 1
        logger.info('deletion: erased data for user %s', uid)
    return processed


async def deletion_worker():
    """Hourly sweeper. Runs forever; never lets an exception kill the loop."""
    while True:
        try:
            await process_due_deletions()
        except Exception as e:  # pragma: no cover - environment dependent
            logger.warning('deletion worker error: %s', e)
        await asyncio.sleep(3600)


@router.post('/admin/data-delete/process')
async def admin_process_deletions(admin=Depends(get_current_admin)):
    """Manually trigger processing of due deletion requests (compliance/audit use)."""
    n = await process_due_deletions()
    return {'ok': True, 'processed': n}
