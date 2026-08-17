"""Expert Agents — 7 AI specialists that users can chat with.

Each agent has a unique system prompt, personality, and tool-use capabilities.
Agents use the LLM provider chain (Ollama → Groq → Gemini → OpenRouter).
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_user, get_current_admin
from db import db
from llm_provider import chat_completion
from workforce.agents import AGENTS as WORKFORCE_AGENTS

router = APIRouter(tags=['agents'])


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Definitions
# ═══════════════════════════════════════════════════════════════════════════════

AGENTS = {
    'business-advisor': {
        'id': 'business-advisor',
        'name': 'Business Advisor',
        'tagline': 'Strategy, pricing, growth & market fit',
        'description': 'Expert in Indian D2C businesses, pricing strategy, market validation, unit economics, and growth playbooks. Gives blunt, actionable advice.',
        'avatar': '💼',
        'color': '#7c3aed',
        'system': (
            "You are Getszy's Business Advisor — a sharp, experienced startup mentor focused on Indian D2C and e-commerce businesses. "
            "You give blunt, honest advice on pricing, market fit, unit economics, competition, and growth strategy. "
            "Use Indian context (₹, GST, Indian consumer behavior, WhatsApp/Instagram commerce). "
            "Be concise. Lead with the answer, then explain. If the user's idea has a flaw, say so directly."
        ),
        'tools': ['pricing_calc', 'competitor_lookup', 'market_size'],
    },
    'creative-writer': {
        'id': 'creative-writer',
        'name': 'Creative Writer',
        'tagline': 'Brand voice, copy, scripts & storytelling',
        'description': 'Crafts brand copy, product descriptions, social media captions, video scripts, and email sequences with authentic Indian voice.',
        'avatar': '✍️',
        'color': '#c97a87',
        'system': (
            "You are Getszy's Creative Writer — a skilled copywriter who understands Indian audiences. "
            "You write brand copy, product descriptions, Instagram captions, YouTube scripts, email sequences, and ad copy. "
            "Match the user's brand tone (playful, premium, Desi, professional). "
            "Use Hinglish when appropriate. Always include a CTA. Format as clean markdown."
        ),
        'tools': ['brand_tone_analyzer', 'caption_generator'],
    },
    'seo-consultant': {
        'id': 'seo-consultant',
        'name': 'SEO Consultant',
        'tagline': 'Rank higher, get found, drive organic traffic',
        'description': 'Analyzes websites, suggests keyword strategies, optimizes product pages, and builds content calendars for organic growth.',
        'avatar': '🔍',
        'color': '#5d8f8e',
        'system': (
            "You are Getszy's SEO Consultant — an expert in Indian e-commerce SEO. "
            "You analyze websites, suggest keyword strategies, optimize product pages, create content calendars, "
            "and explain technical SEO in simple terms. Focus on Google India, YouTube SEO, and Instagram discoverability. "
            "Always give specific, actionable steps with estimated impact."
        ),
        'tools': ['seo_audit', 'keyword_research', 'content_calendar'],
    },
    'marketing-planner': {
        'id': 'marketing-planner',
        'name': 'Marketing Planner',
        'tagline': 'Campaigns, ads, funnels & customer acquisition',
        'description': 'Plans Meta/Google ad campaigns, designs marketing funnels, suggests influencer strategies, and builds launch playbooks.',
        'avatar': '📈',
        'color': '#10b981',
        'system': (
            "You are Getszy's Marketing Planner — a performance marketing expert for Indian D2C brands. "
            "You plan Meta (Instagram/Facebook) and Google ad campaigns, design marketing funnels, suggest influencer collab strategies, "
            "and build product launch playbooks. Always include budget estimates in ₹, target audience specs, and KPIs. "
            "Be specific: CPM ranges, audience sizes, creative formats."
        ),
        'tools': ['campaign_builder', 'audience_planner', 'budget_calculator'],
    },
    'legal-advisor': {
        'id': 'legal-advisor',
        'name': 'Legal Advisor',
        'tagline': 'GST, compliance, trademarks & contracts',
        'description': 'Guides on GST registration, trademark filing, business registration, consumer law, and basic legal compliance for Indian businesses.',
        'avatar': '⚖️',
        'color': '#ef4444',
        'system': (
            "You are Getszy's Legal Advisor — knowledgeable about Indian business law, GST, trademark registration, "
            "consumer protection, and basic compliance. You explain legal concepts in simple language, "
            "suggest when to consult a real lawyer, and help with document templates. "
            "Always include relevant Indian law sections. Disclaimer: you provide guidance, not legal representation."
        ),
        'tools': ['gst_helper', 'trademark_checker'],
    },
    'customer-comms': {
        'id': 'customer-comms',
        'name': 'Customer Comms',
        'tagline': 'Support scripts, FAQs, templates & crisis response',
        'description': 'Writes support email templates, WhatsApp auto-replies, FAQ responses, refund policies, and handles customer complaint escalation scripts.',
        'avatar': '💬',
        'color': '#3b82f6',
        'system': (
            "You are Getszy's Customer Communications expert. You write support email templates, WhatsApp auto-replies, "
            "FAQ responses, refund/return policies, and escalation scripts. You understand Indian customer expectations — "
            "WhatsApp-first, quick resolution, empathy-driven. Write in the brand's tone. Include Hindi/Hinglish versions when useful."
        ),
        'tools': ['email_template', 'whatsapp_reply', 'faq_generator'],
    },
    'sales-outreach': {
        'id': 'sales-outreach',
        'name': 'Sales & Outreach',
        'tagline': 'Cold emails, DMs, partnerships & influencer outreach',
        'description': 'Crafts cold email sequences, Instagram DM scripts, partnership proposals, and influencer outreach templates that get replies.',
        'avatar': '🤝',
        'color': '#f59e0b',
        'system': (
            "You are Getszy's Sales & Outreach specialist. You craft cold email sequences, Instagram DM scripts, "
            "brand partnership proposals, and influencer outreach templates. You understand Indian market dynamics — "
            "how to approach small businesses, negotiate with influencers, and close partnership deals. "
            "Always include subject lines, follow-up sequences, and response handling scripts."
        ),
        'tools': ['cold_email_generator', 'dm_script_writer', 'partnership_template'],
    },
}

AGENT_LIST = list(AGENTS.values())


# ═══════════════════════════════════════════════════════════════════════════════
# API Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.get('/agents')
async def list_agents(user=Depends(get_current_user)):
    """List all available expert agents."""
    return {'agents': AGENT_LIST}


@router.get('/agents/{agent_id}')
async def get_agent(agent_id: str, user=Depends(get_current_user)):
    """Get details for a specific agent."""
    agent = AGENTS.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')
    return agent


@router.get('/agents/all')
async def all_agents(user=Depends(get_current_user)):
    """All agents in one call: expert + AI workforce + the user's custom agents."""
    workforce = [
        {
            'id': a['id'],
            'name': a['name'],
            'role': a.get('role'),
            'icon': a.get('icon'),
            'color': a.get('color'),
            'type': 'workforce',
        }
        for a in WORKFORCE_AGENTS
    ]
    custom = []
    try:
        cur = db.custom_agents.find({'user_id': user['id']}, {'_id': 0}).sort('created_at', -1)
        async for c in cur:
            custom.append({
                'id': c['id'],
                'name': c.get('name'),
                'role': c.get('role'),
                'color': c.get('color'),
                'icon': c.get('icon'),
                'type': 'custom',
            })
    except Exception:
        pass
    return {
        'expert': [
            {
                'id': a['id'],
                'name': a['name'],
                'tagline': a.get('tagline'),
                'color': a.get('color'),
                'avatar': a.get('avatar'),
                'type': 'expert',
            }
            for a in AGENT_LIST
        ],
        'workforce': workforce,
        'custom': custom,
        'total': len(AGENT_LIST) + len(workforce) + len(custom),
    }


