"""AI Video Factory v2 — Multi-agent production pipeline.

Layer above the existing `video/` package (Phase 13 v1).
This module adds the "AI Video Factory" agents from the founder's vision:
- Research Agent (topic → facts, angles, keywords, competitor gaps)
- Prompt Enhancer (raw prompt → optimized topic + angle + hook)
- Script Variants (5 versions: beginner, expert, story, documentary, viral)
- Hook Generator (100+ templates, AI picks/customizes best 5)
- Storyboard (script → hooked scenes with pacing)
- Visual Planner (per-scene visual kind: AI-image, stock, animation, motion-graphic)

Data model:
- video_projects: {id, user_id, title, topic, prompt_raw, prompt_enhanced,
                   research, script_variants, selected_script, hooks, storyboard,
                   visual_plan, status, created_at, updated_at}
"""
import asyncio
import json as _json
import os
import re as _re
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from llm_provider import chat_completion


# Output-token caps per stage. Bounding generation length is the single
# biggest CPU-Ollama speed win (fewer tokens generated = less compute) and is
# harmless on fast GPU providers. Override via env if a stage needs more room.
_ENHANCE_MAX     = int(os.environ.get('FACTORY_ENHANCE_MAX_TOKENS', '600'))
_RESEARCH_MAX    = int(os.environ.get('FACTORY_RESEARCH_MAX_TOKENS', '900'))
_SCRIPT_MAX     = int(os.environ.get('FACTORY_SCRIPT_MAX_TOKENS', '1800'))
_HOOKS_MAX       = int(os.environ.get('FACTORY_HOOKS_MAX_TOKENS', '800'))
_STORYBOARD_MAX  = int(os.environ.get('FACTORY_STORYBOARD_MAX_TOKENS', '1500'))
_VISUALS_MAX     = int(os.environ.get('FACTORY_VISUALS_MAX_TOKENS', '1200'))
# How many script variants to generate concurrently. Keep LOW: Groq's free tier
# is rate-limited (~30 req/min), so firing all 5 at once bursts past the limit,
# 429s, and falls back to slow CPU Ollama. Serializing (1-2) stays on Groq and
# finishes the whole chain in ~20s. Raise only on a paid/high-RPM plan.
_SCRIPT_CONCURRENCY = int(os.environ.get('FACTORY_SCRIPT_CONCURRENCY', '2'))


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_json_response(raw: str) -> Any:
    """Extract JSON from LLM output (strip fences, find first { or [ block)."""
    raw = (raw or '').strip()
    raw = _re.sub(r'^```(?:json)?\s*', '', raw)
    raw = _re.sub(r'\s*```\s*$', '', raw)
    m = _re.search(r'[\[{].*[\]}]', raw, _re.DOTALL)
    if m:
        raw = m.group(0)
    return _json.loads(raw)


# ============================================================
# Agent 1: Prompt Enhancer
# ============================================================
async def enhance_prompt(raw_prompt: str, session_id: str) -> Dict[str, Any]:
    """User's raw prompt → optimized topic, angle, hook direction."""
    system = (
        "You are a viral YouTube strategist. Take the user's rough video idea and enhance it into "
        "a production-ready brief. Return STRICT JSON only, no markdown fences."
    )
    prompt = (
        f"User idea: \"{raw_prompt}\"\n\n"
        "Return JSON:\n"
        "{\n"
        '  "enhanced_topic": "sharpened, specific topic (max 80 chars)",\n'
        '  "angle": "unique angle or POV that makes this stand out",\n'
        '  "target_audience": "who this is for (specific)",\n'
        '  "hook_direction": "type of hook that will work best (curiosity/shock/statistic/question/myth)",\n'
        '  "estimated_duration_seconds": integer between 60 and 900,\n'
        '  "improvements": ["3-5 specific ways this idea was improved"]\n'
        "}"
    )
    raw = await chat_completion(system=system, user=prompt, temperature=0.6, session_id=session_id, max_tokens=_ENHANCE_MAX)
    return _parse_json_response(raw)


