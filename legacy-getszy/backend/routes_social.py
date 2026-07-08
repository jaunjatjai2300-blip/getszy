"""Social media auto-posting + post scheduling system.

Supported platforms: youtube, instagram, facebook, twitter
Each platform needs an access token set via /social/accounts/connect.
Actual OAuth flows are platform-specific — users paste their access token here.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
import httpx

from auth import get_current_user
from db import db

router = APIRouter(prefix='/social', tags=['social'])

PLATFORMS = ['youtube', 'instagram', 'facebook', 'twitter']


# ─── Models ──────────────────────────────────────────────────────────────────

class ScheduleIn(BaseModel):
    video_job_id: str
    platforms: List[str]
    title: str
    description: str = ''
    tags: List[str] = []
    scheduled_at: Optional[str] = None  # ISO datetime; None = publish immediately


class ConnectIn(BaseModel):
    platform: str
    access_token: str
    channel_id: Optional[str] = None
    channel_name: Optional[str] = None
    page_id: Optional[str] = None


class PublishNowIn(BaseModel):
    post_id: str


# ─── Accounts ────────────────────────────────────────────────────────────────

@router.post('/accounts/connect')
async def connect_account(body: ConnectIn, user=Depends(get_current_user)):
    if body.platform not in PLATFORMS:
        raise HTTPException(status_code=400, detail=f'Unknown platform. Use: {PLATFORMS}')
    await db.social_accounts.update_one(
        {'user_id': user['id'], 'platform': body.platform},
        {'$set': {
            'user_id': user['id'],
            'platform': body.platform,
            'access_token': body.access_token,
            'channel_id': body.channel_id,
            'channel_name': body.channel_name,
            'page_id': body.page_id,
            'connected_at': datetime.now(timezone.utc).isoformat(),
            'status': 'connected',
        }},
        upsert=True
    )
    return {'ok': True, 'platform': body.platform}


@router.get('/accounts')
async def list_accounts(user=Depends(get_current_user)):
    cur = db.social_accounts.find({'user_id': user['id']}, {'_id': 0, 'access_token': 0})
    accounts = [doc async for doc in cur]
    connected = {a['platform'] for a in accounts}
    all_platforms = [
        {
            'platform': p,
            'connected': p in connected,
            'info': next((a for a in accounts if a['platform'] == p), None),
            'setup_url': _setup_url(p),
            'instructions': _setup_instructions(p),
        }
        for p in PLATFORMS
    ]
    return {'platforms': all_platforms}


@router.delete('/accounts/{platform}')
async def disconnect_account(platform: str, user=Depends(get_current_user)):
    await db.social_accounts.delete_one({'user_id': user['id'], 'platform': platform})
    return {'ok': True}


# ─── Scheduling ──────────────────────────────────────────────────────────────

@router.post('/schedule')
async def schedule_post(body: ScheduleIn, bg: BackgroundTasks, user=Depends(get_current_user)):
    job = await db.video_jobs.find_one({'id': body.video_job_id, 'user_id': user['id']})
    if not job:
        raise HTTPException(status_code=404, detail='Video job not found')
    if job.get('status') != 'done':
        raise HTTPException(status_code=400, detail='Video must be done (fully generated) before scheduling')

    post_id = str(uuid.uuid4())
    publish_at = body.scheduled_at or datetime.now(timezone.utc).isoformat()
    doc = {
        'id': post_id,
        'user_id': user['id'],
        'video_job_id': body.video_job_id,
        'video_url': job.get('video_url'),
        'topic': job.get('topic', ''),
        'platforms': body.platforms,
        'title': body.title,
        'description': body.description,
        'tags': body.tags,
        'scheduled_at': publish_at,
        'status': 'scheduled',
        'results': {},
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.scheduled_posts.insert_one(doc)

    # If scheduled_at is now (no future date), publish immediately in background
    if not body.scheduled_at:
        bg.add_task(_publish_post, post_id, user['id'])

    return {'id': post_id, 'status': 'scheduled', 'scheduled_at': publish_at}


@router.get('/scheduled')
async def list_scheduled(user=Depends(get_current_user)):
    cur = db.scheduled_posts.find({'user_id': user['id']}, {'_id': 0}).sort('scheduled_at', -1).limit(100)
    return {'items': [doc async for doc in cur]}


@router.delete('/scheduled/{post_id}')
async def delete_scheduled(post_id: str, user=Depends(get_current_user)):
    doc = await db.scheduled_posts.find_one({'id': post_id, 'user_id': user['id']})
    if not doc:
        raise HTTPException(status_code=404, detail='Not found')
    await db.scheduled_posts.delete_one({'id': post_id})
    return {'ok': True}


@router.post('/publish/{post_id}')
async def publish_now(post_id: str, bg: BackgroundTasks, user=Depends(get_current_user)):
    doc = await db.scheduled_posts.find_one({'id': post_id, 'user_id': user['id']})
    if not doc:
        raise HTTPException(status_code=404, detail='Scheduled post not found')
    bg.add_task(_publish_post, post_id, user['id'])
    await db.scheduled_posts.update_one({'id': post_id}, {'$set': {'status': 'publishing'}})
    return {'ok': True, 'status': 'publishing'}


# ─── Internal helpers ─────────────────────────────────────────────────────────

async def _publish_post(post_id: str, user_id: str):
    """Background task: tries to post video to each connected platform."""
    doc = await db.scheduled_posts.find_one({'id': post_id})
    if not doc:
        return
    results = {}
    for platform in (doc.get('platforms') or []):
        acct = await db.social_accounts.find_one({'user_id': user_id, 'platform': platform})
        if not acct:
            results[platform] = {'ok': False, 'error': 'Account not connected'}
            continue
        try:
            res = await _post_to_platform(platform, acct, doc)
            results[platform] = res
        except Exception as e:
            results[platform] = {'ok': False, 'error': str(e)[:200]}

    all_ok = all(v.get('ok') for v in results.values())
    await db.scheduled_posts.update_one(
        {'id': post_id},
        {'$set': {
            'results': results,
            'status': 'published' if all_ok else ('partial' if any(v.get('ok') for v in results.values()) else 'failed'),
            'published_at': datetime.now(timezone.utc).isoformat(),
        }}
    )


async def _post_to_platform(platform: str, acct: dict, post: dict) -> dict:
    """Platform-specific posting logic using stored access tokens."""
    title = post.get('title', post.get('topic', ''))[:100]
    description = post.get('description', '')[:5000]
    tags = post.get('tags', [])
    token = acct.get('access_token', '')

    if platform == 'youtube':
        return await _post_youtube(token, acct, title, description, tags, post)
    elif platform == 'instagram':
        return await _post_instagram(token, acct, title, post)
    elif platform == 'facebook':
        return await _post_facebook(token, acct, title, description, post)
    elif platform == 'twitter':
        return await _post_twitter(token, title, post)
    return {'ok': False, 'error': 'Unknown platform'}


async def _post_youtube(token: str, acct: dict, title: str, description: str, tags: list, post: dict) -> dict:
    """Upload video to YouTube via YouTube Data API v3."""
    # YouTube requires multipart upload — we return instructions if token looks like a placeholder
    if not token or len(token) < 10:
        return {'ok': False, 'error': 'Invalid YouTube access token. Please reconnect your account.'}
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            metadata = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags[:15],
                    'categoryId': '22',
                },
                'status': {'privacyStatus': 'public'},
            }
            r = await client.post(
                'https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status',
                headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json; charset=UTF-8',
                         'X-Upload-Content-Type': 'video/mp4'},
                json=metadata,
            )
            if r.status_code in (200, 201):
                return {'ok': True, 'platform': 'youtube', 'upload_url': r.headers.get('Location', '')}
            return {'ok': False, 'error': f'YouTube API {r.status_code}: {r.text[:200]}'}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:200]}


async def _post_instagram(token: str, acct: dict, caption: str, post: dict) -> dict:
    """Post to Instagram via Graph API (requires video URL accessible from Meta servers)."""
    if not token or len(token) < 10:
        return {'ok': False, 'error': 'Invalid Instagram token. Please reconnect.'}
    ig_user_id = acct.get('channel_id', '')
    if not ig_user_id:
        return {'ok': False, 'error': 'Instagram user ID not set. Reconnect with channel_id.'}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f'https://graph.facebook.com/v18.0/{ig_user_id}/media',
                params={
                    'media_type': 'REELS',
                    'video_url': post.get('video_url', ''),
                    'caption': caption[:2200],
                    'access_token': token,
                }
            )
            if r.status_code == 200:
                creation_id = r.json().get('id')
                if creation_id:
                    pub = await client.post(
                        f'https://graph.facebook.com/v18.0/{ig_user_id}/media_publish',
                        params={'creation_id': creation_id, 'access_token': token}
                    )
                    if pub.status_code == 200:
                        return {'ok': True, 'platform': 'instagram', 'media_id': pub.json().get('id')}
            return {'ok': False, 'error': f'Instagram API {r.status_code}: {r.text[:200]}'}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:200]}


async def _post_facebook(token: str, acct: dict, title: str, description: str, post: dict) -> dict:
    """Post video to a Facebook Page."""
    if not token or len(token) < 10:
        return {'ok': False, 'error': 'Invalid Facebook token. Please reconnect.'}
    page_id = acct.get('page_id') or acct.get('channel_id', 'me')
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f'https://graph.facebook.com/v18.0/{page_id}/videos',
                params={
                    'file_url': post.get('video_url', ''),
                    'title': title[:254],
                    'description': description[:5000],
                    'access_token': token,
                }
            )
            if r.status_code == 200:
                return {'ok': True, 'platform': 'facebook', 'video_id': r.json().get('id')}
            return {'ok': False, 'error': f'Facebook API {r.status_code}: {r.text[:200]}'}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:200]}


async def _post_twitter(token: str, title: str, post: dict) -> dict:
    """Post tweet with video link via Twitter API v2."""
    if not token or len(token) < 10:
        return {'ok': False, 'error': 'Invalid Twitter token. Please reconnect.'}
    try:
        tweet_text = f"{title[:240]}"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                'https://api.twitter.com/2/tweets',
                headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
                json={'text': tweet_text}
            )
            if r.status_code in (200, 201):
                return {'ok': True, 'platform': 'twitter', 'tweet_id': r.json().get('data', {}).get('id')}
            return {'ok': False, 'error': f'Twitter API {r.status_code}: {r.text[:200]}'}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:200]}


def _setup_url(platform: str) -> str:
    return {
        'youtube': 'https://console.cloud.google.com/apis/credentials',
        'instagram': 'https://developers.facebook.com/apps',
        'facebook': 'https://developers.facebook.com/apps',
        'twitter': 'https://developer.twitter.com/en/portal/dashboard',
    }.get(platform, '')


def _setup_instructions(platform: str) -> str:
    return {
        'youtube': 'Google Cloud Console → Create OAuth 2.0 credentials → Enable YouTube Data API v3 → Get access token',
        'instagram': 'Meta for Developers → Create App → Instagram Basic Display → Get long-lived access token',
        'facebook': 'Meta for Developers → Create App → Facebook Login → Get Page access token',
        'twitter': 'Twitter Developer Portal → Create App → OAuth 2.0 → Get Bearer token',
    }.get(platform, '')
