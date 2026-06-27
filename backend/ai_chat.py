"""AI Admin Chat — natural language to structured admin actions, then execute."""
import os
import re
import json
import uuid
from datetime import datetime, timezone, timedelta
from emergentintegrations.llm.chat import LlmChat, UserMessage
from db import db
from models import Product, Supplier, Category

EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']

SYSTEM_PROMPT = """
You are getszy.com's AI Admin assistant. You convert natural-language admin commands
into a SINGLE JSON object that the backend will execute. NEVER produce prose, NEVER wrap
in markdown — output ONLY a raw JSON object with this shape:

{
  "intent": "<one of: add_product | update_product | delete_product | list_products | add_category | list_categories | list_orders | update_order_status | add_supplier | list_suppliers | show_stats | low_stock | clarify | reject | chat>",
  "params": { ...intent-specific fields... },
  "reply": "<short friendly confirmation message in Hinglish for the admin>"
}

Intent param schemas:
- add_product: { name (str), price (number), category (str), cost_price? (number), stock? (int, default 10), supplier? (str), description? (str), image? (str URL) }
- update_product: { product_query (str: name), updates: { price?, stock?, category?, supplier?, description? } }
- delete_product: { product_query (str) }
- list_products: { category? (str), search? (str), limit? (int) }
- add_category: { name (str) }
- list_categories: {}
- list_orders: { status? (str), date_range? (str: today|week|month) }
- update_order_status: { order_id (str), status (str), tracking_number? (str) }
- add_supplier: { name (str), contact? (str), notes? (str) }
- list_suppliers: {}
- show_stats: { range? (str: today|week|month|all) }
- low_stock: { threshold? (int, default 5) }
- clarify: { question (str) }
- reject: { reason (str) }
- chat: { message (str) }

Rules: refuse bulk-destructive ("delete all"), ask clarify if required fields missing, output ONLY valid JSON.
"""


def _extract_json(text: str):
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    start = text.find('{')
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i+1])
                except Exception:
                    return None
    return None


async def parse_intent(message: str, session_id: str):
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=SYSTEM_PROMPT,
    ).with_model('openai', 'gpt-4o-mini')
    raw = await chat.send_message(UserMessage(text=message))
    parsed = _extract_json(raw)
    if not parsed:
        return {'intent': 'chat', 'params': {'message': raw}, 'reply': raw}
    return parsed


