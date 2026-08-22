"""Talk-to-Build Studio — multi-agent single-page-site generator (CPU-friendly)."""
import io
import re
import json
import zipfile
import logging
import uuid
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, Response
from db import db
from models import (
    BuilderProject, BuilderProjectIn, BuilderRefineIn, BuilderHistoryItem,
    BuilderEvidenceUpdateIn, BuilderVersionIn, BuilderReleaseReviewIn,
)
from auth import get_current_user, get_optional_user
from llm_provider import chat_completion, professional_builder_completion
from credits import deduct, refund
from builder_agents import (
    ProfessionalCompositionError, build_site, refine_element, plan_site,
    design_site, review_site,
)
from builder_quality import evaluate_landing_page_quality
from builder_controls import mission_control_state
from template_catalog import public_template_catalog, get_template, recommend_template_id, render_customer_template

logger = logging.getLogger('getszy.builder')
router = APIRouter(prefix='/builder', tags=['builder'])
_TEMPLATE_ASSET_ROOT = Path(__file__).resolve().parent / "starter_templates" / "assets"
_TEMPLATE_ASSETS = {
    "dance-academy-hero.jpg": "image/jpeg",
    "brand-foundation-hero.jpg": "image/jpeg",
}


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
    """Pull HTML doc out of LLM response."""
    raw = raw.strip()
    raw = re.sub(r'^```(?:html)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    m = re.search(r'<!DOCTYPE\s+html[^>]*>', raw, re.IGNORECASE)
    if m:
        raw = raw[m.start():]
    else:
        m2 = re.search(r'<html', raw, re.IGNORECASE)
        if m2:
            raw = '<!DOCTYPE html>\n' + raw[m2.start():]
    end = re.search(r'</html\s*>', raw, re.IGNORECASE)
    if end:
        raw = raw[:end.end()]
    return raw


def _sanitize(html: str) -> str:
    """Strip dangerous patterns from LLM-generated HTML."""
    # Remove script tags and event handlers
    html = re.sub(r'<script[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'\bon\w+\s*=', '', html, flags=re.IGNORECASE)
    # Remove dangerous URIs
    html = re.sub(r'(file://|javascript:|data:text/html)', '', html, flags=re.IGNORECASE)
    # Remove iframe/object/embed
    html = re.sub(r'<(iframe|object|embed)[\s\S]*?</\1>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<(iframe|object|embed)[^>]*/?>', '', html, flags=re.IGNORECASE)
    # Remove style expressions (IE-based XSS)
    html = re.sub(r'expression\s*\(', '', html, flags=re.IGNORECASE)
    html = re.sub(r'@import\s', '', html, flags=re.IGNORECASE)
    return html


async def _generate_site(prompt: str, current_html: str | None = None, session_id: str = 'builder') -> str:
    """Generate or refine a site using the multi-agent pipeline."""
    if current_html:
        # Refinement: use single-pass refine (not full pipeline)
        user_msg = (
            f"CURRENT HTML:\n```html\n{current_html}\n```\n\n"
            f"REFINEMENT REQUEST:\n{prompt}\n\n"
            "Now output the complete updated HTML document only."
        )
        raw = await professional_builder_completion(
            system=SYSTEM_PROMPT_REFINE,
            user=user_msg,
            session_id=session_id,
            temperature=0.45,
            max_tokens=8000,
        )
        html = _sanitize(_extract_html(raw))
        if not html.lower().startswith('<!doctype html'):
            html = current_html  # Fallback: keep original
    else:
        # New site: run full multi-agent pipeline
        html = await build_site(prompt, session_id)
    return html


async def _stream_build_steps(prompt: str, session_id: str = 'builder'):
    """Generator that yields SSE events for each pipeline step."""
    async def emit(event: str, data: dict):
        yield f"event: {event}\ndata: {json.dumps(data)}\n\n"

    # Step 1: Plan
    yield emit('step', {'name': 'planner', 'status': 'started', 'message': 'Planning site structure...'})
    plan = await plan_site(prompt, session_id)
    yield emit('step', {'name': 'planner', 'status': 'done', 'plan': plan})

    # Step 2: Design
    yield emit('step', {'name': 'designer', 'status': 'started', 'message': 'Creating design brief...'})
    design = await design_site(plan, prompt, session_id)
    yield emit('step', {'name': 'designer', 'status': 'done', 'design': design})

    # Step 3: Code
    yield emit('step', {'name': 'coder', 'status': 'started', 'message': 'Generating HTML...'})
    from builder_agents import code_site
    html = await code_site(prompt, plan, design, session_id)
    yield emit('step', {'name': 'coder', 'status': 'done', 'preview': html[:500]})

    # Step 4: Review
    yield emit('step', {'name': 'reviewer', 'status': 'started', 'message': 'Reviewing and fixing...'})
    from builder_agents import review_site
    html = await review_site(html, session_id)
    yield emit('step', {'name': 'reviewer', 'status': 'done'})

    # Final result
    yield emit('complete', {'html': html})


def _now():
    return datetime.now(timezone.utc).isoformat()


def _derive_name(prompt: str) -> str:
    words = re.findall(r'[A-Za-z0-9]+', prompt)[:6]
    return ' '.join(words).title() or 'Untitled Project'


def _brief_to_generation_context(brief: dict | None) -> str:
    """Give the multi-agent builder concrete professional-output constraints."""
    brief = brief or {}
    entries = [
        ('Brand name', brief.get('brand_name')),
        ('Target audience', brief.get('audience')),
        ('Primary conversion goal', brief.get('primary_goal')),
        ('Primary CTA', brief.get('primary_cta')),
        ('Offer', brief.get('offer')),
        ('Visual direction', brief.get('visual_style')),
    ]
    proof_points = [str(item).strip() for item in brief.get('proof_points', []) if str(item).strip()]
    lines = [f'- {label}: {value}' for label, value in entries if str(value or '').strip()]
    if proof_points:
        lines.append('- Verified proof points supplied by the customer: ' + '; '.join(proof_points))
    if not lines:
        return ''
    return (
        '\n\nPROFESSIONAL PAGE BRIEF (follow this as product context):\n'
        + '\n'.join(lines)
        + '\nDo not invent testimonials, company logos, customer counts, prices, guarantees, legal claims, or product capabilities. '
          'Where proof is not supplied, use an honest proof-plan placeholder for the customer to complete before publishing.'
    )


@router.get('/template-assets/{asset_name}', response_class=FileResponse)
async def get_template_asset(asset_name: str):
    """Serve only approved static visual assets embedded by curated customer starters."""
    media_type = _TEMPLATE_ASSETS.get(asset_name)
    asset_path = (_TEMPLATE_ASSET_ROOT / asset_name).resolve()
    if not media_type or asset_path.parent != _TEMPLATE_ASSET_ROOT.resolve() or not asset_path.is_file():
        raise HTTPException(404, 'Template asset not found')
    return FileResponse(asset_path, media_type=media_type, headers={'Cache-Control': 'public, max-age=86400'})


@router.get('/templates')
async def list_professional_templates(user=Depends(get_current_user)):
    """Expose no new-build starters until category-specific professional packs are ready."""
    return {
        'templates': [],
        'notice': 'New customer website production is paused while Getszy prepares approved category-specific professional packs. Existing private projects remain available for review.',
    }


@router.post('/projects')
async def create_project(body: BuilderProjectIn, user=Depends(get_current_user)):
    if not body.prompt.strip():
        raise HTTPException(400, 'Prompt required')

    brief_data = body.brief.model_dump(exclude_none=True) if body.brief else {}
    project_id = str(uuid.uuid4())
    charged = user.get('role') not in ('admin', 'founder')
    ok, message, _balance_after = await deduct(
        user['id'],
        'builder_website',
        meta={'project_id': project_id, 'stage': 'professional_composition'},
        user=user,
    )
    if not ok:
        raise HTTPException(402, message)

    try:
        html = await build_site(body.prompt, session_id=f'professional-{project_id}', brief=brief_data)
        quality_report = evaluate_landing_page_quality(html, brief_data)

        # One bounded repair pass translates objective preflight failures into
        # concrete instructions for the managed quality ladder. A second failure is
        # not silently saved or presented as a finished professional result.
        if quality_report.get('status') == 'needs_work':
            html = await review_site(
                html,
                session_id=f'professional-{project_id}-repair',
                quality_feedback=quality_report.get('next_actions') or [],
            )
            html = _sanitize(html)
            quality_report = evaluate_landing_page_quality(html, brief_data)

        if quality_report.get('status') == 'needs_work':
            raise ProfessionalCompositionError(
                'The draft did not meet Getszy\'s private-review quality baseline after repair.'
            )

        name = (body.name or brief_data.get('brand_name') or _derive_name(body.prompt))[:80]
        history = [
            BuilderHistoryItem(timestamp=_now(), prompt=body.prompt, role='user'),
            BuilderHistoryItem(
                timestamp=_now(),
                prompt='Managed professional private draft created; review required before release.',
                role='assistant',
                snapshot=html,
            ),
        ]
        project = BuilderProject(
            id=project_id,
            user_id=user['id'],
            name=name,
            prompt=body.prompt,
            template_id=None,
            brief=body.brief,
            quality_report=quality_report,
            html_content=html,
            history=history,
        )
        await db.builder_projects.insert_one(project.model_dump())
        return project.model_dump()
    except ProfessionalCompositionError as exc:
        if charged:
            await refund(user['id'], 'builder_website', reason='professional_composition_quality_failed', ref_id=project_id)
        raise HTTPException(
            422,
            'Getszy could not create a reviewable professional private draft for this request. No credit has been consumed. Add more verified brief details or try again.',
        ) from exc
    except Exception as exc:
        logger.exception('Professional builder composition failed for project %s', project_id)
        if charged:
            await refund(user['id'], 'builder_website', reason='professional_composition_failed', ref_id=project_id)
        raise HTTPException(
            503,
            'Getszy\'s professional composition service is temporarily unavailable. No credit has been consumed; please retry shortly.',
        ) from exc


@router.get('/projects')
async def list_projects(user=Depends(get_current_user)):
    items = await db.builder_projects.find({'user_id': user['id']}, {'_id': 0, 'html_content': 0, 'history': 0}).sort('updated_at', -1).to_list(100)
    return items


@router.get('/projects/{pid}/quality')
async def get_project_quality(pid: str, user=Depends(get_current_user)):
    project = await db.builder_projects.find_one(
        {'id': pid, 'user_id': user['id']},
        {'_id': 0, 'quality_report': 1, 'brief': 1, 'updated_at': 1},
    )
    if not project:
        raise HTTPException(404, 'Project not found')
    return {
        'quality_report': project.get('quality_report') or evaluate_landing_page_quality('', project.get('brief') or {}),
        'brief': project.get('brief') or {},
        'updated_at': project.get('updated_at'),
    }


@router.get('/projects/{pid}/controls')
async def get_project_controls(pid: str, user=Depends(get_current_user)):
    """Return only customer-owned project controls and transparent review eligibility."""
    project = await db.builder_projects.find_one({'id': pid, 'user_id': user['id']}, {'_id': 0})
    if not project:
        raise HTTPException(404, 'Project not found')
    versions = project.get('control_versions') or []
    control_input = dict(project)
    control_input['version_count'] = len(versions)
    state = mission_control_state(control_input)
    return {
        'project_id': pid,
        'state': state,
        'evidence_items': project.get('evidence_items') or [],
        'versions': [
            {'id': item.get('id'), 'label': item.get('label'), 'created_at': item.get('created_at')}
            for item in versions
        ],
        'release_reviews': project.get('release_reviews') or [],
    }


@router.put('/projects/{pid}/evidence')
async def replace_project_evidence(pid: str, body: BuilderEvidenceUpdateIn, user=Depends(get_current_user)):
    """Store customer-reviewed evidence; it never publishes or validates a legal claim."""
    project = await db.builder_projects.find_one({'id': pid, 'user_id': user['id']}, {'_id': 0, 'brief': 1})
    if not project:
        raise HTTPException(404, 'Project not found')
    items = [item.model_dump() for item in body.items]
    await db.builder_projects.update_one(
        {'id': pid, 'user_id': user['id']},
        {'$set': {'evidence_items': items, 'updated_at': _now()}},
    )
    refreshed = await db.builder_projects.find_one({'id': pid, 'user_id': user['id']}, {'_id': 0})
    control_input = dict(refreshed)
    control_input['version_count'] = len(refreshed.get('control_versions') or [])
    return {'ok': True, 'evidence_items': items, 'state': mission_control_state(control_input)}


@router.post('/projects/{pid}/versions')
async def create_project_version(pid: str, body: BuilderVersionIn, user=Depends(get_current_user)):
    """Create a named customer restore point for builder state. No external deployment is affected."""
    project = await db.builder_projects.find_one({'id': pid, 'user_id': user['id']}, {'_id': 0})
    if not project:
        raise HTTPException(404, 'Project not found')
    versions = project.get('control_versions') or []
    version = {
        'id': str(uuid.uuid4()),
        'label': (body.label or '').strip()[:120] or f'Version {len(versions) + 1}',
        'created_at': _now(),
        'state': {
            'html_content': project.get('html_content') or '',
            'brief': project.get('brief') or {},
            'evidence_items': project.get('evidence_items') or [],
            'quality_report': project.get('quality_report') or {},
            'prompt': project.get('prompt') or '',
        },
    }
    versions.append(version)
    await db.builder_projects.update_one(
        {'id': pid, 'user_id': user['id']},
        {'$set': {'control_versions': versions, 'updated_at': _now()}},
    )
    return {'ok': True, 'version': {'id': version['id'], 'label': version['label'], 'created_at': version['created_at']}}


@router.post('/projects/{pid}/versions/{version_id}/restore')
async def restore_project_version(pid: str, version_id: str, user=Depends(get_current_user)):
    """Restore a customer-owned named builder version. This cannot publish or mutate another project."""
    project = await db.builder_projects.find_one({'id': pid, 'user_id': user['id']}, {'_id': 0})
    if not project:
        raise HTTPException(404, 'Project not found')
    version = next((item for item in (project.get('control_versions') or []) if item.get('id') == version_id), None)
    if not version or not isinstance(version.get('state'), dict):
        raise HTTPException(404, 'Version not found')
    state = version['state']
    html = state.get('html_content') or ''
    quality_report = evaluate_landing_page_quality(html, state.get('brief') or {})
    history = project.get('history') or []
    history.extend([
        {'timestamp': _now(), 'prompt': f'Restored named version: {version.get("label")}', 'role': 'user', 'snapshot': None},
        {'timestamp': _now(), 'prompt': 'Named version restored', 'role': 'assistant', 'snapshot': html},
    ])
    await db.builder_projects.update_one(
        {'id': pid, 'user_id': user['id']},
        {'$set': {
            'html_content': html,
            'brief': state.get('brief') or {},
            'evidence_items': state.get('evidence_items') or [],
            'quality_report': quality_report,
            'prompt': state.get('prompt') or project.get('prompt') or '',
            'history': history,
            'updated_at': _now(),
        }},
    )
    return {'ok': True, 'restored_version_id': version_id, 'quality_report': quality_report}


@router.post('/projects/{pid}/release-review')
async def request_customer_release_review(pid: str, body: BuilderReleaseReviewIn, user=Depends(get_current_user)):
    """Record a request for customer review, never a publication or production deployment."""
    project = await db.builder_projects.find_one({'id': pid, 'user_id': user['id']}, {'_id': 0})
    if not project:
        raise HTTPException(404, 'Project not found')
    control_input = dict(project)
    control_input['version_count'] = len(project.get('control_versions') or [])
    state = mission_control_state(control_input)
    if not body.confirm_evidence_review:
        raise HTTPException(422, 'Customer confirmation of evidence review is required')
    if not state['eligible_for_customer_review']:
        raise HTTPException(409, 'Project is not eligible for customer review; complete the brief, resolve evidence blockers and run the required quality checks.')
    review = {
        'id': str(uuid.uuid4()),
        'requested_at': _now(),
        'status': 'ready_for_customer_review',
        'note': 'This status is not production-ready and does not publish the project.',
    }
    await db.builder_projects.update_one(
        {'id': pid, 'user_id': user['id']},
        {'$push': {'release_reviews': review}, '$set': {'updated_at': _now()}},
    )
    return {'ok': True, 'review': review, 'state': state}


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
        # P1-3: idempotent refund by project id.
        await refund(user['id'], 'builder_refine', reason='generation_failed', ref_id=f'refine:{pid}')
        raise HTTPException(503, 'AI service temporarily unavailable. Please try again shortly.')
    new_history = p.get('history', []) + [
        {'timestamp': _now(), 'prompt': body.prompt, 'role': 'user', 'snapshot': None},
        {'timestamp': _now(), 'prompt': 'Refinement applied', 'role': 'assistant', 'snapshot': new_html},
    ]
    quality_report = evaluate_landing_page_quality(new_html, p.get('brief') or {})
    await db.builder_projects.update_one(
        {'id': pid},
        {'$set': {
            'html_content': new_html, 'history': new_history, 'updated_at': _now(),
            'prompt': body.prompt, 'quality_report': quality_report,
        }},
    )
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
    """Public preview (no auth).

    Served with a strict CSP `sandbox` so any user-injected <script> in the
    generated HTML cannot execute or access the origin — prevents stored XSS via
    the public preview link.
    """
    p = await db.builder_projects.find_one({'id': pid}, {'_id': 0, 'html_content': 1})
    if not p:
        return Response(content='<h1>Not found</h1>', media_type='text/html', status_code=404,
                        headers={'Content-Security-Policy': "sandbox; default-src 'none'; img-src data:; style-src 'unsafe-inline'"})
    return HTMLResponse(
        content=p.get('html_content', '<h1>Empty</h1>'),
        headers={'Content-Security-Policy': "sandbox; default-src 'none'; img-src data:; style-src 'unsafe-inline'"},
    )


# ============================================================
# Multi-Agent Streaming Build
# ============================================================

@router.post('/build/stream')
async def build_stream(body: BuilderProjectIn, user=Depends(get_current_user)):
    """Stream multi-agent pipeline steps via SSE."""
    if not body.prompt.strip():
        raise HTTPException(400, 'Prompt required')
    ok, msg, _ = await deduct(user['id'], 'builder_website')
    if not ok:
        raise HTTPException(402, msg)

    session_id = f'builder-stream-{user["id"]}'

    async def event_generator():
        try:
            async for chunk in _stream_build_steps(body.prompt, session_id):
                yield chunk
        except Exception as e:
            logger.exception('stream build failed')
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    )


@router.post('/projects/{pid}/refine-element')
async def refine_project_element(pid: str, body: dict, user=Depends(get_current_user)):
    """Refine a specific element/section of a project."""
    p = await db.builder_projects.find_one({'id': pid, 'user_id': user['id']}, {'_id': 0})
    if not p:
        raise HTTPException(404, 'Project not found')
    selector = body.get('selector', '')
    instruction = body.get('instruction', '')
    if not selector or not instruction:
        raise HTTPException(400, 'selector and instruction required')

    ok, msg, _ = await deduct(user['id'], 'builder_refine')
    if not ok:
        raise HTTPException(402, msg)

    try:
        new_html = await refine_element(
            p.get('html_content', ''),
            selector,
            instruction,
            session_id=f'builder-{pid}',
        )
    except Exception as e:
        logger.exception('element refine failed')
        # P1-3: idempotent refund per (project, selector) pair.
        await refund(user['id'], 'builder_refine', reason='generation_failed', ref_id=f'refine-elem:{pid}:{selector[:64]}')
        raise HTTPException(503, 'AI service temporarily unavailable. Please try again shortly.')

    new_history = p.get('history', []) + [
        {'timestamp': _now(), 'prompt': f'[{selector}] {instruction}', 'role': 'user', 'snapshot': None},
        {'timestamp': _now(), 'prompt': 'Element refined', 'role': 'assistant', 'snapshot': new_html},
    ]
    quality_report = evaluate_landing_page_quality(new_html, p.get('brief') or {})
    await db.builder_projects.update_one(
        {'id': pid},
        {'$set': {
            'html_content': new_html, 'history': new_history, 'updated_at': _now(),
            'quality_report': quality_report,
        }},
    )
    return await db.builder_projects.find_one({'id': pid}, {'_id': 0})


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
    # P1-1: gate the free LLM call behind a credit deduct.
    channel_id = str(_uuid.uuid4())
    ok, msg, _ = await deduct(user['id'], 'channel_plan')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    # Keep output small so fast CPU-only Ollama (llama3.2:3b) can respond in <60s.
    # Frontend can call /channel/execute later to expand individual videos.
    total = min(5, max(3, body.posts_per_week))
    system = (
        'You are a content strategist for Indian creators. '
        f'Plan exactly {total} short-video ideas. '
        'Reply ONLY with this JSON and nothing else: '
        '{"channel_name":"...","channel_bio":"...","pillars":["P1","P2","P3"],'
        f'"videos":[{{"day":1,"topic":"...","hook":"...","format":"reel"}}]}} '
        f'(exactly {total} items in videos array).'
    )
    user_msg = f'Niche: {body.niche}. Audience: {body.audience}. Style: {body.style}. Language: {body.language}.'
    try:
        raw = await chat_completion(system=system, user=user_msg, temperature=0.5)
    except Exception:
        await refund(user['id'], 'channel_plan', reason='generation_failed', ref_id=channel_id)
        raise HTTPException(503, 'AI service temporarily unavailable. Please try again shortly.')
    s = (raw or '').find('{'); e = (raw or '').rfind('}')
    plan = None
    if s != -1:
        try: plan = _json.loads(raw[s:e+1])
        except Exception: plan = None
    if not plan or not plan.get('videos'):
        plan = {'channel_name': body.niche.title(), 'channel_bio': body.niche,
                'pillars': ['Educate', 'Trends', 'How-to'],
                'videos': [{'day': i+1, 'topic': f'{body.niche} idea {i+1}', 'hook': 'Watch this!', 'format': 'reel'}
                            for i in range(total)]}
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
    # P1-2: charge the user upfront for the whole batch. Each video job is
    # expected to refund its own share with ref_id=job_id on downstream failure.
    ok, msg, _ = await deduct(user['id'], 'faceless_video', qty=len(to_run))
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    job_ids: _List[str] = []
    try:
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
                                             'credit_ref_id': job_id,
                                             'created_at': _now()})
            _asyncio.create_task(_run_video_job(job_id, params))
            job_ids.append(job_id)
    except Exception:
        # If we couldn't queue everything, refund the unqueued portion.
        unqueued = len(to_run) - len(job_ids)
        if unqueued > 0:
            await refund(user['id'], 'faceless_video', qty=unqueued,
                         reason='queue_failed', ref_id=f'channel-execute:{body.channel_id}')
        raise
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
    # P0-2: credit-gate the LLM call. Was previously an unauthenticated cost leak.
    run_id = str(_uuid.uuid4())
    ok, msg, _ = await deduct(user['id'], 'custom_agent_run')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    user_lines = [f'{k}: {str(v)[:1000]}' for k, v in (body.params or {}).items() if v not in (None, '', [])]
    prompt = '\n'.join(user_lines) or 'No parameters provided.'
    try:
        raw = await chat_completion(system=ag['system_prompt'], user=prompt, session_id=f'custom-{aid}', temperature=0.6)
    except Exception:
        await refund(user['id'], 'custom_agent_run', reason='generation_failed', ref_id=run_id)
        raise HTTPException(503, 'AI service temporarily unavailable. Please try again shortly.')
    parsed = None
    s = (raw or '').find('{'); e = (raw or '').rfind('}')
    if s != -1:
        try: parsed = _json.loads(raw[s:e+1])
        except Exception: parsed = None
    rec = {'id': run_id, 'user_id': user['id'], 'agent_id': aid,
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
    starter_id = str(_uuid.uuid4())
    # P0-3: credit-gate the LLM zip generation.
    ok, msg, _ = await deduct(user['id'], 'starter_kit')
    if not ok:
        raise HTTPException(status_code=402, detail=msg)
    try:
        if kind == 'mobileapp':
            data = await gen_mobileapp_zip(body.prompt, name)
        elif kind == 'fullstack':
            data = await gen_fullstack_zip(body.prompt, name)
        else:
            data = await gen_blog_zip(body.prompt, name)
    except Exception as e:
        logger.exception('starter gen failed')
        await refund(user['id'], 'starter_kit', reason='generation_failed', ref_id=starter_id)
        raise HTTPException(503, 'AI service temporarily unavailable. Please try again shortly.')
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
    except Exception:
        logger.warning('Failed to delete starter file %s', path, exc_info=True)
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
