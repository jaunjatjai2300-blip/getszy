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
import json as _json
import re as _re
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from llm_provider import chat_completion


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
    raw = await chat_completion(system=system, user=prompt, temperature=0.6, session_id=session_id)
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
    raw = await chat_completion(system=system, user=prompt, temperature=0.4, session_id=session_id)
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


async def generate_script_variants(topic: str, angle: str, duration_s: int, research: Dict[str, Any], language: str, session_id: str) -> List[Dict[str, Any]]:
    """Generate 5 script variants in different styles."""
    facts_str = ' | '.join((research.get('key_facts') or [])[:5])
    system = (
        "You are a professional YouTube script writer. Write ONE script in the exact style specified. "
        "Return STRICT JSON only. The narration must be spoken by a single voiceover artist (no scene tags in narration)."
    )
    variants = []
    for style_id, style_desc in SCRIPT_STYLES:
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
        try:
            raw = await chat_completion(system=system, user=prompt, temperature=0.75, session_id=session_id)
            parsed = _parse_json_response(raw)
            parsed['id'] = str(uuid.uuid4())
            parsed['style_id'] = style_id
            variants.append(parsed)
        except Exception as e:
            # Skip failing variant, keep others
            continue
    return variants


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
    raw = await chat_completion(system=system, user=prompt, temperature=0.85, session_id=session_id)
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
        '    "visual_intent": "what should be visible during this scene"\n'
        "  }\n"
        "]\n"
        "Rules: scene 1 must be 'hook' with duration 3-7s. Last scene must be 'cta'. "
        "Middle scenes 5-15s each. Sum of duration_s should approximately equal total."
    )
    raw = await chat_completion(system=system, user=prompt, temperature=0.5, session_id=session_id)
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
    raw = await chat_completion(system=system, user=prompt, temperature=0.6, session_id=session_id)
    plan = _parse_json_response(raw)
    if isinstance(plan, dict) and 'plan' in plan:
        plan = plan['plan']
    return plan


# ============================================================
# Full orchestrator: run the whole factory chain
# ============================================================
async def run_factory_chain(raw_prompt: str, language: str, session_id: str) -> Dict[str, Any]:
    """End-to-end: raw prompt → enhanced → research → 5 scripts → hooks (for viral variant) → storyboard → visual plan.

    Returns partial results even if a stage fails.
    """
    result = {'stages': {}, 'errors': {}}

    try:
        enhanced = await enhance_prompt(raw_prompt, session_id)
        result['stages']['enhanced'] = enhanced
    except Exception as e:
        result['errors']['enhance'] = str(e)[:200]
        return result

    try:
        research = await research_topic(enhanced['enhanced_topic'], enhanced['angle'], session_id)
        result['stages']['research'] = research
    except Exception as e:
        result['errors']['research'] = str(e)[:200]

    try:
        variants = await generate_script_variants(
            enhanced['enhanced_topic'], enhanced['angle'],
            enhanced.get('estimated_duration_seconds', 300),
            result['stages'].get('research', {}),
            language, session_id
        )
        result['stages']['script_variants'] = variants
    except Exception as e:
        result['errors']['scripts'] = str(e)[:200]

    # Auto-select viral variant for further processing
    variants = result['stages'].get('script_variants', [])
    viral = next((v for v in variants if v.get('style_id') == 'viral'), variants[0] if variants else None)

    if viral:
        try:
            hooks = await generate_hooks(enhanced['enhanced_topic'], enhanced['angle'], 'viral', session_id)
            result['stages']['hooks'] = hooks
        except Exception as e:
            result['errors']['hooks'] = str(e)[:200]

        try:
            storyboard = await build_storyboard(
                viral.get('narration', ''),
                enhanced.get('estimated_duration_seconds', 300),
                session_id
            )
            result['stages']['storyboard'] = storyboard
        except Exception as e:
            result['errors']['storyboard'] = str(e)[:200]

        storyboard = result['stages'].get('storyboard', [])
        if storyboard:
            try:
                visual_plan = await plan_visuals(storyboard, 'viral', session_id)
                result['stages']['visual_plan'] = visual_plan
            except Exception as e:
                result['errors']['visual_plan'] = str(e)[:200]

    result['selected_script_id'] = viral.get('id') if viral else None
    return result
