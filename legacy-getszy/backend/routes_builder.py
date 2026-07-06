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
from credits import deduct, refund

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
    ok, msg, _ = await deduct(user['id'], 'builder_website')
    if not ok:
        raise HTTPException(402, msg)
    try:
        html = await _generate_site(body.prompt)
    except Exception as e:
        logger.exception('generate failed')
        await refund(user['id'], 'builder_website', reason='generation_failed')
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
    ok, msg, _ = await deduct(user['id'], 'builder_refine')
    if not ok:
        raise HTTPException(402, msg)
    try:
        new_html = await _generate_site(body.prompt, current_html=p.get('html_content'), session_id=f"builder-{pid}")
    except Exception as e:
        logger.exception('refine failed')
        await refund(user['id'], 'builder_refine', reason='generation_failed')
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


# ============================================================
# Faceless Channel Builder — 30-day content calendar + batch execute
# ============================================================
import json as _json
import uuid as _uuid
from typing import List as _List, Dict as _Dict, Any as _Any
from pydantic import BaseModel as _BaseModel, Field as _Field


class ChannelPlanIn(_BaseModel):
    niche: str = _Field(..., min_length=1, max_length=300)
    audience: str = 'Indian creators'
    style: str = 'energetic'
    posts_per_week: int = 5
    language: str = 'hinglish'
    orientation: str = '9:16'


class ChannelExecuteIn(_BaseModel):
    channel_id: str
    max_videos: int = 5


@router.post('/channel/plan')
async def channel_plan(body: ChannelPlanIn, user=Depends(get_current_user)):
    total = max(4, min(30, body.posts_per_week * 4))
    system = (
        f'You are a YouTube/Reels content strategist for Indian creators. Given a niche, plan '
        f'{total} videos for the next 30 days. Reply ONLY JSON: '
        '{channel_name, channel_bio, pillars: [4 with theme], videos: [{day, topic, hook, format, pillar}]}.'
    )
    user_msg = f'Niche: {body.niche}\nAudience: {body.audience}\nStyle: {body.style}\nLanguage: {body.language}'
    raw = await chat_completion(system=system, user=user_msg, temperature=0.6)
    s = (raw or '').find('{'); e = (raw or '').rfind('}')
    plan = None
    if s != -1:
        try: plan = _json.loads(raw[s:e+1])
        except Exception: plan = None
    if not plan or not plan.get('videos'):
        plan = {'channel_name': body.niche.title(), 'channel_bio': body.niche,
                'pillars': [{'theme': 'Educate'}, {'theme': 'Trends'}, {'theme': 'Stories'}, {'theme': 'How-to'}],
                'videos': [{'day': i+1, 'topic': f'{body.niche} idea {i+1}', 'hook': '', 'format': 'reel',
                            'pillar': 'Educate'} for i in range(total)]}
    channel_id = str(_uuid.uuid4())
    doc = {'id': channel_id, 'user_id': user['id'], 'niche': body.niche, 'audience': body.audience,
           'style': body.style, 'language': body.language, 'orientation': body.orientation,
           'plan': plan, 'status': 'planned', 'executed_video_ids': [],
           'created_at': _now()}
    await db.channel_plans.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.post('/channel/execute')
async def channel_execute(body: ChannelExecuteIn, user=Depends(get_current_user)):
    from video.pipeline import run_job as _run_video_job
    import asyncio as _asyncio
    ch = await db.channel_plans.find_one({'id': body.channel_id, 'user_id': user['id']}, {'_id': 0})
    if not ch:
        raise HTTPException(404, 'channel not found')
    videos = (ch.get('plan') or {}).get('videos') or []
    to_run = videos[:max(1, min(10, body.max_videos))]
    job_ids: _List[str] = []
    for v in to_run:
        job_id = str(_uuid.uuid4())
        params = {'topic': v.get('topic', ch.get('niche')), 'orientation': ch.get('orientation', '9:16'),
                  'language': ch.get('language', 'hinglish'), 'voice_gender': 'female',
                  'target_seconds': 45, 'tone': ch.get('style', 'energetic'), 'subtitles': True,
                  'audience': ch.get('audience', 'indian creators')}
        await db.video_jobs.insert_one({'id': job_id, 'user_id': user['id'], 'topic': v.get('topic'),
                                         'orientation': params['orientation'], 'language': params['language'],
                                         'status': 'queued', 'percent': 0, 'params': params,
                                         'channel_id': body.channel_id,
                                         'created_at': _now()})
        _asyncio.create_task(_run_video_job(job_id, params))
        job_ids.append(job_id)
    await db.channel_plans.update_one({'id': body.channel_id},
        {'$set': {'status': 'executing'}, '$push': {'executed_video_ids': {'$each': job_ids}}})
    return {'channel_id': body.channel_id, 'queued_video_ids': job_ids, 'count': len(job_ids)}