class AgentChatIn(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: Optional[List[Dict[str, str]]] = None
    session_id: Optional[str] = None


@router.post('/agents/{agent_id}/chat')
async def agent_chat(agent_id: str, payload: AgentChatIn, user=Depends(get_current_user)):
    """Chat with an expert agent."""
    agent = AGENTS.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail='Agent not found')

    session_id = payload.session_id or str(uuid.uuid4())

    # Build conversation context
    system = agent['system']
    history_lines = []
    for h in (payload.history or [])[-8:]:
        role = 'U' if h.get('role') == 'user' else 'A'
        history_lines.append(f'{role}: {h.get("content", "")}')
    history_lines.append(f'U: {payload.message}')
    user_prompt = '\n'.join(history_lines)

    try:
        content = await chat_completion(system, user_prompt, temperature=0.5)
        response_text = (content or '').strip()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f'Agent unavailable: {e}')

    # Persist conversation
    chat_doc = {
        'id': str(uuid.uuid4()),
        'user_id': user['id'],
        'agent_id': agent_id,
        'session_id': session_id,
        'user_message': payload.message,
        'agent_response': response_text,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }
    await db.agent_chats.insert_one(chat_doc)

    return {
        'id': chat_doc['id'],
        'session_id': session_id,
        'agent_id': agent_id,
        'response': response_text,
        'created_at': chat_doc['created_at'],
    }


