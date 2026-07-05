"""YAML Campaign Stacks - executor and parser.

A stack is a YAML document describing an end-to-end campaign:

  name: "Diwali Sale 2026"
  audience: ["women", "girls"]
  steps:
    - skill: scan_trending
      params: { count: 10 }
    - skill: import_trending
      params: { count: 5, min_score: 80 }
    - skill: generate_logo
      params: { brand: "Diwali Sale" }

Each step references a skill from skills.registry. Steps run sequentially
and pass their result to ctx.previous so later steps can reference outputs.
"""
import yaml
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from skills.registry import registry


def parse(yaml_text: str) -> Dict[str, Any]:
    try:
        data = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise ValueError(f'Invalid YAML: {e}')
    if not isinstance(data, dict):
        raise ValueError('Stack must be a YAML object')
    if 'name' not in data:
        raise ValueError("Stack is missing required field 'name'")
    steps = data.get('steps') or []
    if not isinstance(steps, list):
        raise ValueError("'steps' must be a list")
    for i, step in enumerate(steps):
        if not isinstance(step, dict) or 'skill' not in step:
            raise ValueError(f'Step #{i+1} must have a `skill` key')
        if registry.get(step['skill']) is None:
            raise ValueError(f'Unknown skill in step #{i+1}: {step["skill"]}')
    return data


async def execute(stack_doc: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    ctx: Dict[str, Any] = {'user_id': user.get('id'), 'previous': None, 'outputs': {}}
    results: List[Dict[str, Any]] = []
    overall_ok = True

    for i, step in enumerate(stack_doc.get('steps', []) or []):
        skill_name = step['skill']
        params = step.get('params', {}) or {}
        skill = registry.get(skill_name)
        entry: Dict[str, Any] = {'index': i, 'skill': skill_name, 'params': params, 'started_at': datetime.now(timezone.utc).isoformat()}
        try:
            result = await skill.run(params, ctx)
            entry['status'] = 'ok'
            entry['result'] = result
            ctx['previous'] = result
            ctx['outputs'][skill_name] = result
        except Exception as e:
            entry['status'] = 'error'
            entry['error'] = str(e)
            overall_ok = False
        entry['ended_at'] = datetime.now(timezone.utc).isoformat()
        results.append(entry)

    return {
        'run_id': run_id,
        'stack_name': stack_doc.get('name'),
        'started_at': started_at,
        'ended_at': datetime.now(timezone.utc).isoformat(),
        'overall_status': 'ok' if overall_ok else 'partial',
        'steps': results,
    }
