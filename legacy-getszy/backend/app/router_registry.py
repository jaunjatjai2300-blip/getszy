"""Router Registry — Organized by category for easy management.

Instead of importing 65+ routers in server.py, this file groups them logically.
Each category can be enabled/disabled independently.
"""
from fastapi import APIRouter

# ── Core routers (always loaded) ──────────────────────────────────────────────
CORE_ROUTERS = [
    ('auth', 'routes_auth', 'auth'),
    ('catalog', 'routes_catalog', 'catalog'),
    ('cart_orders', 'routes_cart_orders', 'cart'),
    ('admin', 'routes_admin', 'admin'),
]

# ── Learning & Academy ────────────────────────────────────────────────────────
LEARNING_ROUTERS = [
    ('learning', 'routes_learning', 'learning'),
    ('learning_platform', 'routes_learning_platform', 'learning-platform'),
]

# ── AI & Chat ─────────────────────────────────────────────────────────────────
AI_ROUTERS = [
    ('ai_ops', 'routes_ai_ops', 'ai-ops'),
    ('ai_platform', 'routes_ai_platform', 'ai-platform'),
    ('ai_workforce', 'routes_ai_workforce', 'ai-workforce'),
    ('chat_builder', 'routes_chat_builder', 'chat-builder'),
    ('copilot', 'routes_copilot', 'copilot'),
    ('neo_content', 'routes_neo_content', 'neo-content'),
]

# ── Commerce & Payments ───────────────────────────────────────────────────────
COMMERCE_ROUTERS = [
    ('subscription', 'routes_subscription', 'subscription'),
    ('razorpay', 'routes_razorpay', 'razorpay'),
    ('credits', 'routes_credits', 'credits'),
    ('commerce_extra', 'routes_commerce_extra', 'commerce-extra'),
    ('sourcing', 'routes_sourcing', 'sourcing'),
]

# ── Media & Content ───────────────────────────────────────────────────────────
MEDIA_ROUTERS = [
    ('media', 'routes_media', 'media'),
    ('images', 'routes_images', 'images'),
    ('voice', 'routes_voice', 'voice'),
    ('video', 'routes_video', 'video'),
    ('video_factory', 'routes_video_factory', 'video-factory'),
    ('publishing', 'routes_publishing', 'publishing'),
    ('avatar', 'routes_avatar', 'avatar'),
]

# ── Creator & Workforce ───────────────────────────────────────────────────────
CREATOR_ROUTERS = [
    ('creator', 'routes_creator', 'creator'),
    ('creator_platform', 'routes_creator_platform', 'creator-platform'),
    ('workforce', 'routes_workforce', 'workforce'),
    ('video_tools', 'routes_video_tools', 'video-tools'),
    ('catalog_video', 'routes_catalog_video', 'catalog-video'),
]

# ── Builders & Studio ─────────────────────────────────────────────────────────
BUILD_ROUTERS = [
    ('builder', 'routes_builder', 'builder'),
    ('build_studio', 'routes_build_studio', 'build-studio'),
    ('api_builder', 'routes_api_builder', 'api-builder'),
    ('mobile_builder', 'routes_mobile_builder', 'mobile-builder'),
    ('business_builders', 'routes_business_builders', 'business-builders'),
    ('saas_builder', 'routes_saas_builder', 'saas-builder'),
]

# ── Deploy & Infrastructure ───────────────────────────────────────────────────
DEPLOY_ROUTERS = [
    ('deploy', 'routes_deploy', 'deploy'),
    ('deploy_platform', 'routes_deploy_platform', 'deploy-platform'),
    ('hosting', 'routes_hosting', 'hosting'),
    ('git', 'routes_git', 'git'),
]

# ── Platform & Operations ─────────────────────────────────────────────────────
PLATFORM_ROUTERS = [
    ('founder', 'routes_founder', 'founder'),
    ('enterprise_security', 'routes_enterprise_security', 'enterprise-security'),
    ('security', 'routes_security', 'security'),
    ('operations', 'routes_operations', 'operations'),
    ('settings', 'routes_settings', 'settings'),
    ('skills', 'routes_skills', 'skills'),
    ('stacks', 'routes_stacks', 'stacks'),
    ('neo_ops', 'routes_neo_ops', 'neo-ops'),
    ('automations', 'routes_automations', 'automations'),
    ('bulk', 'routes_bulk', 'bulk'),
    ('observability', 'routes_observability', 'observability'),
    ('i18n', 'routes_i18n', 'i18n'),
    ('einvoice', 'routes_einvoice', 'einvoice'),
]

# ── Support & Legal ───────────────────────────────────────────────────────────
SUPPORT_ROUTERS = [
    ('support', 'routes_support', 'support'),
    ('legal', 'routes_legal', 'legal'),
    ('waitlist', 'routes_waitlist', 'waitlist'),
]

# ── Analytics & Growth ────────────────────────────────────────────────────────
ANALYTICS_ROUTERS = [
    ('advanced_analytics', 'routes_advanced_analytics', 'analytics'),
    ('growth', 'routes_growth', 'growth'),
    ('marketplace', 'routes_marketplace', 'marketplace'),
]

# ── Misc & Extras ─────────────────────────────────────────────────────────────
# ── AI Tools (customer-facing) ─────────────────────────────────────────────────
AI_TOOLS_ROUTERS = [
    ('ai_tools', 'routes_ai_tools', 'ai-tools'),
    ('agents', 'routes_agents', 'agents'),
    ('integrations', 'routes_integrations', 'integrations'),
]

MISC_ROUTERS = [
    ('workspace', 'routes_workspace', 'workspace'),
    ('projects', 'routes_projects', 'projects'),
    ('social', 'routes_social', 'social'),
    ('workflows', 'routes_workflows', 'workflows'),
    ('notifications', 'routes_notifications', 'notifications'),
    ('audit', 'routes_audit', 'audit'),
    ('queue', 'routes_queue', 'queue'),
    ('extras', 'routes_extras', 'extras'),
    ('ws', 'routes_ws', 'ws'),
]

# ── Founder's Creator Engine (newest) ─────────────────────────────────────────
ENGINE_ROUTERS = [
    ('creator_engine', 'creator_engine', 'creator-engine'),
]


def load_all_routers() -> APIRouter:
    """Load all routers into a single APIRouter."""
    combined = APIRouter()
    all_categories = (
        CORE_ROUTERS + LEARNING_ROUTERS + AI_ROUTERS + COMMERCE_ROUTERS +
        MEDIA_ROUTERS + CREATOR_ROUTERS + BUILD_ROUTERS + DEPLOY_ROUTERS +
        PLATFORM_ROUTERS + SUPPORT_ROUTERS + ANALYTICS_ROUTERS + MISC_ROUTERS +
        AI_TOOLS_ROUTERS + ENGINE_ROUTERS
    )
    for name, module_name, prefix in all_categories:
        try:
            mod = __import__(module_name)
            router = getattr(mod, 'router', None)
            if router:
                combined.include_router(router)
        except ImportError as e:
            print(f'[router-registry] Skipping {name}: {e}')
    return combined


def load_core_routers() -> APIRouter:
    """Load only core routers (for minimal deployments)."""
    combined = APIRouter()
    for name, module_name, prefix in CORE_ROUTERS:
        try:
            mod = __import__(module_name)
            router = getattr(mod, 'router', None)
            if router:
                combined.include_router(router)
        except ImportError as e:
            print(f'[router-registry] Skipping {name}: {e}')
    return combined