def _slug(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


async def _ensure_category(name: str) -> str:
    if not name:
        return 'fashion'
    slug = _slug(name)
    existing = await db.categories.find_one({'slug': slug}, {'_id': 0})
    if existing:
        return existing['slug']
    cat = Category(name=name.title(), slug=slug)
    await db.categories.insert_one(cat.model_dump())
    return slug


async def execute_intent(parsed: dict) -> dict:
    intent = parsed.get('intent')
    p = parsed.get('params', {}) or {}
    try:
        if intent == 'add_product':
            name = p.get('name')
            price = float(p.get('price', 0))
            if not name or not price:
                return {'ok': False, 'error': 'Name & price required'}
            cat_slug = await _ensure_category(p.get('category') or 'fashion')
            image = p.get('image') or 'https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=600'
            prod = Product(
                name=name,
                slug=_slug(name),
                description=p.get('description', ''),
                images=[image],
                price=price,
                cost_price=float(p.get('cost_price', 0) or 0),
                stock=int(p.get('stock', 10) or 10),
                category=cat_slug,
                supplier=p.get('supplier'),
            )
            await db.products.insert_one(prod.model_dump())
            return {'ok': True, 'type': 'product', 'data': prod.model_dump()}

        if intent == 'update_product':
            q = p.get('product_query', '')
            updates = p.get('updates', {}) or {}
            if not q:
                return {'ok': False, 'error': 'product_query required'}
            prod = await db.products.find_one({'name': {'$regex': q, '$options': 'i'}}, {'_id': 0})
            if not prod:
                return {'ok': False, 'error': f"No product matches '{q}'"}
            await db.products.update_one({'id': prod['id']}, {'$set': updates})
            updated = await db.products.find_one({'id': prod['id']}, {'_id': 0})
            return {'ok': True, 'type': 'product', 'data': updated}

        if intent == 'delete_product':
            q = p.get('product_query', '')
            prod = await db.products.find_one({'name': {'$regex': q, '$options': 'i'}}, {'_id': 0})
            if not prod:
                return {'ok': False, 'error': f"No product matches '{q}'"}
            await db.products.delete_one({'id': prod['id']})
            return {'ok': True, 'type': 'deleted_product', 'data': {'name': prod['name'], 'id': prod['id']}}

        if intent == 'list_products':
            q = {}
            if p.get('category'):
                q['category'] = _slug(p['category'])
            if p.get('search'):
                q['name'] = {'$regex': p['search'], '$options': 'i'}
            limit = int(p.get('limit', 20) or 20)
            prods = await db.products.find(q, {'_id': 0}).limit(limit).to_list(limit)
            return {'ok': True, 'type': 'product_list', 'data': prods, 'count': len(prods)}

        if intent == 'add_category':
            name = p.get('name')
            if not name:
                return {'ok': False, 'error': 'name required'}
            slug = await _ensure_category(name)
            cat = await db.categories.find_one({'slug': slug}, {'_id': 0})
            return {'ok': True, 'type': 'category', 'data': cat}

        if intent == 'list_categories':
            cats = await db.categories.find({}, {'_id': 0}).to_list(100)
            return {'ok': True, 'type': 'category_list', 'data': cats}

        if intent == 'list_orders':
            q = {}
            if p.get('status'):
                q['status'] = p['status']
            if p.get('date_range'):
                now = datetime.now(timezone.utc)
                if p['date_range'] == 'today':
                    since = now.replace(hour=0, minute=0, second=0, microsecond=0)
                elif p['date_range'] == 'week':
                    since = now - timedelta(days=7)
                else:
                    since = now - timedelta(days=30)
                q['created_at'] = {'$gte': since.isoformat()}
            orders = await db.orders.find(q, {'_id': 0}).sort('created_at', -1).limit(50).to_list(50)
            return {'ok': True, 'type': 'order_list', 'data': orders, 'count': len(orders)}

        if intent == 'update_order_status':
            order_id = p.get('order_id')
            order = await db.orders.find_one({'$or': [{'order_number': order_id}, {'id': order_id}]}, {'_id': 0})
            if not order:
                return {'ok': False, 'error': f'Order {order_id} not found'}
            updates = {'status': p.get('status', order['status'])}
            if p.get('tracking_number'):
                updates['tracking_number'] = p['tracking_number']
            await db.orders.update_one({'id': order['id']}, {'$set': updates})
            updated = await db.orders.find_one({'id': order['id']}, {'_id': 0})
            return {'ok': True, 'type': 'order', 'data': updated}

        if intent == 'add_supplier':
            name = p.get('name')
            if not name:
                return {'ok': False, 'error': 'name required'}
            sup = Supplier(name=name, contact=p.get('contact'), notes=p.get('notes'))
            await db.suppliers.insert_one(sup.model_dump())
            return {'ok': True, 'type': 'supplier', 'data': sup.model_dump()}

        if intent == 'list_suppliers':
            sups = await db.suppliers.find({}, {'_id': 0}).to_list(100)
            return {'ok': True, 'type': 'supplier_list', 'data': sups}

        if intent == 'show_stats':
            from routes_admin import compute_stats
            stats = await compute_stats(p.get('range', 'today'))
            return {'ok': True, 'type': 'stats', 'data': stats}

        if intent == 'low_stock':
            threshold = int(p.get('threshold', 5) or 5)
            prods = await db.products.find({'stock': {'$lte': threshold}}, {'_id': 0}).to_list(100)
            return {'ok': True, 'type': 'product_list', 'data': prods, 'count': len(prods)}

        if intent == 'clarify':
            return {'ok': True, 'type': 'clarify', 'data': p}

        if intent == 'reject':
            return {'ok': True, 'type': 'reject', 'data': p}

        # chat / fallback
        return {'ok': True, 'type': 'chat', 'data': p}

    except Exception as e:
        return {'ok': False, 'error': str(e)}
