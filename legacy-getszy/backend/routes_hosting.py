"""Subdomain/Path-based Hosting for Neo-built webapps & blogs.

Design:
  - In this preview environment (Kubernetes ingress routes `/api/*` to backend),
    hosted sites are served at `/api/host/{slug}/` (path-based).
  - In production on user's VPS, Caddy config maps `{slug}.getszy.com` → `getszy.com/api/host/{slug}/`
    (see /api/hosting/caddy-snippet endpoint for the config).

Collections:
  - hosted_sites: {id, user_id, slug (unique), asset_id, project_id (chat),
                   source_kind, source_ref, html, size_bytes, status,
                   created_at, updated_at}
  - workspace_deployments: also gets a mirror record for the Deployments tab.
"""
import re
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from auth import get_current_user
from db import db

router = APIRouter(prefix='/hosting', tags=['hosting'])

# Public host router (no auth) — separate prefix so unauth users can view hosted sites
host_router = APIRouter(prefix='/host', tags=['hosted-sites'])

SLUG_RE = re.compile(r'^[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])?$')
RESERVED = {'admin', 'api', 'www', 'app', 'dashboard', 'labs', 'auth',
            'login', 'signup', 'checkout', 'cart', 'shop', 'academy',
            'studio', 'account', 'pricing', 'host', 'hosting', 'health',
            'mail', 'ftp', 'blog', 'static', 'assets'}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_slug(text: str) -> str:
    s = re.sub(r'[^a-z0-9-]+', '-', (text or '').lower()).strip('-')
    s = re.sub(r'-+', '-', s)[:40].strip('-')
    return s or f'site-{uuid.uuid4().hex[:8]}'


async def _asset_html(user_id: str, asset_id: str) -> tuple[str, dict]:
    """Extract HTML content from an asset. Supports webapp / starter_blog kinds."""
    asset = await db.chat_assets.find_one({'id': asset_id, 'user_id': user_id}, {'_id': 0})
    if not asset:
        raise HTTPException(404, 'asset not found')
    kind = asset.get('kind') or ''
    data = asset.get('data') or {}
    if kind == 'webapp':
        bpid = data.get('project_id')
        if not bpid:
            raise HTTPException(400, 'webapp asset missing project_id')
        bp = await db.builder_projects.find_one({'id': bpid}, {'_id': 0, 'html_content': 1})
        if not bp:
            raise HTTPException(404, 'builder project not found')
        return bp.get('html_content') or '<h1>Empty</h1>', asset
    if kind == 'starter_blog':
        # blog starter zips have index.html inside; we don't unzip here — fallback
        html = data.get('index_html') or data.get('html')
        if not html:
            raise HTTPException(400, 'blog starter has no inline index_html; use webapp assets for now')
        return html, asset
    raise HTTPException(400, f'asset kind "{kind}" is not deployable yet (supported: webapp)')


# ---------- Deploy ----------
class DeployIn(BaseModel):
    project_id: str  # chat project id
    asset_id: str
    slug: Optional[str] = None


@router.post('/deploy')
async def deploy(body: DeployIn, user=Depends(get_current_user)):
    # Validate chat project belongs to user
    proj = await db.chat_projects.find_one({'id': body.project_id, 'user_id': user['id']}, {'_id': 0})
    if not proj:
        raise HTTPException(404, 'workspace project not found')

    html, asset = await _asset_html(user['id'], body.asset_id)

    slug = (body.slug or '').strip().lower() or _make_slug(asset.get('title') or 'site')
    if not SLUG_RE.match(slug):
        raise HTTPException(400, 'slug must be 3-40 chars: lowercase letters, digits, hyphens')
    if slug in RESERVED:
        raise HTTPException(400, f'slug "{slug}" is reserved')

    # Uniqueness: allow same-slug only if same user replaces
    existing = await db.hosted_sites.find_one({'slug': slug}, {'_id': 0})
    if existing and existing.get('user_id') != user['id']:
        raise HTTPException(409, 'slug already taken by another user')

    doc = {
        'id': existing['id'] if existing else str(uuid.uuid4()),
        'user_id': user['id'],
        'slug': slug,
        'asset_id': body.asset_id,
        'project_id': body.project_id,
        'source_kind': asset.get('kind'),
        'source_ref': (asset.get('data') or {}).get('project_id'),
        'html': html,
        'size_bytes': len(html.encode('utf-8')),
        'status': 'live',
        'created_at': existing['created_at'] if existing else _iso(),
        'updated_at': _iso(),
        'title': asset.get('title') or slug,
    }
    await db.hosted_sites.update_one({'slug': slug}, {'$set': doc}, upsert=True)

    # Mirror to workspace_deployments so it shows up in the Deploy tab
    hosted_url = f'/api/host/{slug}/'
    deploy_doc = {
        'id': str(uuid.uuid4()),
        'project_id': body.project_id,
        'user_id': user['id'],
        'kind': asset.get('kind') or 'webapp',
        'target': slug,
        'url': hosted_url,
        'meta': {'hosted_site_id': doc['id'], 'size_bytes': doc['size_bytes'],
                 'production_url': f'https://{slug}.getszy.com'},
        'status': 'live',
        'created_at': _iso(),
    }
    await db.workspace_deployments.insert_one(deploy_doc)
    deploy_doc.pop('_id', None)

    return {
        'ok': True,
        'slug': slug,
        'hosted_url': hosted_url,
        'production_url': f'https://{slug}.getszy.com',
        'size_bytes': doc['size_bytes'],
        'updated_at': doc['updated_at'],
        'deployment': deploy_doc,
    }


