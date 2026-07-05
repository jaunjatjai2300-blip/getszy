"""Built-in Getszy Skills - the marketplace catalog.

Each skill is small, focused, and reuses existing services so we never
duplicate business logic. Skills can be triggered by:
  * REST: POST /api/admin/skills/{name}/run
  * Copilot: natural language -> skill name + params
  * Stack: included in a YAML campaign stack
  * Auto-pilot: scheduled cron triggers
"""
import os
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from skills.registry import register
from db import db
from llm_provider import chat_completion
from sourcing.trending import scan_trending
from sourcing.markup import enforce_price, compute_margin
from media import pollinations

logger = logging.getLogger('getszy.skills')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============================================================================
# COMMERCE (5 skills)
# ============================================================================
@register(
    name='scan_trending', title='Scan Trending Products', category='commerce',
    icon='TrendingUp', badge='free',
    description='Discover trending Indian niches with AI-curated picks.',
    params={'count': {'type': 'integer', 'default': 12, 'min': 3, 'max': 24}},
)
async def scan_trending_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    items = await scan_trending(limit=int(p.get('count', 12)))
    return {'count': len(items), 'items': items[:5], 'preview_only': True}


@register(
    name='import_trending', title='Import Trending to Store', category='commerce',
    icon='Plus', badge='free',
    description='Run a scan, then auto-import the top N items with enforced margins.',
    params={'count': {'type': 'integer', 'default': 5}, 'min_score': {'type': 'integer', 'default': 80}},
)
async def import_trending_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    items = await scan_trending(limit=int(p.get('count', 5)))
    min_score = int(p.get('min_score', 80))
    imported = []
    for it in items:
        if it['trend_score'] < min_score:
            continue
        pid = str(uuid.uuid4())
        doc = {
            'id': pid,
            'name': it['title'],
            'slug': it['title'].lower().replace(' ', '-')[:80] + '-' + pid[:6],
            'description': f"Trending pick. {it.get('niche', '')}",
            'images': [it['hero_image']],
            'price': it['suggested_price'],
            'cost_price': it['cost_price'],
            'stock': 50,
            'category': it['category'],
            'supplier': 'Getszy Source',
            'is_digital': False,
            'is_featured': True,
            'is_active': True,
            'sourcing': {'niche': it['niche'], 'audience': it['audience'], 'imported_at': _now()},
            'created_at': _now(),
        }
        await db.products.insert_one(doc)
        imported.append({'id': pid, 'name': it['title'], 'price': it['suggested_price'], 'margin_pct': it['margin_pct']})
    return {'imported_count': len(imported), 'items': imported}


@register(
    name='enforce_margins', title='Audit & Fix Product Margins', category='commerce',
    icon='IndianRupee', badge='free',
    description='Find products below 40% physical / 70% digital margin and auto-correct.',
    params={'dry_run': {'type': 'boolean', 'default': True}},
)
async def enforce_margins_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    fixed = []
    cur = db.products.find({}, {'_id': 0})
    async for prod in cur:
        cost = prod.get('cost_price') or 0
        if cost <= 0:
            continue
        is_digital = bool(prod.get('is_digital'))
        m = compute_margin(cost, prod.get('price', 0))
        floor = 70 if is_digital else 40
        if m['margin_pct'] < floor:
            new_price = enforce_price(cost, is_digital=is_digital)
            fixed.append({'id': prod['id'], 'name': prod['name'], 'old_price': prod.get('price'), 'new_price': new_price, 'old_margin': m['margin_pct']})
            if not p.get('dry_run', True):
                await db.products.update_one({'id': prod['id']}, {'$set': {'price': new_price, 'price_updated_at': _now()}})
    return {'mode': 'dry_run' if p.get('dry_run', True) else 'applied', 'affected_count': len(fixed), 'items': fixed[:20]}


@register(
    name='list_low_stock', title='Low Stock Alert', category='commerce',
    icon='AlertTriangle', badge='free',
    description='List products with stock below a threshold.',
    params={'threshold': {'type': 'integer', 'default': 5}},
)
async def list_low_stock_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    threshold = int(p.get('threshold', 5))
    cur = db.products.find({'stock': {'$lte': threshold}, 'is_active': True}, {'_id': 0, 'id': 1, 'name': 1, 'stock': 1, 'price': 1})
    items = [doc async for doc in cur]
    return {'count': len(items), 'threshold': threshold, 'items': items[:20]}


