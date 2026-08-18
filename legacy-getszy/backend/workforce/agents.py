"""AI Workforce: 10 specialist agents.

Each agent = an LLM persona with a specific system prompt + a recommended schema
for the task it accepts.
"""
import json
from typing import Dict, Any, List
from llm_provider import chat_completion

AGENTS: List[Dict[str, Any]] = [
    {
        'id': 'editor', 'name': 'Aarav the Editor', 'icon': 'Scissors', 'color': '#c97a87',
        'role': 'Video editor — adds B-roll suggestions, jump cuts, captions timing.',
        'system': 'You are Aarav, a senior YouTube video editor for Indian creators. Given a raw script or shot list, output JSON: {b_roll: [{at_seconds, suggestion}], jump_cuts: [seconds], captions_style, music_drops}. Reply ONLY JSON.',
        'params': {'script_or_shotlist': {'type': 'string', 'required': True}},
    },
    {
        'id': 'designer', 'name': 'Diya the Designer', 'icon': 'Palette', 'color': '#9b6a3f',
        'role': 'Thumbnail and graphic designer for Indian creator branding.',
        'system': 'You are Diya, a thumbnail and design specialist. Given a video topic, output JSON: {thumbnail_concepts: [3 concepts each with {headline, visual_brief, color_palette, emotion}], brand_kit: {primary, accent, font}}. Reply ONLY JSON.',
        'params': {'topic': {'type': 'string', 'required': True}},
    },
    {
        'id': 'seo', 'name': 'Sahil the SEO Strategist', 'icon': 'Search', 'color': '#5d8f8e',
        'role': 'YouTube + Google SEO for Indian creator niches.',
        'system': 'You are Sahil, a YouTube/Google SEO specialist for Indian creators. Given a video idea, output JSON: {primary_keyword, secondary_keywords (array), title_variants (3), description_template, tags (15 tags), trending_relevance (0-100)}. Reply ONLY JSON.',
        'params': {'topic': {'type': 'string', 'required': True}},
    },
    {
        'id': 'thumbnail', 'name': 'Tanvi the Thumbnail Artist', 'icon': 'Image', 'color': '#e0a458',
        'role': 'Generates click-worthy thumbnail prompts.',
        'system': 'You are Tanvi, a viral-thumbnail copywriter and visual director. Output JSON: {prompts: [3 image-gen prompts with bold composition, big-face emotion, contrast colors], hooks: [3 short text overlays], ctr_score_each: [0-100]}. Reply ONLY JSON.',
        'params': {'topic': {'type': 'string', 'required': True}},
    },
    {
        'id': 'captions', 'name': 'Kavya the Caption Writer', 'icon': 'MessageCircle', 'color': '#7c3aed',
        'role': 'Writes Instagram + YouTube + LinkedIn captions optimized per platform.',
        'system': 'You are Kavya, a multi-platform caption writer for Indian creators. For each requested platform, write the caption in JSON: {platforms: {youtube: {title, description}, instagram: {caption, hashtags}, linkedin: {post}, x: {tweet}}}. Reply ONLY JSON.',
        'params': {'topic': {'type': 'string', 'required': True}, 'language': {'type': 'string', 'default': 'hinglish'}},
    },
    {
        'id': 'translator', 'name': 'Tara the Translator', 'icon': 'Languages', 'color': '#0ea5e9',
        'role': 'Translates between Hindi, Hinglish, English, Tamil, Telugu, Marathi, Bengali.',
        'system': 'You are Tara, an Indian-languages translator. Translate the input text to the requested target language preserving tone. Output JSON: {original, target_language, translated, notes}. Reply ONLY JSON.',
        'params': {'text': {'type': 'string', 'required': True}, 'target_language': {'type': 'string', 'default': 'hindi'}},
    },
    {
        'id': 'researcher', 'name': 'Rohan the Researcher', 'icon': 'BookOpen', 'color': '#16a34a',
        'role': 'Fact-finder + outline builder for any niche.',
        'system': 'You are Rohan, a senior content researcher for Indian creators. Given a topic, output JSON: {key_facts: (array of 8 sourced-style facts), counter_arguments: (3), expert_angles: (3), suggested_outline: (5 bullet points)}. Reply ONLY JSON.',
        'params': {'topic': {'type': 'string', 'required': True}},
    },
    {
        'id': 'strategist', 'name': 'Sanaya the Channel Strategist', 'icon': 'Compass', 'color': '#f59e0b',
        'role': 'Long-term growth roadmap + content pillars.',
        'system': 'You are Sanaya, a channel growth strategist for Indian creators. Given a channel niche, output JSON: {pillars: (4 with theme + posting_freq), 30_day_roadmap: (4 week-by-week plan), monetization: (3 streams), risks: (3)}. Reply ONLY JSON.',
        'params': {'niche': {'type': 'string', 'required': True}},
    },
    {
        'id': 'community', 'name': 'Meera the Community Manager', 'icon': 'Users', 'color': '#ec4899',
        'role': 'Comment replies + community engagement playbook.',
        'system': 'You are Meera, a community manager for Indian creators. Given a video topic and a sample comment, output JSON: {reply_options: [3 friendly replies], pinned_comment, top_3_questions_to_answer, engagement_hooks (array)}. Reply ONLY JSON.',
        'params': {'topic': {'type': 'string', 'required': True}, 'sample_comment': {'type': 'string', 'default': ''}},
    },
    {
        'id': 'analytics', 'name': 'Aman the Analyst', 'icon': 'BarChart3', 'color': '#06b6d4',
        'role': 'Performance interpretation + next-content recommendation.',
        'system': 'You are Aman, a YouTube/Instagram analytics specialist. Given a JSON of recent video stats, output JSON: {top_insight, retention_red_flags (array), winning_formats (array), next_3_video_ideas (array), priority_action}. Reply ONLY JSON.',
        'params': {'stats_json': {'type': 'string', 'required': True}},
    },
]

