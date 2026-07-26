"""Agent Loop — Multi-step execution with Planner → Coder → Reviewer pipeline.

Integrates with the existing orchestrator and ChromaDB codebase RAG to handle
complex requests that require planning, code generation, and self-review.

Flow:
  1. PLANNER: Analyze request, search codebase for similar patterns, plan steps
  2. CODER: Generate/modify code using RAG context from existing codebase
  3. REVIEWER: Validate output, check for issues, suggest fixes
  4. Self-correct on failure (max 2 retries)
  5. Return final result

Key principle: NO arbitrary code execution. All actions go through
existing capabilities with validation.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from db import db
from llm_provider import chat_completion
from chat_builder.capabilities import CAPABILITIES

logger = logging.getLogger('getszy.agent')

# ── Multi-step intent detection ───────────────────────────────────────────────
MULTI_STEP_INTENTS = {
    'create_product',      # May need category check + margin calc
    'bulk_import',         # Multiple products
    'create_course',       # Course + modules + lessons
    'deploy_webapp',       # Build + push + deploy
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── RAG-powered code context ──────────────────────────────────────────────────
async def _get_rag_context(query: str, n_results: int = 3) -> str:
    """Search codebase for relevant code patterns using ChromaDB RAG."""
    try:
        from codebase_rag import search_codebase
        results = search_codebase(query, n_results=n_results)
        if not results or 'error' in results[0]:
            return ''
        parts = []
        for r in results:
            file = r.get('file', '')
            funcs = r.get('functions', '')
            code = r.get('code', '')[:500]
            parts.append(f'## {file} ({funcs})\n```python\n{code}\n```')
        return '\n\n'.join(parts)
    except Exception:
        return ''


# ── PLANNER agent ─────────────────────────────────────────────────────────────
async def _plan_steps(intent: str, params: Dict[str, Any], context: str) -> List[Dict[str, Any]]:
    """PLANNER: Use LLM + RAG to break down request into validated steps."""
    rag_context = await _get_rag_context(f'{intent} {json.dumps(params)}')

    system = f"""You are the PLANNER agent for Getszy platform.
Given a user intent and params, output a JSON array of steps.
Each step: {{"action": "capability_id", "params": {{...}}, "validation": "check description", "rag_hint": "relevant file to reference"}}

Available capabilities: {', '.join(CAPABILITIES.keys())}

EXISTING CODE PATTERNS (from codebase RAG):
{rag_context or 'No matching patterns found.'}

RULES:
- Only use capabilities that exist
- Params must match the capability's required fields
- Include validation for each step
- Reference relevant existing code in rag_hint
- Max 5 steps
- Output ONLY the JSON array, no prose"""

    user_msg = f"Intent: {intent}\nParams: {json.dumps(params)}\nContext: {context}"

    try:
        response = await chat_completion(user_msg, system, temperature=0.1)
        if '```json' in response:
            response = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            response = response.split('```')[1].split('```')[0]
        steps = json.loads(response.strip())
        if isinstance(steps, list) and len(steps) <= 5:
            return steps
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f'Planner failed: {e}')

    return [{'action': intent, 'params': params, 'validation': 'basic'}]


# ── CODER agent ───────────────────────────────────────────────────────────────
async def _generate_code(step: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """CODER: Generate code with RAG context from existing codebase."""
    action = step.get('action', '')
    params = step.get('params', {})
    rag_hint = step.get('rag_hint', '')

    # Fetch RAG context for this specific step
    rag_context = ''
    if rag_hint:
        try:
            from codebase_rag import get_file_context
            rag_context = get_file_context(rag_hint) or ''
        except Exception:
            pass

    if not rag_context:
        rag_context = await _get_rag_context(f'{action} {json.dumps(params)}')

    system = f"""You are the CODER agent for Getszy platform.
Generate or modify code based on the step requirements.

EXISTING CODEBASE CONTEXT:
{rag_context[:2000] if rag_context else 'No existing patterns found.'}

RULES:
- Reuse patterns from existing code when possible
- Follow the same code style as the existing codebase
- Include proper error handling
- Use Pydantic models for data validation
- Use motor async driver for MongoDB operations
- Return ONLY the generated code, no explanations"""

    user_msg = f"Generate code for: {action}\nParams: {json.dumps(params)}\nValidation: {step.get('validation', '')}"

    try:
        response = await chat_completion(user_msg, system, temperature=0.3)
        return {'success': True, 'code': response, 'action': action}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ── REVIEWER agent ────────────────────────────────────────────────────────────
async def _review_output(code_result: Dict[str, Any], step: Dict[str, Any]) -> Dict[str, Any]:
    """REVIEWER: Validate generated code for issues."""
    if not code_result.get('success'):
        return code_result

    code = code_result.get('code', '')
    action = step.get('action', '')

    system = """You are the REVIEWER agent. Check the generated code for:
1. Security issues (SQL injection, XSS, hardcoded secrets)
2. Missing error handling
3. Incorrect API patterns
4. Missing imports
5. Logic errors

Output JSON: {"approved": true/false, "issues": ["list of issues"], "fixes": {"issue": "fix suggestion"}}"""

    user_msg = f"Review this code for action '{action}':\n\n{code[:3000]}"

    try:
        response = await chat_completion(user_msg, system, temperature=0.1)
        if '```json' in response:
            response = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            response = response.split('```')[1].split('```')[0]
        review = json.loads(response.strip())

        if not review.get('approved', True):
            logger.warning(f'Reviewer found issues: {review.get("issues", [])}')
            code_result['review_issues'] = review.get('issues', [])
            code_result['review_fixes'] = review.get('fixes', {})

        return code_result
    except Exception:
        return code_result  # Approve on review failure


# ── Execute step through capabilities ─────────────────────────────────────────
async def _execute_step(step: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single step through the capability system."""
    from chat_builder.orchestrator import process_message

    action = step.get('action', '')
    params = step.get('params', {})

    if action not in CAPABILITIES:
        return {'success': False, 'error': f'Unknown action: {action}'}

    from auth import role_level, ROLE_LEVEL
    needed = CAPABILITIES[action].get('min_role', 'customer')
    if role_level(user) < ROLE_LEVEL.get(needed, 1):
        return {'success': False, 'error': f'Requires {needed} role'}

    try:
        project_id = f'agent_{user["id"]}_{int(datetime.now(timezone.utc).timestamp())}'
        result = await process_message(project_id, user, json.dumps({'action': action, **params}))
        return {'success': True, 'result': result}
    except Exception as e:
        return {'success': False, 'error': str(e)}


async def _self_correct(step: Dict[str, Any], error: str, attempt: int) -> Dict[str, Any]:
    """Ask LLM to fix the failed step."""
    system = f"""A step failed (attempt {attempt}/2). Fix the params and output corrected JSON.
Original step: {json.dumps(step)}
Error: {error}

Output ONLY corrected JSON step. No prose."""

    try:
        response = await chat_completion('Fix this step.', system, temperature=0.2)
        if '```json' in response:
            response = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            response = response.split('```')[1].split('```')[0]
        return json.loads(response.strip())
    except Exception:
        return step


# ── Main agent loop ───────────────────────────────────────────────────────────
async def run_agent_loop(
    intent: str,
    params: Dict[str, Any],
    user: Dict[str, Any],
    context: str = '',
    max_retries: int = 2,
) -> Dict[str, Any]:
    """Run Planner → Coder → Reviewer agent loop.

    Returns:
        {
            'steps_executed': int,
            'results': [...],
            'success': bool,
            'summary': str
        }
    """
    # PLANNER phase
    steps = await _plan_steps(intent, params, context)
    logger.info(f'Planner produced {len(steps)} steps')

    results = []
    for i, step in enumerate(steps):
        success = False
        last_error = ''

        for attempt in range(max_retries + 1):
            # CODER phase
            code_result = await _generate_code(step, user)

            # REVIEWER phase
            code_result = await _review_output(code_result, step)

            # Execute the step
            result = await _execute_step(step, user)
            if result.get('success'):
                success = True
                results.append({
                    'step': i + 1,
                    'action': step.get('action'),
                    'code_generated': code_result.get('success', False),
                    'review_issues': code_result.get('review_issues', []),
                    'result': result.get('result'),
                })
                break
            else:
                last_error = result.get('error', 'Unknown error')
                if attempt < max_retries:
                    step = await _self_correct(step, last_error, attempt + 1)

        if not success:
            return {
                'steps_executed': i,
                'results': results,
                'success': False,
                'summary': f'Step {i+1} failed after {max_retries} retries: {last_error}',
            }

    return {
        'steps_executed': len(steps),
        'results': results,
        'success': True,
        'summary': f'Successfully completed {len(steps)} step(s) with code generation and review',
    }