@register(
    name='top_sellers', title='Top Sellers Report', category='analytics',
    icon='Trophy', badge='free',
    description='Identify best-selling products by units sold this month.',
    params={'limit': {'type': 'integer', 'default': 10}},
)
async def top_sellers_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    pipeline = [
        {'$unwind': '$items'},
        {'$group': {'_id': '$items.product_id', 'units': {'$sum': '$items.qty'}, 'revenue': {'$sum': '$items.subtotal'}}},
        {'$sort': {'units': -1}},
        {'$limit': int(p.get('limit', 10))},
    ]
    rows = []
    async for row in db.orders.aggregate(pipeline):
        prod = await db.products.find_one({'id': row['_id']}, {'_id': 0, 'name': 1})
        rows.append({'product_id': row['_id'], 'name': (prod or {}).get('name', 'Unknown'), 'units': row['units'], 'revenue': row['revenue']})
    return {'count': len(rows), 'items': rows}


# ============================================================================
# MEDIA (4 skills)
# ============================================================================
@register(
    name='generate_logo', title='Generate Logo & Brand Kit', category='media',
    icon='Palette', badge='free',
    description='4 logo concepts for a brand name + tagline.',
    params={'brand': {'type': 'string', 'required': True}, 'style': {'type': 'string', 'default': 'minimal'}},
)
async def generate_logo_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    brand = p.get('brand') or 'Getszy'
    prompt = f'logo for "{brand}", {p.get("style", "minimal")} style, vector mark, centered, flat, modern'
    variants = []
    for i in range(4):
        url = pollinations.build_url(prompt, style='logo', width=1024, height=1024, seed=10000 + i * 17)
        variants.append({'index': i, 'url': url})
    return {'brand': brand, 'variants': variants}


@register(
    name='generate_hero_image', title='Generate Hero Image', category='media',
    icon='Image', badge='free',
    description='AI-generated hero image for landing or product page.',
    params={'prompt': {'type': 'string', 'required': True}, 'style': {'type': 'string', 'default': 'photoreal'}},
)
async def generate_hero_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    url = pollinations.build_url(p.get('prompt', 'hero image'), style=p.get('style', 'photoreal'), width=1536, height=864)
    return {'url': url, 'prompt': p.get('prompt')}


@register(
    name='write_product_descriptions', title='Write Product Descriptions', category='media',
    icon='PenTool', badge='free',
    description='Generate compelling descriptions for products that are missing one.',
    params={'limit': {'type': 'integer', 'default': 5}},
)
async def write_descriptions_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    limit = int(p.get('limit', 5))
    cur = db.products.find({'$or': [{'description': {'$exists': False}}, {'description': ''}, {'description': None}]}, {'_id': 0, 'id': 1, 'name': 1}).limit(limit)
    targets = [doc async for doc in cur]
    updated = []
    for t in targets:
        try:
            out = await chat_completion(
                'You write concise, persuasive product descriptions for an Indian D2C brand. Reply with 2 short paragraphs, no markdown.',
                f'Write a product description for: {t["name"]}',
                temperature=0.7,
            )
            await db.products.update_one({'id': t['id']}, {'$set': {'description': out.strip()}})
            updated.append({'id': t['id'], 'name': t['name']})
        except Exception as e:
            logger.warning(f'desc gen failed for {t["id"]}: {e}')
    return {'updated_count': len(updated), 'items': updated}


@register(
    name='translate_to_hindi', title='Translate Store to Hindi', category='media',
    icon='Languages', badge='pro',
    description='Add a Hindi name/description field to selected products.',
    params={'limit': {'type': 'integer', 'default': 10}},
)
async def translate_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    limit = int(p.get('limit', 10))
    cur = db.products.find({'name_hi': {'$exists': False}}, {'_id': 0, 'id': 1, 'name': 1, 'description': 1}).limit(limit)
    targets = [doc async for doc in cur]
    done = []
    for t in targets:
        try:
            out = await chat_completion(
                'You translate Indian e-commerce product copy to natural Hindi. Reply with just the translated text, no explanation.',
                f'Translate to Hindi:\nName: {t["name"]}\nDescription: {t.get("description", "")}',
                temperature=0.3,
            )
            await db.products.update_one({'id': t['id']}, {'$set': {'name_hi': out.split(chr(10))[0].strip(), 'description_hi': out.strip()}})
            done.append({'id': t['id'], 'name': t['name']})
        except Exception as e:
            logger.warning(f'translate failed for {t["id"]}: {e}')
    return {'translated_count': len(done), 'items': done}