# ---------- List / Undeploy ----------
@router.get('/list')
async def list_sites(user=Depends(get_current_user)):
    items = [s async for s in db.hosted_sites.find({'user_id': user['id']}, {'_id': 0, 'html': 0}).sort('updated_at', -1).limit(100)]
    return {'items': items}


@router.delete('/{slug}')
async def undeploy(slug: str, user=Depends(get_current_user)):
    r = await db.hosted_sites.delete_one({'slug': slug, 'user_id': user['id']})
    if r.deleted_count == 0:
        raise HTTPException(404, 'not found')
    # mark existing deployments as offline
    await db.workspace_deployments.update_many(
        {'user_id': user['id'], 'target': slug},
        {'$set': {'status': 'offline', 'updated_at': _iso()}}
    )
    return {'ok': True, 'slug': slug}


# ---------- Caddy snippet (for production wildcard hosting on user's VPS) ----------
@router.get('/caddy-snippet', response_class=PlainTextResponse)
async def caddy_snippet(user=Depends(get_current_user)):
    """Return a Caddy config snippet the user can paste on their VPS.
    Assumes DNS wildcard *.getszy.com → VPS.
    """
    snippet = """# --- getszy dynamic subdomain hosting ---
# Prerequisite: DNS wildcard A record `*.getszy.com` → your VPS IP.
# Caddy will auto-provision TLS via on-demand for each subdomain.

*.getszy.com {
    @notReserved not host getszy.com www.getszy.com api.getszy.com
    handle @notReserved {
        # Extract subdomain (labels[0]) and proxy to backend /api/host/<slug>/
        rewrite * /api/host/{labels.2}{uri}
        reverse_proxy backend:8001
    }
    tls {
        on_demand
    }
}

# Add a rate-limit + allow-list on the on_demand_tls in Caddy globals:
# {
#   on_demand_tls {
#     ask http://backend:8001/api/hosting/tls-allow?domain={domain}
#     interval 2m
#     burst 5
#   }
# }
"""
    return snippet


@router.get('/tls-allow')
async def tls_allow(domain: str):
    """Endpoint Caddy calls to verify a domain is allowed for on-demand TLS.
    Returns 200 if a hosted_sites record exists for the subdomain slug.
    """
    if not domain.endswith('.getszy.com'):
        raise HTTPException(400, 'not a getszy subdomain')
    slug = domain.replace('.getszy.com', '').strip().lower()
    exists = await db.hosted_sites.find_one({'slug': slug}, {'_id': 0, 'id': 1})
    if not exists:
        raise HTTPException(404, 'slug not found')
    return {'ok': True, 'slug': slug}


# ---------- Public host route ----------
@host_router.get('/{slug}')
@host_router.get('/{slug}/')
async def host_root(slug: str):
    site = await db.hosted_sites.find_one({'slug': slug, 'status': 'live'}, {'_id': 0, 'html': 1, 'title': 1})
    if not site:
        return HTMLResponse(_not_found_html(slug), status_code=404)
    return HTMLResponse(content=site.get('html', ''))


@host_router.get('/{slug}/{path:path}')
async def host_subpath(slug: str, path: str):
    # Single-file HTML apps — everything routes to index; SPAs can handle their own routing.
    site = await db.hosted_sites.find_one({'slug': slug, 'status': 'live'}, {'_id': 0, 'html': 1})
    if not site:
        return HTMLResponse(_not_found_html(slug), status_code=404)
    return HTMLResponse(content=site.get('html', ''))


def _not_found_html(slug: str) -> str:
    return f"""<!DOCTYPE html><html><head><title>Not found</title>
<style>body{{font-family:system-ui,sans-serif;padding:64px;text-align:center;background:#fafaf7;color:#0f1a1a}}
h1{{font-size:64px;margin:0;color:#0d9488}}p{{color:#6b7280}}</style></head>
<body><h1>404</h1><p>No site deployed at <b>{slug}</b>.</p>
<p><a href="/dashboard" style="color:#0d9488">Go to Neo →</a></p></body></html>"""