# ============================================================
# Agent 2: Research
# ============================================================
async def research_topic(topic: str, angle: str, session_id: str) -> Dict[str, Any]:
    """Topic + angle → structured research report (facts, stats, gaps, keywords)."""
    system = (
        "You are a research analyst for a viral video studio. Produce a compact but factual "
        "research report. Do NOT fabricate specific numbers you're not confident about — "
        "prefer ranges or qualitative claims. Return STRICT JSON only."
    )
    prompt = (
        f"Topic: {topic}\nAngle: {angle}\n\n"
        "Return JSON:\n"
        "{\n"
        '  "key_facts": ["5-8 verified facts most viewers do NOT know"],\n'
        '  "statistics": ["3-5 stats with rough figures if uncertain (say \'approximately\' or \'around\')"],\n'
        '  "faqs": ["4-6 common questions viewers will have"],\n'
        '  "competitor_gaps": ["3-5 angles competitors typically miss"],\n'
        '  "trending_keywords": ["8-12 SEO/hashtag keywords"],\n'
        '  "credible_sources_types": ["types of sources to cite (e.g. \'peer-reviewed journals\', \'gov.in reports\', \'company annual reports\')"]\n'
        "}"
    )
    raw = await chat_completion(system=system, user=prompt, temperature=0.4, session_id=session_id, max_tokens=_RESEARCH_MAX)
    return _parse_json_response(raw)


# ============================================================
# Agent 3: Script Variants
# ============================================================
SCRIPT_STYLES = [
    ('viral',       'high-energy Gen-Z tone, punchy sentences, hooks every 15s, meme-friendly'),
    ('educational', 'clear teaching structure, define-explain-example-summary, calm authoritative tone'),
    ('story',       'narrative arc with characters, tension, resolution — like a mini-documentary story'),
    ('documentary', 'balanced journalistic tone, facts + quotes + context, longer scenes'),
    ('beginner',    'simple vocabulary, short sentences, lots of analogies, assumes no prior knowledge'),
]


async def generate_script_variants(topic: str, angle: str, duration_s: int, research: Dict[str, Any], language: str, session_id: str, count: int = 5) -> List[Dict[str, Any]]:
    """Generate `count` script variants in different styles, concurrently for speed."""
    facts_str = ' | '.join((research.get('key_facts') or [])[:5])
    system = (
        "You are a professional YouTube script writer. Write ONE script in the exact style specified. "
        "Return STRICT JSON only. The narration must be spoken by a single voiceover artist (no scene tags in narration)."
    )

    async def _gen_one(style_id: str, style_desc: str) -> Dict[str, Any]:
        prompt = (
            f"Style: {style_id} — {style_desc}\n"
            f"Language: {language}\n"
            f"Topic: {topic}\n"
            f"Angle: {angle}\n"
            f"Target duration: {duration_s} seconds ({duration_s // 60} minutes)\n"
            f"Key facts to weave in: {facts_str}\n\n"
            "Return JSON:\n"
            "{\n"
            f'  "style": "{style_id}",\n'
            '  "hook": "opening 3-5 second hook that stops the scroll",\n'
            '  "narration": "full spoken script, no scene labels inside",\n'
            '  "cta": "final call-to-action line",\n'
            '  "estimated_word_count": integer,\n'
            '  "key_moments": ["4-6 bullet points describing the story arc"]\n'
            "}"
        )
        raw = await chat_completion(system=system, user=prompt, temperature=0.75, session_id=session_id, max_tokens=_SCRIPT_MAX)
        parsed = _parse_json_response(raw)
        parsed['id'] = str(uuid.uuid4())
        parsed['style_id'] = style_id
        return parsed

    # CPU-bound Ollama serializes inference, so limit concurrency; GPU/Groq
    # scales to all at once. Failures drop a single variant instead of
    # aborting the whole stage.
    styles = SCRIPT_STYLES[:max(1, min(count, len(SCRIPT_STYLES)))]
    sem = asyncio.Semaphore(_SCRIPT_CONCURRENCY)
    async def _guarded(item):
        async with sem:
            return await _gen_one(item[0], item[1])
    results = await asyncio.gather(*[_guarded(it) for it in styles], return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]


