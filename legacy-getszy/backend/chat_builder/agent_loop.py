"""Agent Loop — Lightweight multi-step execution with self-correction.

Integrates with the existing orchestrator to handle complex requests that
require multiple steps (e.g., "create a product and add it to a category").

Flow:
  1. Classify intent (existing)
  2. If intent needs multi-step → run agent loop
  3. Execute steps sequentially with validation
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


async def _plan_steps(intent: str, params: Dict[str, Any], context: str) -> List[Dict[str, Any]]:
    """Use LLM to break down a complex request into validated steps."""
    system = """You are a task planner for Getszy platform.
Given a user intent and params, output a JSON array of steps.
Each step: {"action": "capability_id", "params": {...}, "validation": "check description"}

Available capabilities: create_product, update_product, list_products, create_course, etc.

RULES:
- Only use capabilities that exist
- Params must match the capability's required fields
- Include validation for each step
- Max 5 steps
- Output ONLY the JSON array, no prose"""

    user_msg = f"Intent: {intent}\nParams: {json.dumps(params)}\nContext: {context}"

    try:
        response = await chat_completion(user_msg, system, temperature=0.1)
        # Extract JSON from response
        if '```json' in response:
            response = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            response = response.split('```')[1].split('```')[0]
        steps = json.loads(response.strip())
        if isinstance(steps, list) and len(steps) <= 5:
            return steps
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f'Agent plan failed: {e}')

    # Fallback: single step
    return [{'action': intent, 'params': params, 'validation': 'basic'}]


async def _execute_step(step: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single step through the capability system."""
    from chat_builder.orchestrator import process_message

    action = step.get('action', '')
    params = step.get('params', {})

    # Validate action exists
    if action not in CAPABILITIES:
        return {'success': False, 'error': f'Unknown action: {action}'}

    # Check role permission
    from auth import role_level, ROLE_LEVEL
    needed = CAPABILITIES[action].get('min_role', 'customer')
    if role_level(user) < ROLE_LEVEL.get(needed, 1):
        return {'success': False, 'error': f'Requires {needed} role'}

    # Execute via orchestrator (reuses existing validation)
    try:
        # Create a virtual project for this agent run
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
        return step  # Return original on failure


async def run_agent_loop(
    intent: str,
    params: Dict[str, Any],
    user: Dict[str, Any],
    context: str = '',
    max_retries: int = 2,
) -> Dict[str, Any]:
    """Run multi-step agent loop with self-correction.

    Returns:
        {
            'steps_executed': int,
            'results': [...],
            'success': bool,
            'summary': str
        }
    """
    # Plan steps
    steps = await _plan_steps(intent, params, context)

    results = []
    for i, step in enumerate(steps):
        success = False
        last_error = ''

        for attempt in range(max_retries + 1):
            result = await _execute_step(step, user)
            if result.get('success'):
                success = True
                results.append(result)
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
        'summary': f'Successfully completed {len(steps)} step(s)',
    }
