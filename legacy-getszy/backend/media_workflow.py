"""Vibe-Workflow engine - server-side JSON-DAG executor for media pipelines.

A workflow is a JSON graph:
    {
      "nodes": [
        {"id": "art", "type": "image", "params": {"prompt": "a calm landscape", "model": "FLUX.1-schnell"}},
        {"id": "voice", "type": "tts", "params": {"text": "welcome", "voice": "en-US-AriaNeural"}}
      ],
      "edges": [{"from": "art", "to": "voice", "as": "image"}]
    }

Nodes run in topological order; an edge feeds a predecessor's output into the
successor's ``inputs`` under the edge's ``as`` name (default ``input``). This is
the backend for the Vibe-Workflow canvas (the drag-and-drop UI is a later phase;
the executor + status polling are live now).
"""
import logging
from typing import Dict, Any, List, Callable, Awaitable, Optional

logger = logging.getLogger('getszy.media_workflow')

# Node runners are resolved lazily so this module imports with no heavy deps.
_RUNNERS: Dict[str, Callable[..., Awaitable[Any]]] = {}

# Public list of supported node types (used for request validation).
KNOWN_NODE_TYPES = ('image', 'tts', 'text', 'delay', 'shorts')


def _runner(type_name: str):
    async def image(inputs, params):
        from media_models import generate_image_model
        return await generate_image_model(
            params.get('prompt', ''), params.get('model'),
            int(params.get('width', 1024)), int(params.get('height', 1024)),
        )

    async def tts(inputs, params):
        from media_models import text_to_speech
        return await text_to_speech(params.get('text', ''), params.get('voice'), params.get('rate'), params.get('pitch'))

    async def text_node(inputs, params):
        return {'text': params.get('value', '')}

    async def delay(inputs, params):
        import asyncio
        await asyncio.sleep(float(params.get('seconds', 0)))
        return {'slept': True}

    async def shorts(inputs, params):
        from media_shorts import run_shorts
        src = inputs.get('input') or params.get('source')
        return await run_shorts(src, params)

    table = {
        'image': image, 'tts': tts, 'text': text_node, 'delay': delay, 'shorts': shorts,
    }
    return table.get(type_name)


def topo_sort(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[str]:
    """Return node ids in dependency order. Raises ValueError on a cycle."""
    by_id = {n['id']: n for n in nodes}
    indeg = {n['id']: 0 for n in nodes}
    adj: Dict[str, List[str]] = {n['id']: [] for n in nodes}
    for e in edges:
        f, t = e['from'], e['to']
        if f not in by_id or t not in by_id:
            raise ValueError(f'edge references unknown node: {e}')
        adj[f].append(t)
        indeg[t] += 1
    queue = [nid for nid, d in indeg.items() if d == 0]
    order: List[str] = []
    while queue:
        nid = queue.pop(0)
        order.append(nid)
        for nxt in adj[nid]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(nodes):
        raise ValueError('workflow graph contains a cycle')
    return order


async def run_graph(graph: Dict[str, Any], runner_overrides: Optional[Dict[str, Callable]] = None) -> Dict[str, Any]:
    """Execute a workflow graph and return a mapping of node id -> output."""
    nodes = graph.get('nodes', [])
    edges = graph.get('edges', [])
    order = topo_sort(nodes, edges)
    outputs: Dict[str, Any] = {}
    incoming: Dict[str, Dict[str, str]] = {n['id']: {} for n in nodes}
    for e in edges:
        name = e.get('as', 'input')
        incoming[e['to']][name] = e['from']
    for nid in order:
        node = next(n for n in nodes if n['id'] == nid)
        inputs = {name: outputs[src] for name, src in incoming[nid].items()}
        runner = (runner_overrides or {}).get(node['type']) or _runner(node['type'])
        if runner is None:
            raise ValueError(f'unsupported node type: {node["type"]}')
        outputs[nid] = await runner(inputs, node.get('params', {}) or {})
    return outputs