# ============================================================
# Agent 4: Hook Generator
# ============================================================
HOOK_TEMPLATES = {
    'curiosity': [
        "What if I told you {claim}?",
        "The one thing nobody talks about {topic}",
        "This changes everything you knew about {topic}",
        "You've been {activity} wrong your whole life",
    ],
    'shock': [
        "{number}% of people don't know this",
        "This will destroy your assumptions about {topic}",
        "The dark truth behind {topic}",
    ],
    'statistic': [
        "By {year}, {stat} will happen",
        "{number} out of every {denominator} {group} do this",
    ],
    'question': [
        "Why does {phenomenon} really happen?",
        "Can {subject} actually {verb}?",
    ],
    'myth_vs_fact': [
        "You've been told {myth}. Here's the truth.",
        "Everyone thinks {common_belief}. Actually...",
    ],
    'before_after': [
        "From {bad_state} to {good_state} — here's how",
        "{time_period} ago this was {old}. Now it's {new}.",
    ],
}


async def generate_hooks(topic: str, angle: str, style: str, session_id: str) -> List[Dict[str, Any]]:
    """AI generates 8-10 hook options across styles, ranked by expected performance."""
    system = (
        "You are a viral hook writer. Generate diverse hooks in different psychological styles. "
        "Return STRICT JSON array only."
    )
    prompt = (
        f"Topic: {topic}\nAngle: {angle}\nContent style: {style}\n\n"
        "Generate 8 hooks (3-8 words each) across these types: curiosity, shock, statistic, question, "
        "myth-vs-fact, before-after, story, contrarian. Return JSON:\n"
        "[\n"
        "  { \"text\": \"...\", \"type\": \"curiosity\", \"expected_score\": integer 0-100, \"why\": \"one-line reasoning\" },\n"
        "  ...\n"
        "]\n"
        "Score based on: scroll-stop power, specificity, emotional trigger."
    )
    raw = await chat_completion(system=system, user=prompt, temperature=0.85, session_id=session_id, max_tokens=_HOOKS_MAX)
    hooks = _parse_json_response(raw)
    if isinstance(hooks, dict) and 'hooks' in hooks:
        hooks = hooks['hooks']
    return sorted(hooks, key=lambda h: h.get('expected_score', 0), reverse=True)


# ============================================================
# Agent 5: Storyboard (Script → Scenes)
# ============================================================
async def build_storyboard(script_narration: str, duration_s: int, session_id: str) -> List[Dict[str, Any]]:
    """Divide narration into paced scenes (hook, problem, explanation, example, cta pattern)."""
    system = (
        "You are a video editor. Divide the narration into 5-10 scenes with pacing. "
        "Return STRICT JSON array only."
    )
    prompt = (
        f"Narration:\n{script_narration[:3500]}\n\n"
        f"Target total duration: {duration_s} seconds\n\n"
        "Return JSON:\n"
        "[\n"
        "  {\n"
        '    "index": 1,\n'
        '    "role": "hook|problem|context|example|climax|cta|transition",\n'
        '    "narration_chunk": "exact text from the narration for this scene",\n'
        '    "duration_s": integer,\n'
        '    "pacing_note": "fast | medium | slow — with reasoning",\n'
        '    "visual_intent": "what should be visible during this scene",\n'
        '    "motion": "ken-burns-in | ken-burns-out | pan-left | pan-right | tilt-up | tilt-down"\n'
        "  }\n"
        "]\n"
        "Rules: scene 1 must be 'hook' with duration 3-7s. Last scene must be 'cta'. "
        "Middle scenes 5-15s each. Sum of duration_s should approximately equal total. "
        "Assign a varied 'motion' per scene (do NOT use 'static') to create cinematic "
        "camera movement — e.g. hook = ken-burns-in, a reveal = pan-right, a climax = tilt-up."
    )
    raw = await chat_completion(system=system, user=prompt, temperature=0.5, session_id=session_id, max_tokens=_STORYBOARD_MAX)
    scenes = _parse_json_response(raw)
    if isinstance(scenes, dict) and 'scenes' in scenes:
        scenes = scenes['scenes']
    # ensure ids
    for i, s in enumerate(scenes):
        s['id'] = str(uuid.uuid4())
        s['index'] = i + 1
        s['locked'] = False
    return scenes


# ============================================================
# Agent 6: Visual Planner (per-scene visual strategy)
# ============================================================
VISUAL_KINDS = ['ai_image', 'ai_video', 'stock_footage', 'animation', 'motion_graphic',
                'screen_recording', 'chart', 'map', 'icon', 'text_slate']


