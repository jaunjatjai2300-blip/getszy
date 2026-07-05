"""Registry of chat-invocable capabilities.

Each capability WRAPS an existing backend module — we do not duplicate business
logic. This registry is the single source of truth for what the Chat Builder
can do.

Adding a capability:
  CAPABILITIES['my_thing'] = {
      'desc': 'What it does',
      'params': {'topic': 'string (required)'},
      'run': my_async_function,
      'result_kind': 'asset_kind_for_ui',
  }
"""
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Callable, Awaitable

from db import db


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------- Capability implementations -------------------------
# Each returns a dict that is stored as an "asset" against the project.

async def _cap_write_script(user: Dict[str, Any], params: Dict[str, Any], emit) -> Dict[str, Any]:
    from creator.scripts import generate
    fmt = params.get('format', 'youtube_short')
    topic = (params.get('topic') or '').strip() or 'trending topic'
    await emit('progress', {'msg': f'Writing {fmt} script on "{topic}"…', 'percent': 20})
    out = await generate(
        topic=topic,
        fmt=fmt,
        audience=params.get('audience', 'indian creators'),
        tone=params.get('tone', 'energetic'),
        language=params.get('language', 'hinglish'),
    )
    await emit('progress', {'msg': 'Script ready ✅', 'percent': 100})
    return {'kind': 'script', 'title': out.get('title', topic), 'data': out}


async def _cap_score_hook(user, params, emit) -> Dict[str, Any]:
    from creator.scripts import score_hook
    await emit('progress', {'msg': 'Scoring hook…', 'percent': 40})
    r = await score_hook((params.get('hook') or '').strip())
    return {'kind': 'hook_score', 'title': f"Hook score: {r.get('score', '?')}/100", 'data': r}


async def _cap_viral_score(user, params, emit) -> Dict[str, Any]:
    from creator.scripts import viral_score
    content = params.get('content') or {'title': params.get('title', ''), 'hook': params.get('hook', ''), 'format': params.get('format', 'reel')}
    await emit('progress', {'msg': 'Predicting viral score…', 'percent': 40})
    r = await viral_score(content)
    return {'kind': 'viral_score', 'title': f"Viral score: {r.get('viral_score', '?')}/100", 'data': r}


async def _cap_predict_trends(user, params, emit) -> Dict[str, Any]:
    from creator.trends import predict
    niche = (params.get('niche') or '').strip()
    await emit('progress', {'msg': f'Forecasting trends for "{niche or "general"}"…', 'percent': 30})
    r = await predict(niche=niche, count=int(params.get('count', 8)))
    return {'kind': 'trends', 'title': f'{len(r.get("predictions", []))} trends for {niche or "general"}', 'data': r}


async def _cap_competitor_gap(user, params, emit) -> Dict[str, Any]:
    from creator.trends import competitor_gap
    hint = (params.get('competitor') or '').strip()
    await emit('progress', {'msg': 'Analyzing competitor gaps…', 'percent': 40})
    r = await competitor_gap(hint)
    return {'kind': 'competitor_gap', 'title': f'Gap analysis: {hint[:40]}', 'data': r}


async def _cap_generate_video(user, params, emit) -> Dict[str, Any]:
    """Queue a faceless video job. Returns immediately with job id; poll for updates."""
    from video.pipeline import run_job
    import asyncio
    topic = (params.get('topic') or '').strip()
    if len(topic) < 4:
        return {'kind': 'error', 'title': 'Video needs a topic', 'data': {'error': 'topic too short'}}
    job_id = str(uuid.uuid4())
    orient = params.get('orientation', '9:16')
    lang = params.get('language', 'hinglish')
    job_params = {
        'topic': topic, 'orientation': orient, 'language': lang,
        'voice_gender': params.get('voice_gender', 'female'),
        'target_seconds': int(params.get('target_seconds', 25)),
        'tone': params.get('tone', 'energetic'),
        'subtitles': False,
        'audience': params.get('audience', 'indian creators'),
    }
    await db.video_jobs.insert_one({
        'id': job_id, 'user_id': user['id'], 'topic': topic,
        'orientation': orient, 'language': lang,
        'status': 'queued', 'percent': 0, 'params': job_params,
        'created_at': _iso(),
    })
    asyncio.create_task(run_job(job_id, job_params))
    await emit('progress', {'msg': f'Video job queued (id {job_id[:8]}) — tracking in Video Studio', 'percent': 10})
    return {'kind': 'video_job', 'title': f'Faceless video: {topic}',
            'data': {'job_id': job_id, 'status_endpoint': f'/api/video/jobs/{job_id}',
                     'video_url_when_done': f'/api/video/files/{job_id}.mp4'}}