@router.get('/channel')
async def list_channels(user=Depends(get_current_user)):
    cur = db.channel_plans.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(30)
    return {'items': [doc async for doc in cur]}


@router.get('/channel/{cid}')
async def get_channel(cid: str, user=Depends(get_current_user)):
    ch = await db.channel_plans.find_one({'id': cid, 'user_id': user['id']}, {'_id': 0})
    if not ch:
        raise HTTPException(404, 'not found')
    return ch


@router.delete('/channel/{cid}')
async def del_channel(cid: str, user=Depends(get_current_user)):
    r = await db.channel_plans.delete_one({'id': cid, 'user_id': user['id']})
    return {'deleted': r.deleted_count}


# ============================================================
# Custom AI Agent Factory — user-defined agents beyond the preset 10
# ============================================================

class CustomAgentIn(_BaseModel):
    name: str
    role: str
    system_prompt: str
    param_keys: _List[str] = ['input']
    color: str = '#1e8e8e'
    icon: str = 'Bot'


class AgentRunIn(_BaseModel):
    params: _Dict[str, _Any] = {}


@router.post('/agent')
async def create_agent(body: CustomAgentIn, user=Depends(get_current_user)):
    if len(body.name.strip()) < 2:
        raise HTTPException(400, 'name too short')
    doc = {'id': str(_uuid.uuid4()), 'user_id': user['id'], 'name': body.name.strip()[:60],
           'role': body.role.strip()[:280], 'system_prompt': body.system_prompt.strip()[:2000],
           'param_keys': body.param_keys or ['input'], 'color': body.color, 'icon': body.icon,
           'created_at': _now()}
    await db.custom_agents.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.get('/agent')
async def list_custom_agents(user=Depends(get_current_user)):
    cur = db.custom_agents.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1)
    return {'items': [doc async for doc in cur]}


@router.post('/agent/{aid}/run')
async def run_custom_agent(aid: str, body: AgentRunIn, user=Depends(get_current_user)):
    ag = await db.custom_agents.find_one({'id': aid, 'user_id': user['id']}, {'_id': 0})
    if not ag:
        raise HTTPException(404, 'agent not found')
    user_lines = [f'{k}: {str(v)[:1000]}' for k, v in (body.params or {}).items() if v not in (None, '', [])]
    prompt = '\n'.join(user_lines) or 'No parameters provided.'
    raw = await chat_completion(system=ag['system_prompt'], user=prompt, session_id=f'custom-{aid}', temperature=0.6)
    parsed = None
    s = (raw or '').find('{'); e = (raw or '').rfind('}')
    if s != -1:
        try: parsed = _json.loads(raw[s:e+1])
        except Exception: parsed = None
    rec = {'id': str(_uuid.uuid4()), 'user_id': user['id'], 'agent_id': aid,
           'params': body.params, 'raw': (raw or '')[:4000], 'parsed': parsed,
           'created_at': _now()}
    await db.custom_agent_runs.insert_one(rec)
    rec.pop('_id', None)
    return rec