async def plan_visuals(scenes: List[Dict[str, Any]], style: str, session_id: str) -> List[Dict[str, Any]]:
    """For each scene decide the best visual kind + generation prompt."""
    scenes_lite = [{'index': s['index'], 'role': s.get('role'), 'visual_intent': s.get('visual_intent')} for s in scenes]
    system = (
        "You are a visual director. For each scene, decide the best visual kind and write "
        "a specific generation prompt. Return STRICT JSON array only."
    )
    prompt = (
        f"Content style: {style}\n"
        f"Scenes:\n{_json.dumps(scenes_lite, ensure_ascii=False)}\n\n"
        f"Available visual kinds: {', '.join(VISUAL_KINDS)}\n\n"
        "Return JSON array matching scenes 1:1:\n"
        "[\n"
        "  {\n"
        '    "scene_index": 1,\n'
        '    "kind": "ai_image",\n'
        '    "generation_prompt": "specific detailed prompt (or search query for stock)",\n'
        '    "style_ref": "cinematic|minimal|documentary|anime|whiteboard|infographic|3d|corporate",\n'
        '    "aspect_ratio": "16:9|9:16|1:1|4:5",\n'
        '    "notes": "optional camera direction / motion notes"\n'
        "  }\n"
        "]"
    )
    raw = await chat_completion(system=system, user=prompt, temperature=0.6, session_id=session_id, max_tokens=_VISUALS_MAX)
    plan = _parse_json_response(raw)
    if isinstance(plan, dict) and 'plan' in plan:
        plan = plan['plan']
    return plan


# ============================================================
# Full orchestrator: run the whole factory chain
# ============================================================
async def run_factory_chain(raw_prompt: str, language: str, session_id: str,
                            fast: bool = False, brief: dict = None) -> Dict[str, Any]:
    """End-to-end: prompt → enhanced → research → scripts → hooks → storyboard → visual plan.

    `fast=True` is the ≤60s path: skips the research round-trip, generates a
    single script, and targets a ~60s video. `brief` (from Prompt Architect)
    supplies a pre-structured prompt so the chain produces best-in-class output
    on the first try instead of re-deriving intent from raw text.
    """
    result = {'stages': {}, 'errors': {}}

    async def _stage(key, coro):
        try:
            val = await coro
            result['stages'][key] = val
            return val
        except Exception as e:
            result['errors'][key] = str(e)[:200]
            return None

    # Use a pre-structured brief when available (no wasted enhance call + better output)
    if brief and brief.get('structured_prompt'):
        work_prompt = brief['structured_prompt']
        enhanced = {
            'enhanced_topic': (brief.get('name') or brief.get('category') or raw_prompt)[:300],
            'angle': (brief.get('goal') or brief.get('tone') or '')[:200],
            'estimated_duration_seconds': 60 if fast else 180,
        }
        result['stages']['enhanced'] = enhanced
    else:
        try:
            enhanced = await enhance_prompt(raw_prompt, session_id)
            result['stages']['enhanced'] = enhanced
        except Exception as e:
            result['errors']['enhance'] = str(e)[:200]
            return result
        work_prompt = enhanced.get('enhanced_topic', raw_prompt)

    duration = 60 if fast else enhanced.get('estimated_duration_seconds', 300)

    # In fast mode skip research (one fewer LLM round-trip); always compute hooks.
    if fast:
        await _stage('hooks', generate_hooks(enhanced['enhanced_topic'], enhanced['angle'], 'viral', session_id))
        research: Dict[str, Any] = {}
    else:
        research, hooks = await asyncio.gather(
            _stage('research', research_topic(enhanced['enhanced_topic'], enhanced['angle'], session_id)),
            _stage('hooks', generate_hooks(enhanced['enhanced_topic'], enhanced['angle'], 'viral', session_id)),
        )

    await _stage(
        'script_variants',
        generate_script_variants(
            enhanced['enhanced_topic'], enhanced['angle'],
            duration,
            (research or {}),
            language, session_id,
            count=1 if fast else 5,
        ),
    )

    # Auto-select viral variant for further processing
    variants = result['stages'].get('script_variants', [])
    viral = next((v for v in variants if v.get('style_id') == 'viral'), variants[0] if variants else None)

    if viral:
        await _stage(
            'storyboard',
            build_storyboard(
                viral.get('narration', ''),
                duration,
                session_id,
            ),
        )
        storyboard = result['stages'].get('storyboard', [])
        if storyboard:
            await _stage('visual_plan', plan_visuals(storyboard, 'viral', session_id))

    result['selected_script_id'] = viral.get('id') if viral else None
    return result