async def _cap_plan_channel(user, params, emit) -> Dict[str, Any]:
    """Plan a 30-day faceless channel using existing builder route logic."""
    from llm_provider import chat_completion
    import json
    niche = (params.get('niche') or '').strip() or 'ai tools for indian creators'
    posts_per_week = int(params.get('posts_per_week', 5))
    total = max(4, min(30, posts_per_week * 4))
    await emit('progress', {'msg': f'Planning {total} videos for "{niche}"…', 'percent': 25})
    system = (
        f'You are a YouTube/Reels content strategist for Indian creators. Given a niche, plan '
        f'{total} videos for the next 30 days. Reply ONLY JSON: '
        '{channel_name, channel_bio, pillars: [4 with theme], videos: [{day, topic, hook, format, pillar}]}.'
    )
    user_msg = f'Niche: {niche}\nAudience: {params.get("audience", "indian creators")}\nStyle: {params.get("style", "energetic")}\nLanguage: {params.get("language", "hinglish")}'
    raw = await chat_completion(system=system, user=user_msg, temperature=0.6)
    s = (raw or '').find('{'); e = (raw or '').rfind('}')
    plan = None
    if s != -1:
        try: plan = json.loads(raw[s:e + 1])
        except Exception: plan = None
    if not plan or not plan.get('videos'):
        plan = {'channel_name': niche.title(), 'channel_bio': niche,
                'pillars': [{'theme': 'Educate'}, {'theme': 'Trends'}, {'theme': 'Stories'}, {'theme': 'How-to'}],
                'videos': [{'day': i + 1, 'topic': f'{niche} idea {i + 1}', 'hook': '', 'format': 'reel', 'pillar': 'Educate'} for i in range(total)]}
    channel_id = str(uuid.uuid4())
    doc = {'id': channel_id, 'user_id': user['id'], 'niche': niche, 'audience': params.get('audience', 'indian creators'),
           'style': params.get('style', 'energetic'), 'language': params.get('language', 'hinglish'),
           'orientation': params.get('orientation', '9:16'), 'plan': plan, 'status': 'planned',
           'executed_video_ids': [], 'created_at': _iso()}
    await db.channel_plans.insert_one(doc)
    await emit('progress', {'msg': f'Channel "{plan.get("channel_name", niche)}" planned ✅', 'percent': 100})
    return {'kind': 'channel_plan', 'title': plan.get('channel_name', niche),
            'data': {'channel_id': channel_id, 'plan': plan}}


async def _cap_build_webapp(user, params, emit) -> Dict[str, Any]:
    """Uses existing routes_builder web app generator by calling its underlying LLM prompt directly."""
    from llm_provider import chat_completion
    prompt = (params.get('prompt') or params.get('description') or '').strip()
    if len(prompt) < 4:
        return {'kind': 'error', 'title': 'Web app needs a description', 'data': {'error': 'prompt too short'}}
    name = params.get('name') or _derive_name(prompt)
    await emit('progress', {'msg': f'Generating web app "{name}"…', 'percent': 40})
    system = (
        'You are a senior front-end engineer. Given a prompt, output ONE complete, self-contained '
        'HTML file (with inline CSS + inline JS) that is production-quality, mobile-responsive, and '
        'accessible. Modern design, tasteful gradients allowed, use Google Fonts via <link>. '
        'No external JS frameworks. Reply ONLY the raw HTML (no code fences, no markdown).'
    )
    raw = await chat_completion(system=system, user=prompt, temperature=0.6)
    html = _extract_html(raw) or f'<!doctype html><html><body style="font-family:sans-serif;padding:40px"><h1>{name}</h1><p>{prompt}</p></body></html>'
    project_id = str(uuid.uuid4())
    await db.builder_projects.insert_one({
        'id': project_id, 'user_id': user['id'], 'name': name,
        'prompt': prompt, 'html_content': html, 'history': [],
        'created_at': _iso(), 'updated_at': _iso(),
    })
    await emit('progress', {'msg': f'Web app ready ({len(html) // 1024}KB) ✅', 'percent': 100})
    return {'kind': 'webapp', 'title': name,
            'data': {'project_id': project_id, 'preview_url': f'/api/builder/projects/{project_id}/preview',
                     'download_url': f'/api/builder/projects/{project_id}/download', 'size_bytes': len(html)}}