# ============================================================================
# ANALYTICS (3 skills)
# ============================================================================
@register(
    name='revenue_report', title='Revenue Report', category='analytics',
    icon='LineChart', badge='free',
    description='Aggregate revenue, orders, AOV for a date range.',
    params={'days': {'type': 'integer', 'default': 30}},
)
async def revenue_report_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    days = int(p.get('days', 30))
    pipeline = [
        {'$match': {'status': {'$in': ['paid', 'shipped', 'delivered']}}},
        {'$group': {'_id': None, 'orders': {'$sum': 1}, 'revenue': {'$sum': '$total'}}},
    ]
    agg = [r async for r in db.orders.aggregate(pipeline)]
    revenue = (agg[0]['revenue'] if agg else 0) or 0
    orders = (agg[0]['orders'] if agg else 0) or 0
    return {'window_days': days, 'orders': orders, 'revenue': revenue, 'aov': round(revenue / orders, 2) if orders else 0}


@register(
    name='ai_insights', title='Daily AI Insights', category='analytics',
    icon='Brain', badge='free',
    description='Generate human-readable insights about today\'s store performance.',
    params={},
)
async def ai_insights_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    rev = await revenue_report_skill({'days': 7}, ctx)
    sellers = await top_sellers_skill({'limit': 3}, ctx)
    summary_data = f'Last 7 days revenue: ₹{rev["revenue"]}, orders: {rev["orders"]}, AOV: ₹{rev["aov"]}. Top sellers: {[s["name"] for s in sellers["items"]]}.'
    try:
        out = await chat_completion(
            'You are a friendly Indian e-commerce strategist. Reply in Hinglish (Hindi-English mix). 3 short bullets max.',
            f'Summarize and suggest 3 actions: {summary_data}',
            temperature=0.6,
        )
        insights = out.strip()
    except Exception:
        insights = summary_data
    return {'metrics': rev, 'top_sellers': sellers.get('items', [])[:3], 'insights': insights}


@register(
    name='cart_abandonment', title='Cart Abandonment Report', category='analytics',
    icon='ShoppingCart', badge='free',
    description='Count carts active >24h without an order.',
    params={},
)
async def cart_abandon_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    try:
        carts = await db.carts.count_documents({})
    except Exception:
        carts = 0
    orders = await db.orders.count_documents({}) if 'orders' in await db.list_collection_names() else 0
    return {'active_carts': carts, 'orders_placed': orders, 'abandonment_signal': max(0, carts - orders)}


# ============================================================================
# DEVOPS (3 skills)
# ============================================================================
@register(
    name='deploy_to_github', title='Push Plan to GitHub', category='devops',
    icon='GitBranch', badge='free',
    description='Save a deploy job manifest to the configured repo.',
    params={'brief': {'type': 'string', 'required': True}},
)
async def deploy_github_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    from routes_deploy import _run_swarm, _push_marker_commit
    brief = p.get('brief', '')
    swarm = await _run_swarm(brief, 'tool')
    job_id = str(uuid.uuid4())
    push = await _push_marker_commit(job_id, brief, swarm)
    await db.deploy_jobs.insert_one({
        'id': job_id, 'brief': brief, 'target': 'tool', 'admin_id': ctx.get('user_id', 'copilot'),
        'status': 'pushed' if push.get('ok') else 'planned', 'agents': swarm, 'deploy_status': push, 'created_at': _now(),
    })
    return {'job_id': job_id, 'push': push}


@register(
    name='health_check', title='System Health Check', category='devops',
    icon='Activity', badge='free',
    description='Verify backend services, LLM, MongoDB, media cache.',
    params={},
)
async def health_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    checks = {}
    try:
        await db.command('ping')
        checks['mongodb'] = 'ok'
    except Exception as e:
        checks['mongodb'] = f'fail: {e}'
    try:
        out = await chat_completion('You reply with one word.', 'ping', temperature=0)
        checks['llm'] = 'ok' if out else 'empty'
    except Exception as e:
        checks['llm'] = f'fail: {e}'
    from pathlib import Path
    checks['media_cache'] = 'ok' if Path('/app/backend/media_cache').exists() else 'missing'
    return {'status': 'healthy' if all(v == 'ok' for v in checks.values()) else 'degraded', 'checks': checks}


@register(
    name='backup_database', title='Backup Database', category='devops',
    icon='Database', badge='pro',
    description='Export all collections to a JSON dump record.',
    params={},
)
async def backup_db_skill(p: Dict[str, Any], ctx: Dict[str, Any]):
    cols = await db.list_collection_names()
    counts = {}
    for c in cols:
        if c.startswith('system.'):
            continue
        try:
            counts[c] = await db[c].count_documents({})
        except Exception:
            counts[c] = -1
    backup_id = str(uuid.uuid4())
    await db.backups.insert_one({'id': backup_id, 'at': _now(), 'counts': counts})
    return {'backup_id': backup_id, 'collections': counts}
