"""Real, store-backed tools agents can call during a conversation.

Each tool performs a real action against Getszy's own data (products, courses,
pricing), a safe computation, or an optional web lookup. No simulated output.
"""
import os
import ast
import re
import json
import logging
from typing import Any, Callable, Coroutine, Dict, List

from db import db

logger = logging.getLogger('getszy.tools')

# ── Optional web search (active only when an API key is configured) ───────────
TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY', '').strip()
BRAVE_API_KEY = os.environ.get('BRAVE_API_KEY', '').strip()


async def search_products(query: str, max_price: float = None, category: str = None, limit: int = 8) -> List[dict]:
    """Search the live store catalogue by keyword, optional max price (INR) & category."""
    if not query or not query.strip():
        return []
    regex = {'$regex': re.escape(query), '$options': 'i'}
    q: Dict[str, Any] = {'is_active': True, '$or': [
        {'name': regex}, {'description': regex}, {'tags': regex}, {'category': regex},
    ]}
    if category:
        q['category'] = category
    if max_price is not None:
        try:
            q['price'] = {'$lte': float(max_price)}
        except (TypeError, ValueError):
            pass
    cur = db.products.find(
        q, {'_id': 0, 'name': 1, 'slug': 1, 'price': 1, 'category': 1, 'currency': 1, 'image_url': 1}
    ).limit(limit)
    out = []
    async for p in cur:
        out.append({
            'id': p.get('slug') or p.get('id'),
            'name': p.get('name'),
            'price': p.get('price'),
            'currency': p.get('currency', 'INR'),
            'category': p.get('category'),
            'image': p.get('image_url'),
        })
    return out


async def list_courses(query: str = '', limit: int = 8) -> List[dict]:
    """List published Academy courses, optionally filtered by keyword."""
    q: Dict[str, Any] = {}
    if query:
        regex = {'$regex': re.escape(query), '$options': 'i'}
        q['$or'] = [{'title': regex}, {'description': regex}, {'tags': regex}]
    cur = db.courses.find(
        q, {'_id': 0, 'title': 1, 'slug': 1, 'level': 1, 'price': 1, 'is_premium': 1}
    ).limit(limit)
    out = []
    async for c in cur:
        out.append({
            'title': c.get('title'), 'slug': c.get('slug'),
            'level': c.get('level'), 'price': c.get('price'), 'premium': c.get('is_premium'),
        })
    return out


async def get_pricing_plans() -> List[dict]:
    """Return current subscription plan tiers and monthly prices."""
    try:
        from subscription import PRICING
        return PRICING
    except Exception:
        return [
            {'id': 'free', 'name': 'Free', 'price_monthly': 0},
            {'id': 'pro', 'name': 'Pro', 'price_monthly': 799},
            {'id': 'elite', 'name': 'Elite', 'price_monthly': 1999},
        ]


# Guardrails against arithmetic-bomb DoS (e.g. 9**9**9).
_MAX_OPERAND = 1e12
_MAX_EXPONENT = 10000
_MAX_RESULT_MAGNITUDE = 1e18
_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.FloorDiv)
_ALLOWED_UNARYOPS = (ast.UAdd, ast.USub)


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):  # numbers only
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return float(node.value)
        raise ValueError('only numeric constants are allowed')
    if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINOPS):
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        # NOTE: do NOT build a dict of `left OP right` expressions — a dict literal
        # evaluates every value eagerly, so `left ** right` would run even for a
        # `+`/`*` op and overflow on large operands. Compute only the actual op.
        if isinstance(node.op, ast.Pow):
            if abs(left) > _MAX_OPERAND or abs(right) > _MAX_EXPONENT:
                raise ValueError('exponent too large')
        elif abs(left) > _MAX_OPERAND or abs(right) > _MAX_OPERAND:
            raise ValueError('operand too large')
        if isinstance(node.op, ast.Div) and right == 0:
            raise ZeroDivisionError('division by zero')
        if isinstance(node.op, ast.Add):
            result = left + right
        elif isinstance(node.op, ast.Sub):
            result = left - right
        elif isinstance(node.op, ast.Mult):
            result = left * right
        elif isinstance(node.op, ast.Div):
            result = left / right
        elif isinstance(node.op, ast.Mod):
            result = left % right
        elif isinstance(node.op, ast.Pow):
            result = left ** right
        elif isinstance(node.op, ast.FloorDiv):
            result = left // right
        else:
            raise ValueError('unsupported expression')
        if not __import__('math').isfinite(result) or abs(result) > _MAX_RESULT_MAGNITUDE:
            raise ValueError('result out of range')
        return result
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_UNARYOPS):
        return _safe_eval(node.operand) if isinstance(node.op, ast.UAdd) else -_safe_eval(node.operand)
    raise ValueError('unsupported expression')