async def _cap_starter(kind_key: str, user, params, emit) -> Dict[str, Any]:
    """Generate mobileapp/fullstack/blog starter zip via existing builder_starters module."""
    from builder_starters import gen_mobileapp_zip, gen_fullstack_zip, gen_blog_zip
    prompt = (params.get('prompt') or '').strip()
    if len(prompt) < 4:
        return {'kind': 'error', 'title': f'{kind_key} needs a description', 'data': {'error': 'prompt too short'}}
    name = params.get('name') or _derive_name(prompt)
    await emit('progress', {'msg': f'Generating {kind_key} starter…', 'percent': 50})
    gen = {'mobileapp': gen_mobileapp_zip, 'fullstack': gen_fullstack_zip, 'blog': gen_blog_zip}[kind_key]
    data = await gen(prompt, name)
    starter_id = str(uuid.uuid4())
    starters_dir = os.path.join(os.path.dirname(__file__), '..', 'media_cache', 'starters')
    os.makedirs(starters_dir, exist_ok=True)
    with open(os.path.join(starters_dir, f'{starter_id}.zip'), 'wb') as f:
        f.write(data)
    await db.builder_starters.insert_one({
        'id': starter_id, 'user_id': user['id'], 'kind': kind_key, 'name': name,
        'prompt': prompt, 'size_bytes': len(data), 'created_at': _iso(),
    })
    await emit('progress', {'msg': f'{kind_key.title()} starter ready ({len(data) // 1024}KB) ✅', 'percent': 100})
    return {'kind': f'starter_{kind_key}', 'title': name,
            'data': {'starter_id': starter_id, 'download_url': f'/api/builder/starter/{starter_id}/download',
                     'size_bytes': len(data)}}


async def _cap_starter_mobile(user, params, emit): return await _cap_starter('mobileapp', user, params, emit)
async def _cap_starter_fullstack(user, params, emit): return await _cap_starter('fullstack', user, params, emit)
async def _cap_starter_blog(user, params, emit): return await _cap_starter('blog', user, params, emit)


async def _cap_run_workforce(user, params, emit) -> Dict[str, Any]:
    from workforce.agents import run_agent, AGENTS
    agent_id = (params.get('agent_id') or '').strip()
    if agent_id not in {a['id'] for a in AGENTS}:
        return {'kind': 'error', 'title': 'Unknown workforce agent', 'data': {'valid_ids': [a['id'] for a in AGENTS]}}
    await emit('progress', {'msg': f'Delegating to {agent_id}…', 'percent': 40})
    out = await run_agent(agent_id, params.get('agent_params') or params)
    return {'kind': 'workforce_run', 'title': f'{agent_id} output', 'data': out}


async def _cap_sourcing(user, params, emit) -> Dict[str, Any]:
    """Trending product sourcing via existing scan."""
    from sourcing.aggregator import scan as _scan
    niche = (params.get('niche') or '').strip() or 'trending'
    await emit('progress', {'msg': f'Scanning trending suppliers for "{niche}"…', 'percent': 30})
    try:
        r = await _scan(niche=niche, limit=int(params.get('limit', 12)))
    except Exception as e:
        return {'kind': 'error', 'title': 'Sourcing failed', 'data': {'error': str(e)[:200]}}
    return {'kind': 'sourcing_scan', 'title': f'{len(r.get("items", []))} trending items', 'data': r}


# ---- Simple utilities ----

def _derive_name(prompt: str) -> str:
    words = [w for w in prompt.split() if w.isalnum()][:4]
    return ' '.join(words).title() or 'Untitled'


def _extract_html(raw: str) -> str:
    if not raw:
        return ''
    t = raw.strip()
    if t.startswith('```'):
        # strip code fences
        t = t.split('\n', 1)[-1]
        if t.rstrip().endswith('```'):
            t = t.rstrip()[:-3]
    return t.strip()


