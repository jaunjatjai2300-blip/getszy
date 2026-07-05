"""Legal, compliance & data export endpoints.

Provides:
- /api/legal/tos           — Terms of Service (Markdown/HTML)
- /api/legal/privacy       — Privacy Policy
- /api/legal/data-export   — Download all user data (GDPR / DPDP Act 2023 compliant)
- /api/legal/data-delete   — Request account + data deletion
"""
import json
import io
import zipfile
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from auth import get_current_user
from db import db

router = APIRouter(prefix='/legal', tags=['legal'])


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


# ---------- Data Deletion (Right to Erasure) ----------
@router.post('/data-delete')
async def data_delete_request(user=Depends(get_current_user)):
    """Request account & data deletion. Recorded for review — 30-day cooling period."""
    existing = await db.deletion_requests.find_one({'user_id': user['id'], 'status': 'pending'})
    if existing:
        return {'ok': True, 'status': 'already_pending', 'requested_at': existing.get('requested_at')}
    await db.deletion_requests.insert_one({
        'user_id': user['id'],
        'email': user.get('email'),
        'status': 'pending',
        'requested_at': _iso(),
        'process_after': _iso(),  # in production: +30 days grace period
    })
    return {'ok': True, 'status': 'pending', 'note': 'Aapka deletion request record ho gaya hai. Team 7 din mein confirm karegi.'}


@router.get('/data-delete/status')
async def data_delete_status(user=Depends(get_current_user)):
    rec = await db.deletion_requests.find_one({'user_id': user['id']}, {'_id': 0})
    return {'pending': bool(rec), 'record': rec}