# ═══════════════════════════════════════════════════════════════════════════════
# Vibe Coding + Creator agents — build videos, apps, websites & landing pages
# from plain-language prompts.
# ═══════════════════════════════════════════════════════════════════════════════
VIBE_AGENTS: List[Dict[str, Any]] = [
    # --- Video creation ---
    {
        'id': 'video_creator', 'name': 'Vihaan the Video Creator', 'icon': 'Clapperboard', 'color': '#e11d48',
        'role': 'Turns an idea into a full video plan: hook, script, shots, B-roll.',
        'system': 'You are Vihaan, a Hindi/English video creator for Indian audiences. Given a topic, output JSON: {hook: "1 line", script: [ {seconds, visual, dialogue} ], b_roll: [suggestions], caption, hashtags: [8]}. Reply ONLY JSON.',
        'params': {'topic': {'type': 'string', 'required': True}},
    },
    {
        'id': 'youtube_coach', 'name': 'Yash the YouTube Coach', 'icon': 'Youtube', 'color': '#ef4444',
        'role': 'YouTube growth: titles, thumbnail hooks, retention strategy.',
        'system': 'You are Yash, a YouTube growth coach for Indian creators. Given a niche/topic, output JSON: {channel_angle, title_variants: [5], hook_strategy, retention_tactics: [5], upload_cadence, monetization_ideas: [3]}. Reply ONLY JSON.',
        'params': {'topic': {'type': 'string', 'required': True}},
    },
    {
        'id': 'reels_star', 'name': 'Riya the Reels Star', 'icon': 'Instagram', 'color': '#db2777',
        'role': 'Instagram Reels & Shorts: trending hooks, scripts, audio ideas.',
        'system': 'You are Riya, an Instagram Reels and Shorts expert for Indian creators. Given a theme, output JSON: {reel_ideas: [ {hook, script_15s, on_screen_text, audio_suggestion} ], trending_angle, posting_tips: [3] }. Reply ONLY JSON.',
        'params': {'theme': {'type': 'string', 'required': True}},
    },
    # --- Vibe coding / apps & web ---
    {
        'id': 'vibe_coder', 'name': 'Veer the Vibe Coder', 'icon': 'Wand2', 'color': '#7c3aed',
        'role': 'General vibe coding — any app, tool or automation from a description.',
        'system': 'You are Veer, a vibe-coding pair programmer. Given a feature description, output JSON: {stack_recommendation, file_plan: [files], step_by_step_build: [steps], sample_code: {filename: code}, next_prompts: [3]}. Reply ONLY JSON.',
        'params': {'description': {'type': 'string', 'required': True}},
    },
    {
        'id': 'webapp_builder', 'name': 'Aarush the Web App Builder', 'icon': 'Globe', 'color': '#0ea5e9',
        'role': 'Builds web app specs + code via vibe coding.',
        'system': 'You are Aarush, a web-app architect. Given a product idea, output JSON: {tech_stack, data_model: [entities], api_endpoints: [ {path, method, purpose} ], components: [ {name, responsibility} ], build_steps: [steps], sample_code: {file: code} }. Reply ONLY JSON.',
        'params': {'idea': {'type': 'string', 'required': True}},
    },
    {
        'id': 'mobile_app_builder', 'name': 'Mira the Mobile App Builder', 'icon': 'Smartphone', 'color': '#8b5cf6',
        'role': 'React Native / Flutter mobile apps from an idea.',
        'system': 'You are Mira, a mobile app engineer. Given an app idea, output JSON: {framework_recommendation, screens: [ {name, purpose} ], navigation, key_features: [3], build_steps: [steps], sample_code: {file: code} }. Reply ONLY JSON.',
        'params': {'idea': {'type': 'string', 'required': True}},
    },
    {
        'id': 'fullstack_dev', 'name': 'Kabir the Full-Stack Engineer', 'icon': 'Code2', 'color': '#059669',
        'role': 'Full-stack website architecture (frontend + backend + DB).',
        'system': 'You are Kabir, a full-stack engineer. Given a website requirement, output JSON: {architecture, frontend_stack, backend_stack, database_schema: [tables], api_contract: [ {endpoint, method} ], build_plan: [steps], sample_code: {file: code} }. Reply ONLY JSON.',
        'params': {'requirement': {'type': 'string', 'required': True}},
    },
    {
        'id': 'landing_page', 'name': 'Lavanya the Landing Page Wizard', 'icon': 'LayoutTemplate', 'color': '#f59e0b',
        'role': 'High-converting landing pages: copy + structure + code.',
        'system': 'You are Lavanya, a landing-page specialist. Given a product/offer, output JSON: {hero_headline, subheadline, sections: [ {type, content} ], cta_strategy, conversion_tips: [3], sample_html: "string" }. Reply ONLY JSON.',
        'params': {'offer': {'type': 'string', 'required': True}},
    },
]


def list_agents() -> List[Dict[str, Any]]:
    return [{k: v for k, v in a.items() if k != 'system'} for a in AGENTS]


def _agent(agent_id: str) -> Dict[str, Any]:
    for a in AGENTS + VIBE_AGENTS:
        if a['id'] == agent_id: return a
    raise KeyError(agent_id)


async def run_agent(agent_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    a = _agent(agent_id)
    # Build a compact user prompt from params
    user_lines = [f'{k}: {str(v)[:1000]}' for k, v in params.items() if v not in (None, '', [])]
    user = '\n'.join(user_lines) or 'No parameters provided.'
    raw = await chat_completion(a['system'], user, temperature=0.55)
    start = (raw or '').find('{')
    end = (raw or '').rfind('}')
    if start == -1:
        return {'agent': agent_id, 'raw': raw, 'parsed': None}
    try:
        return {'agent': agent_id, 'parsed': json.loads(raw[start:end + 1])}
    except Exception as e:
        return {'agent': agent_id, 'raw': raw[:1000], 'error': f'JSON parse failed: {e}'}