@router.get('/agent/{aid}/history')
async def custom_agent_history(aid: str, user=Depends(get_current_user)):
    cur = db.custom_agent_runs.find({'agent_id': aid, 'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(30)
    return {'items': [doc async for doc in cur]}


@router.delete('/agent/{aid}')
async def del_custom_agent(aid: str, user=Depends(get_current_user)):
    r = await db.custom_agents.delete_one({'id': aid, 'user_id': user['id']})
    return {'deleted': r.deleted_count}


# ============================================================
# Starter Kits — downloadable zips for mobile / fullstack / blog
# ============================================================

class StarterIn(_BaseModel):
    kind: str        # mobileapp | fullstack | blog
    prompt: str
    app_name: str = ''


@router.post('/starter')
async def make_starter(body: StarterIn, user=Depends(get_current_user)):
    from builder_starters import gen_mobileapp_zip, gen_fullstack_zip, gen_blog_zip
    import os as _os
    kind = body.kind.lower()
    if kind not in ('mobileapp', 'fullstack', 'blog'):
        raise HTTPException(400, 'kind must be mobileapp|fullstack|blog')
    if len(body.prompt.strip()) < 4:
        raise HTTPException(400, 'prompt too short')
    name = body.app_name.strip() or _derive_name(body.prompt)
    try:
        if kind == 'mobileapp':
            data = await gen_mobileapp_zip(body.prompt, name)
        elif kind == 'fullstack':
            data = await gen_fullstack_zip(body.prompt, name)
        else:
            data = await gen_blog_zip(body.prompt, name)
    except Exception as e:
        logger.exception('starter gen failed')
        raise HTTPException(500, f'Generation failed: {e}')
    starter_id = str(_uuid.uuid4())
    starters_dir = _os.path.join(_os.path.dirname(__file__), 'media_cache', 'starters')
    _os.makedirs(starters_dir, exist_ok=True)
    zip_path = _os.path.join(starters_dir, f'{starter_id}.zip')
    with open(zip_path, 'wb') as f:
        f.write(data)
    doc = {'id': starter_id, 'user_id': user['id'], 'kind': kind, 'name': name,
           'prompt': body.prompt, 'size_bytes': len(data), 'created_at': _now()}
    await db.builder_starters.insert_one(doc)
    doc.pop('_id', None)
    doc['download_url'] = f'/api/builder/starter/{starter_id}/download'
    return doc


@router.get('/starter')
async def list_starters(user=Depends(get_current_user)):
    cur = db.builder_starters.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1).limit(50)
    items = [doc async for doc in cur]
    for it in items:
        it['download_url'] = f'/api/builder/starter/{it["id"]}/download'
    return {'items': items}


@router.get('/starter/{sid}/download')
async def download_starter(sid: str, user=Depends(get_current_user)):
    import os as _os
    from fastapi.responses import FileResponse as _FileResponse
    doc = await db.builder_starters.find_one({'id': sid, 'user_id': user['id']})
    if not doc:
        raise HTTPException(404, 'starter not found')
    starters_dir = _os.path.join(_os.path.dirname(__file__), 'media_cache', 'starters')
    path = _os.path.join(starters_dir, f'{sid}.zip')
    if not _os.path.exists(path):
        raise HTTPException(404, 'starter not found')
    return _FileResponse(path, media_type='application/zip', filename=f'{sid[:8]}-starter.zip')


@router.delete('/starter/{sid}')
async def del_starter(sid: str, user=Depends(get_current_user)):
    import os as _os
    doc = await db.builder_starters.find_one({'id': sid, 'user_id': user['id']})
    if not doc:
        raise HTTPException(404, 'not found')
    await db.builder_starters.delete_one({'id': sid})
    starters_dir = _os.path.join(_os.path.dirname(__file__), 'media_cache', 'starters')
    path = _os.path.join(starters_dir, f'{sid}.zip')
    try:
        if _os.path.exists(path): _os.remove(path)
    except Exception: pass
    return {'ok': True}


# ============================================================
# Build Studio Hub — aggregated counts + recent projects
# ============================================================

@router.get('/hub')
async def build_hub(user=Depends(get_current_user)):
    webapps = await db.builder_projects.count_documents({'user_id': user['id']})
    channels = await db.channel_plans.count_documents({'user_id': user['id']})
    agents = await db.custom_agents.count_documents({'user_id': user['id']})
    starters = await db.builder_starters.count_documents({'user_id': user['id']})
    videos = await db.video_jobs.count_documents({'user_id': user['id']})
    return {
        'counts': {'webapps': webapps, 'channels': channels, 'agents': agents,
                   'starters': starters, 'videos': videos},
        'categories': [
            {'id': 'webapp',    'title': 'Web App / Landing Page',  'desc': 'Prompt \u2192 single-page site with live preview.', 'icon': 'Globe',    'color': '#1e8e8e'},
            {'id': 'channel',   'title': 'Faceless Video Channel',  'desc': '30-day content plan \u2192 batch generate + schedule.', 'icon': 'Youtube',  'color': '#c97a87'},
            {'id': 'agent',     'title': 'Custom AI Agent',         'desc': 'Design your own agent + tools + persona.', 'icon': 'Bot',       'color': '#7c3aed'},
            {'id': 'mobileapp', 'title': 'Mobile App (Expo/RN)',    'desc': 'Downloadable React Native starter zip.', 'icon': 'Smartphone', 'color': '#e0a458'},
            {'id': 'fullstack', 'title': 'Full-Stack Website',      'desc': 'FastAPI + React + Mongo starter zip.', 'icon': 'Layers',    'color': '#5d8f8e'},
            {'id': 'blog',      'title': 'Blog / Content Site',     'desc': 'Multi-post static blog zip \u2014 deploy anywhere.', 'icon': 'BookOpen',  'color': '#9b6a3f'},
        ],
    }