@router.get('/agents/{agent_id}/history')
async def agent_history(agent_id: str, session_id: str = '', limit: int = 30, user=Depends(get_current_user)):
    """Get chat history for an agent session."""
    q = {'user_id': user['id'], 'agent_id': agent_id}
    if session_id:
        q['session_id'] = session_id
    limit = max(1, min(limit, 100))
    cur = db.agent_chats.find(q, {'_id': 0}).sort('created_at', -1).limit(limit)
    items = [doc async for doc in cur]
    items.reverse()
    return {'items': items, 'session_id': session_id}


@router.get('/agents/sessions')
async def agent_sessions(user=Depends(get_current_user)):
    """List all agent chat sessions for the user."""
    pipeline = [
        {'$match': {'user_id': user['id']}},
        {'$sort': {'created_at': -1}},
        {'$group': {
            '_id': {'agent_id': '$agent_id', 'session_id': '$session_id'},
            'last_message': {'$first': '$user_message'},
            'last_response': {'$first': '$agent_response'},
            'created_at': {'$first': '$created_at'},
            'count': {'$sum': 1},
        }},
        {'$sort': {'created_at': -1}},
        {'$limit': 50},
    ]
    results = await db.agent_chats.aggregate(pipeline).to_list(50)
    sessions = []
    for r in results:
        gid = r['_id']
        agent = AGENTS.get(gid['agent_id'], {})
        sessions.append({
            'agent_id': gid['agent_id'],
            'session_id': gid['session_id'],
            'agent_name': agent.get('name', gid['agent_id']),
            'agent_avatar': agent.get('avatar', '🤖'),
            'last_message': r.get('last_message', ''),
            'last_response': r.get('last_response', ''),
            'message_count': r.get('count', 0),
            'created_at': r.get('created_at', ''),
        })
    return {'sessions': sessions}


# ═══════════════════════════════════════════════════════════════════════════════
# Admin Routes
# ═══════════════════════════════════════════════════════════════════════════════

class AgentUpdateIn(BaseModel):
    system: Optional[str] = None
    description: Optional[str] = None
    tools: Optional[List[str]] = None
    is_enabled: Optional[bool] = None


@router.get('/admin/agents', dependencies=[Depends(get_current_admin)])
async def admin_list_agents():
    """Admin: list all agents with stats."""
    agent_stats = []
    for a in AGENT_LIST:
        count = await db.agent_chats.count_documents({'agent_id': a['id']})
        unique_users = len(await db.agent_chats.distinct('user_id', {'agent_id': a['id']}))
        agent_stats.append({**a, 'total_chats': count, 'unique_users': unique_users})
    return {'agents': agent_stats}


@router.put('/admin/agents/{agent_id}', dependencies=[Depends(get_current_admin)])
async def admin_update_agent(agent_id: str, payload: AgentUpdateIn):
    """Admin: update agent configuration (runtime override, not persisted to source)."""
    if agent_id not in AGENTS:
        raise HTTPException(status_code=404, detail='Agent not found')
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    if updates:
        await db.agent_config.update_one(
            {'agent_id': agent_id},
            {'$set': updates},
            upsert=True,
        )
    return {'ok': True, 'updated': list(updates.keys())}


@router.get('/admin/agents/analytics', dependencies=[Depends(get_current_admin)])
async def admin_agent_analytics():
    """Admin: agent usage analytics."""
    pipeline = [
        {'$group': {
            '_id': '$agent_id',
            'total_chats': {'$sum': 1},
            'unique_users': {'$addToSet': '$user_id'},
        }},
        {'$project': {
            'agent_id': '$_id',
            'total_chats': 1,
            'unique_users': {'$size': '$unique_users'},
        }},
        {'$sort': {'total_chats': -1}},
    ]
    results = await db.agent_chats.aggregate(pipeline).to_list(20)
    return {'analytics': results}
