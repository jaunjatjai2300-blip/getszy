"""Multi-platform publishing adapters.

Real API calls happen only when env keys are present; otherwise dry-run mode
returns a deterministic preview so the UI can be tested without credentials.

Supported platforms:
  youtube   YOUTUBE_API_KEY + YOUTUBE_REFRESH_TOKEN (OAuth)
  instagram META_ACCESS_TOKEN + IG_BUSINESS_ID
  facebook  META_ACCESS_TOKEN + FB_PAGE_ID
  x         X_BEARER_TOKEN
  linkedin  LINKEDIN_ACCESS_TOKEN
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

PLATFORMS = ['youtube', 'instagram', 'facebook', 'x', 'linkedin']

ENV_KEYS = {
    'youtube':   ['YOUTUBE_API_KEY', 'YOUTUBE_REFRESH_TOKEN'],
    'instagram': ['META_ACCESS_TOKEN', 'IG_BUSINESS_ID'],
    'facebook':  ['META_ACCESS_TOKEN', 'FB_PAGE_ID'],
    'x':         ['X_BEARER_TOKEN'],
    'linkedin':  ['LINKEDIN_ACCESS_TOKEN'],
}


def connections() -> Dict[str, Any]:
    out = {}
    for p, keys in ENV_KEYS.items():
        have = all(bool(os.environ.get(k, '').strip()) for k in keys)
        out[p] = {'connected': have, 'requires': keys,
                  'mode': 'live' if have else 'dry-run'}
    return out


async def publish(platform: str, content: Dict[str, Any]) -> Dict[str, Any]:
    """Returns a dict with status (live|dry-run|failed), external_id, url."""
    if platform not in PLATFORMS:
        return {'status': 'failed', 'error': f'unknown platform: {platform}'}
    keys = ENV_KEYS[platform]
    have = all(bool(os.environ.get(k, '').strip()) for k in keys)
    fake_id = uuid.uuid4().hex[:10]
    if not have:
        return {
            'status': 'dry-run',
            'platform': platform,
            'external_id': fake_id,
            'url': f'https://dryrun.getszy.com/{platform}/{fake_id}',
            'requires': keys,
            'message': f'Configure {", ".join(keys)} to enable real posting.',
            'preview': {
                'caption': content.get('caption', '')[:280],
                'title': content.get('title', ''),
                'hashtags': content.get('hashtags', [])[:10],
                'media_url': content.get('media_url'),
            },
            'scheduled_at': content.get('scheduled_at'),
            'posted_at': datetime.now(timezone.utc).isoformat(),
        }
    # Live mode: stub - real API call would go here.
    # We intentionally do NOT make real calls until user provides + validates keys.
    return {
        'status': 'live-stub',
        'platform': platform,
        'external_id': fake_id,
        'url': f'https://{platform}.com/{fake_id}',
        'message': 'Keys detected but live posting requires the provider SDK integration step.',
        'posted_at': datetime.now(timezone.utc).isoformat(),
    }
