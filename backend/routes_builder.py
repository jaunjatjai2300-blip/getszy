"""Talk-to-Build Studio — multi-agent single-page-site generator (CPU-friendly)."""
import io
import re
import zipfile
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from db import db
from models import BuilderProject, BuilderProjectIn, BuilderRefineIn, BuilderHistoryItem
from auth import get_current_user, get_optional_user
from llm_provider import chat_completion
from subscription import can_use_studio, increment_studio_builds

logger = logging.getLogger('getszy.builder')
router = APIRouter(prefix='/builder', tags=['builder'])


SYSTEM_PROMPT_GENERATE = """You are an elite front-end web developer.

TASK: Generate a stunning, modern, fully-responsive SINGLE-PAGE WEBSITE based on the user's request.

STRICT OUTPUT RULES:
1. Output ONLY a SINGLE complete HTML document. No prose. No markdown fences. No explanations.
2. Begin with <!DOCTYPE html> and end with </html>.
3. Use Tailwind CSS via CDN: <script src="https://cdn.tailwindcss.com"></script>
4. Use Google Fonts via <link> for typography (one display + one body font).
5. Use real, free, royalty-friendly placeholder images from https://images.unsplash.com (specific photo IDs) or https://picsum.photos. NEVER use placeholder.com or broken URLs.
6. Include semantic sections: header/nav, hero, features/services, about/testimonials, CTA, footer.
7. Animations must be CSS-only (transform/opacity transitions). No external JS frameworks. Tiny inline <script> for menu toggle is OK.
8. Modern design: generous whitespace, premium typography, soft shadows, rounded corners, smooth hover states.
9. Fully responsive (mobile-first).
10. NEVER include forms that POST to external URLs. NEVER include trackers, analytics, or fetch() to third-party.
11. Total HTML should be 200-800 lines (rich but loadable on CPU).

START IMMEDIATELY WITH <!DOCTYPE html>. End with </html>. Nothing else."""


SYSTEM_PROMPT_REFINE = """You are an elite front-end web developer refining an existing single-page website.

You will be given:
1. The CURRENT HTML of the website
2. The user's REFINEMENT REQUEST

OUTPUT RULES:
1. Output ONLY the COMPLETE, UPDATED HTML document. No prose. No markdown.
2. Apply the user's request precisely while keeping the rest of the design coherent.
3. Maintain Tailwind CDN + responsive design.
4. Begin with <!DOCTYPE html>. End with </html>.

START IMMEDIATELY WITH <!DOCTYPE html>."""


def _extract_html(raw: str) -> str:
    """Pull the HTML doc out of the LLM response (strip any leading prose / fences)."""
    raw = raw.strip()
    # Strip code fences
    raw = re.sub(r'^```(?:html)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    # Find <!DOCTYPE html> or <html
    m = re.search(r'<!DOCTYPE\s+html[^>]*>', raw, re.IGNORECASE)
    if m:
        raw = raw[m.start():]
    else:
        m2 = re.search(r'<html', raw, re.IGNORECASE)
        if m2:
            raw = '<!DOCTYPE html>\n' + raw[m2.start():]
    # Truncate after </html>
    end = re.search(r'</html\s*>', raw, re.IGNORECASE)
    if end:
        raw = raw[:end.end()]
    return raw


def _sanitize(html: str) -> str:
    """Light sanitization — block dangerous patterns."""
    # Remove any localhost / file:// references just in case
    html = re.sub(r'(file://|javascript:eval\()', '', html, flags=re.IGNORECASE)
    return html


async def _generate_site(prompt: str, current_html: str | None = None, session_id: str = 'builder') -> str:
    if current_html:
        user_msg = (
            f"CURRENT HTML:\n```html\n{current_html}\n```\n\n"
            f"REFINEMENT REQUEST:\n{prompt}\n\n"
            "Now output the complete updated HTML document only."
        )
        system = SYSTEM_PROMPT_REFINE
    else:
        user_msg = f"Build this website:\n\n{prompt}"
        system = SYSTEM_PROMPT_GENERATE
    raw = await chat_completion(system=system, user=user_msg, session_id=session_id, temperature=0.6)
    html = _sanitize(_extract_html(raw))
    if not html.lower().startswith('<!doctype html'):
        # Fallback: wrap as html if model returned something weird
        html = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Generated</title>"
            "<script src='https://cdn.tailwindcss.com'></script></head><body class='p-8 font-sans'>"
            f"<pre class='whitespace-pre-wrap'>{raw}</pre></body></html>"
        )
    return html


def _now():
    return datetime.now(timezone.utc).isoformat()


