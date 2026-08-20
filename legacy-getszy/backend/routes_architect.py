"""Prompt Architect API — single natural-language entry point.

Customers type whatever they're thinking; the architect structures it and we
dispatch to the best generator: landing/website -> full HTML site, video ->
fast factory render, copy/social -> professional copy. One call, best-in-class
output, no wasted credits on vague prompts.
"""
import uuid
import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_user
from db import db
from prompt_architect import architect

logger = logging.getLogger('getszy.architect.api')
router = APIRouter(prefix='/architect', tags=['architect'])


class ArchitectIn(BaseModel):
    text: str
    intent: Optional[str] = None
    language: str = 'english'
    fast: bool = True  # video: target a ~60s express render


def _iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


@router.post('/generate')
async def generate(body: ArchitectIn, user=Depends(get_current_user)):
    return await _generate(body, user)


async def _generate(body: ArchitectIn, user):
    brief = await architect(body.text, body.intent)
    intent = brief.get('intent') or detect_intent(body.text)
    brief['intent'] = intent

    # ── Landing page / Website → full HTML site ──
    if intent in ('landing', 'website'):
        from builder_agents import build_site
        html = await build_site(brief['structured_prompt'], session_id=f'arch-{user["id"]}')
        pid = str(uuid.uuid4())
        await db.builder_projects.insert_one({
            'id': pid, 'user_id': user['id'], 'name': brief.get('name') or 'Untitled',
            'prompt': brief['structured_prompt'], 'html_content': html, 'history': [],
            'created_at': _iso(), 'updated_at': _iso(), 'source': 'architect',
        })
        return {
            'intent': intent,
            'brief': brief,
            'project_id': pid,
            'preview_url': f'/api/builder/projects/{pid}/preview',
            'download_url': f'/api/builder/projects/{pid}/download',
            'size_bytes': len(html),
        }

    # ── Video → fast factory render ──
    if intent == 'video':
        from credits import deduct
        from routes_video_factory import _run_chain_bg
        ok, msg, _ = await deduct(user['id'], 'video_factory_chain')
        if not ok:
            raise HTTPException(status_code=402, detail=msg)
        pid = str(uuid.uuid4())
        await db.video_projects.insert_one({
            'id': pid, 'user_id': user['id'],
            'title': brief.get('name') or body.text[:60],
            'prompt_raw': body.text, 'prompt': brief['structured_prompt'],
            'brief': brief, 'language': body.language, 'fast': body.fast,
            'status': 'created', 'stages': {}, 'selected_script_id': None,
            'created_at': _iso(), 'updated_at': _iso(),
        })
        asyncio.create_task(_run_chain_bg(pid, brief['structured_prompt'], body.language, user['id'], body.fast, brief))
        await db.video_projects.update_one({'id': pid}, {'$set': {'status': 'processing'}})
        return {
            'intent': 'video',
            'brief': brief,
            'project_id': pid,
            'status': 'processing',
            'poll_url': f'/api/video-factory/project/{pid}',
        }

    # ── Copy / Social → professional copy text ──
    if intent in ('copy', 'social'):
        from llm_provider import chat_completion
        system = (
            "You are a world-class conversion copywriter. Using the provided brief, "
            "write polished, specific, brand-grade copy. Use clear markdown structure "
            "(headings, bullets). No generic filler. Match the brief's tone, audience, "
            "language and CTA."
        )
        user_msg = (
            f"Brief:\n{brief.get('structured_prompt')}\n\n"
            f"Deliver {('a social media post' if intent=='social' else 'complete marketing copy')} "
            f"with hook, body and CTA."
        )
        try:
            content = await chat_completion(system=system, user=user_msg, temperature=0.6, max_tokens=2000)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f'generation failed: {e}')
        return {'intent': intent, 'brief': brief, 'content': content.strip()}

    # ── Logo / Image → structured brief + guidance ──
    return {
        'intent': intent,
        'brief': brief,
        'note': (
            'Use the dedicated Logo or Image tool with this structured brief for best results.'
            if intent == 'logo' else
            'Use the Image tool, or call /media/image with this brief.'
        ),
        'suggested_prompt': brief.get('visual_style') or brief['structured_prompt'],
    }