async def calculate(expression: str) -> str:
    """Safely evaluate a basic arithmetic expression (numbers and + - * / ( ) % only).

    Uses an AST whitelist instead of eval(); rejects code execution and arithmetic
    bombs (huge exponents / results) that would hang or OOM the server.
    """
    if not expression:
        return 'empty expression'
    if not all(ch in set('0123456789.+-*/()% ') for ch in expression):
        return 'unsupported characters in expression'
    if len(expression) > 200:
        return 'expression too long'
    try:
        tree = ast.parse(expression, mode='eval')
        result = _safe_eval(tree)
        return str(int(result)) if result == int(result) else str(result)
    except ZeroDivisionError:
        return 'division by zero'
    except Exception as e:
        return f'could not compute: {e}'


async def web_search(query: str, max_results: int = 5) -> List[dict]:
    """Web search via Tavily or Brave. Returns [] if no key is configured."""
    if TAVILY_API_KEY:
        import httpx
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(
                'https://api.tavily.com/search',
                json={'api_key': TAVILY_API_KEY, 'query': query, 'max_results': max_results},
                headers={'Content-Type': 'application/json'},
            )
            r.raise_for_status()
            return [{'title': i.get('title'), 'url': i.get('url'), 'snippet': i.get('content')}
                    for i in r.json().get('results', [])]
    if BRAVE_API_KEY:
        import httpx
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(
                'https://api.search.brave.com/res/v1/web/search',
                params={'q': query, 'count': max_results},
                headers={'X-Subscription-Token': BRAVE_API_KEY, 'Accept': 'application/json'},
            )
            r.raise_for_status()
            return [{'title': i.get('title'), 'url': i.get('url'), 'snippet': i.get('description')}
                    for i in r.json().get('web', {}).get('results', [])]
    return []


# ── Registry ──────────────────────────────────────────────────────────────────
TOOL_REGISTRY: Dict[str, Callable[..., Coroutine]] = {
    'search_products': search_products,
    'list_courses': list_courses,
    'get_pricing_plans': get_pricing_plans,
    'calculate': calculate,
    'web_search': web_search,
}

TOOL_SCHEMAS: List[dict] = [
    {
        'type': 'function',
        'function': {
            'name': 'search_products',
            'description': 'Search Getszy store products by keyword, optional max price (INR) and category. Use when the user asks about products, prices, or what to buy.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'query': {'type': 'string', 'description': 'Product search keywords'},
                    'max_price': {'type': 'number', 'description': 'Maximum price in INR'},
                    'category': {'type': 'string', 'description': 'Product category e.g. Saree, Jewellery, Beauty'},
                },
                'required': ['query'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'list_courses',
            'description': 'List Getszy Academy courses, optionally filtered by keyword. Use for course recommendations.',
            'parameters': {'type': 'object', 'properties': {'query': {'type': 'string'}}, 'required': []},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_pricing_plans',
            'description': 'Return current subscription plan tiers and monthly prices (Free/Pro/Elite).',
            'parameters': {'type': 'object', 'properties': {}, 'required': []},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'calculate',
            'description': 'Evaluate a basic arithmetic expression (e.g. unit economics, margins, ROI). Only numbers and + - * / ( ) % allowed.',
            'parameters': {
                'type': 'object',
                'properties': {'expression': {'type': 'string', 'description': 'Arithmetic expression'}},
                'required': ['expression'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'web_search',
            'description': 'Search the public web for recent facts, trends, or competitor info. Use sparingly.',
            'parameters': {
                'type': 'object',
                'properties': {'query': {'type': 'string'}, 'max_results': {'type': 'integer'}},
                'required': ['query'],
            },
        },
    },
]


def get_schemas(names: List[str]) -> List[dict]:
    by_name = {s['function']['name']: s for s in TOOL_SCHEMAS}
    return [by_name[n] for n in names if n in by_name]


async def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool by name and return a compact string result for the model."""
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return f'error: unknown tool {name}'
    try:
        result = await fn(**(arguments or {}))
    except Exception as e:
        return f'error executing {name}: {e}'
    if isinstance(result, str):
        return result
    text = json.dumps(result, ensure_ascii=False, default=str)
    if len(text) > 4000:
        text = text[:4000] + '...[truncated]'
    return text