def _derive_name(prompt: str) -> str:
    words = re.findall(r'[A-Za-z0-9]+', prompt)[:6]
    return ' '.join(words).title() or 'Untitled Project'


@router.post('/projects')
async def create_project(body: BuilderProjectIn, user=Depends(get_current_user)):
    if not body.prompt.strip():
        raise HTTPException(400, 'Prompt required')
    ok, msg, _ = await can_use_studio(user)
    if not ok:
        raise HTTPException(402, msg)
    try:
        html = await _generate_site(body.prompt)
    except Exception as e:
        logger.exception('generate failed')
        raise HTTPException(500, f'Generation failed: {e}')
    name = (body.name or _derive_name(body.prompt))[:80]
    history = [
        BuilderHistoryItem(timestamp=_now(), prompt=body.prompt, role='user'),
        BuilderHistoryItem(timestamp=_now(), prompt='Initial build complete', role='assistant', snapshot=html),
    ]
    project = BuilderProject(user_id=user['id'], name=name, prompt=body.prompt, html_content=html, history=history)
    await db.builder_projects.insert_one(project.model_dump())
    await increment_studio_builds(user['id'])
    return project.model_dump()


@router.get('/projects')
async def list_projects(user=Depends(get_current_user)):
    items = await db.builder_projects.find({'user_id': user['id']}, {'_id': 0, 'html_content': 0, 'history': 0}).sort('updated_at', -1).to_list(100)
    return items


@router.get('/projects/{pid}')
async def get_project(pid: str, user=Depends(get_current_user)):
    p = await db.builder_projects.find_one({'id': pid, 'user_id': user['id']}, {'_id': 0})
    if not p:
        raise HTTPException(404, 'Project not found')
    return p


@router.post('/projects/{pid}/refine')
async def refine_project(pid: str, body: BuilderRefineIn, user=Depends(get_current_user)):
    p = await db.builder_projects.find_one({'id': pid, 'user_id': user['id']}, {'_id': 0})
    if not p:
        raise HTTPException(404, 'Project not found')
    ok, msg, _ = await can_use_studio(user)
    if not ok:
        raise HTTPException(402, msg)
    try:
        new_html = await _generate_site(body.prompt, current_html=p.get('html_content'), session_id=f"builder-{pid}")
    except Exception as e:
        logger.exception('refine failed')
        raise HTTPException(500, f'Refinement failed: {e}')
    new_history = p.get('history', []) + [
        {'timestamp': _now(), 'prompt': body.prompt, 'role': 'user', 'snapshot': None},
        {'timestamp': _now(), 'prompt': 'Refinement applied', 'role': 'assistant', 'snapshot': new_html},
    ]
    await db.builder_projects.update_one(
        {'id': pid},
        {'$set': {'html_content': new_html, 'history': new_history, 'updated_at': _now(), 'prompt': body.prompt}},
    )
    await increment_studio_builds(user['id'])
    return await db.builder_projects.find_one({'id': pid}, {'_id': 0})


@router.delete('/projects/{pid}')
async def delete_project(pid: str, user=Depends(get_current_user)):
    res = await db.builder_projects.delete_one({'id': pid, 'user_id': user['id']})
    return {'deleted': res.deleted_count}


@router.get('/projects/{pid}/download')
async def download_project(pid: str, user=Depends(get_current_user)):
    p = await db.builder_projects.find_one({'id': pid, 'user_id': user['id']}, {'_id': 0})
    if not p:
        raise HTTPException(404, 'Project not found')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('index.html', p.get('html_content', ''))
        z.writestr(
            'README.md',
            f"# {p['name']}\n\nGenerated by getszy.com Talk-to-Build Studio.\n\n## Prompt\n{p.get('prompt','')}\n\nOpen `index.html` in your browser.\n",
        )
    buf.seek(0)
    safe_name = re.sub(r'[^a-zA-Z0-9-]+', '-', p['name']).strip('-') or 'project'
    return StreamingResponse(
        buf,
        media_type='application/zip',
        headers={'Content-Disposition': f'attachment; filename="{safe_name}.zip"'},
    )


@router.get('/projects/{pid}/preview', response_class=HTMLResponse)
async def preview_project(pid: str):
    """Public preview (no auth) — safe because content is sandboxed by iframe on client."""
    p = await db.builder_projects.find_one({'id': pid}, {'_id': 0, 'html_content': 1})
    if not p:
        return Response(content='<h1>Not found</h1>', media_type='text/html', status_code=404)
    return HTMLResponse(content=p.get('html_content', '<h1>Empty</h1>'))