# ------------------------- Registry -------------------------
# min_role: visitor < customer < founder < admin
# UI + intent classifier will only surface capabilities matching the caller's role.
CAPABILITIES: Dict[str, Dict[str, Any]] = {
    'write_script': {
        'desc': 'Write a script for a video/reel/blog/thread in Hinglish/Hindi/English',
        'params': {'topic': 'string (required)', 'format': 'youtube_short|youtube_long|instagram_reel|blog|tweet_thread|linkedin', 'tone': 'string', 'language': 'hinglish|hindi|english'},
        'run': _cap_write_script, 'result_kind': 'script',
    },
    'score_hook': {
        'desc': 'Score and improve the first-3-seconds hook of a video/post',
        'params': {'hook': 'string (required)'},
        'run': _cap_score_hook, 'result_kind': 'hook_score',
    },
    'viral_score': {
        'desc': 'Predict viral probability of a title+hook before publishing',
        'params': {'title': 'string (required)', 'hook': 'string', 'format': 'reel|long|post'},
        'run': _cap_viral_score, 'result_kind': 'viral_score',
    },
    'predict_trends': {
        'desc': 'Forecast trending content topics for a niche (next 14 days)',
        'params': {'niche': 'string', 'count': 'int (default 8)'},
        'run': _cap_predict_trends, 'result_kind': 'trends',
    },
    'competitor_gap': {
        'desc': 'Find content gaps in a competitor channel',
        'params': {'competitor': 'string (required, e.g. channel name/URL)'},
        'run': _cap_competitor_gap, 'result_kind': 'competitor_gap',
    },
    'generate_video': {
        'desc': 'Generate a faceless video end-to-end (script + AI visuals + Indian TTS + auto-edit)',
        'params': {'topic': 'string (required)', 'orientation': '9:16|16:9|1:1', 'language': 'hinglish|hindi|english', 'target_seconds': 'int'},
        'run': _cap_generate_video, 'result_kind': 'video_job',
    },
    'plan_channel': {
        'desc': 'Plan a 30-day faceless video channel (calendar + pillars + hooks)',
        'params': {'niche': 'string (required)', 'posts_per_week': 'int', 'language': 'hinglish|hindi|english'},
        'run': _cap_plan_channel, 'result_kind': 'channel_plan',
    },
    'build_webapp': {
        'desc': 'Build a single-page web app / landing page from a prompt (with live iframe preview)',
        'params': {'prompt': 'string (required, describe the page)', 'name': 'string'},
        'run': _cap_build_webapp, 'result_kind': 'webapp',
    },
    'starter_mobileapp': {
        'desc': 'Generate a downloadable Expo/React Native mobile app starter zip',
        'params': {'prompt': 'string (required)', 'name': 'string'},
        'run': _cap_starter_mobile, 'result_kind': 'starter_mobileapp',
    },
    'starter_fullstack': {
        'desc': 'Generate a FastAPI + React + Mongo full-stack starter zip',
        'params': {'prompt': 'string (required)', 'name': 'string'},
        'run': _cap_starter_fullstack, 'result_kind': 'starter_fullstack',
    },
    'starter_blog': {
        'desc': 'Generate a static multi-post blog zip for a niche',
        'params': {'prompt': 'string (required)', 'name': 'string'},
        'run': _cap_starter_blog, 'result_kind': 'starter_blog',
    },
    'run_workforce': {
        'desc': 'Delegate a task to one of the 10 preset AI workforce agents (editor, designer, seo, thumbnail, captions, translator, researcher, strategist, community, analytics)',
        'params': {'agent_id': 'editor|designer|seo|thumbnail|captions|translator|researcher|strategist|community|analytics', 'agent_params': 'dict'},
        'run': _cap_run_workforce, 'result_kind': 'workforce_run',
    },
    'sourcing_scan': {
        'desc': 'Scan for trending dropshipping products in a niche via CJ + Getszy Source',
        'params': {'niche': 'string', 'limit': 'int (default 12)'},
        'run': _cap_sourcing, 'result_kind': 'sourcing_scan',
    },
}




# -------- Extended registry (founder + admin) --------
from chat_builder.capabilities_ext import EXTENDED_CAPABILITIES
CAPABILITIES.update(EXTENDED_CAPABILITIES)

# Backfill: every entry without min_role defaults to 'customer'
for _cid, _spec in CAPABILITIES.items():
    _spec.setdefault('min_role', 'customer')
