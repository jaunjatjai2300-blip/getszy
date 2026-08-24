import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:27017')
os.environ.setdefault('JWT_SECRET', 'test-only-reliability-secret')

import auth
import routes_builder as builder_routes
from models import BuilderProjectIn, BuilderRefineIn
from fastapi import HTTPException


class _Projects:
    def __init__(self):
        self.items = {}

    async def find_one(self, query, projection=None):
        item = self.items.get(query.get('id'))
        if not item or any(item.get(k) != v for k, v in query.items() if k != '_id'):
            return None
        if not projection:
            return dict(item)
        return {k: v for k, v in item.items() if projection.get(k, 1)}

    async def update_one(self, query, update, upsert=False):
        pid = query.get('id')
        if '$setOnInsert' in update:
            self.items.setdefault(pid, dict(update['$setOnInsert']))
        if '$set' in update:
            self.items.setdefault(pid, {}).update(update['$set'])


class _DB:
    def __init__(self):
        self.builder_projects = _Projects()


@pytest.fixture(autouse=True)
def isolated_builder_db(monkeypatch):
    monkeypatch.setattr(builder_routes, 'db', _DB())


# ---------------------------------------------------------------------------
# #2 sanitizer: must keep the trusted Tailwind CDN script but strip vectors.
# ---------------------------------------------------------------------------
def test_sanitize_keeps_tailwind_and_strips_dangerous():
    html = (
        '<script>alert(1)</script>'
        '<script src="https://cdn.tailwindcss.com"></script>'
        '<iframe src="evil.example"></iframe>'
        '<object data="x"></object>'
        '<img src="x" onerror="alert(2)">'
        '<a href="javascript:alert(3)">x</a>'
        '<div style="background:url(javascript:alert(4))">'
    )
    out = builder_routes._sanitize(html)
    assert 'cdn.tailwindcss.com' in out, 'Tailwind CDN script must be preserved for styling'
    assert '<script>alert' not in out, 'inline scripts must be removed'
    assert '<iframe' not in out
    assert '<object' not in out
    assert 'onerror=' not in out
    assert 'javascript:alert' not in out


def test_sanitize_keeps_tailwind_with_versioned_path():
    out = builder_routes._sanitize('<script src="https://cdn.tailwindcss.com/3.4.0"></script>')
    assert 'cdn.tailwindcss.com/3.4.0' in out


# ---------------------------------------------------------------------------
# #1 preview CSP: sandbox the iframe yet allow the Tailwind CDN + fonts.
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_preview_csp_sandboxes_but_allows_tailwind_and_fonts():
    builder_routes.db.builder_projects.items['project-a'] = {
        'id': 'project-a', 'user_id': 'user-a', 'html_content': '<!DOCTYPE html><h1>A</h1>',
    }
    token = (await builder_routes.issue_preview_token('project-a', user={'id': 'user-a'}))['token']
    resp = await builder_routes.preview_project('project-a', token=token)
    csp = resp.headers['content-security-policy']
    assert 'sandbox allow-scripts' in csp, 'preview must remain sandboxed'
    assert 'script-src https://cdn.tailwindcss.com' in csp, 'Tailwind CDN must be executable for styling'
    assert "script-src 'unsafe-inline'" not in csp, 'inline scripts must stay blocked'
    assert 'connect-src' in csp


# ---------------------------------------------------------------------------
# #3 build_stream: must persist the generated project (no lost work / leak).
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_build_stream_persists_project_and_is_idempotent(monkeypatch):
    captured = {}

    async def fake_deduct(user_id, action, **kwargs):
        captured['deduct_calls'] = captured.get('deduct_calls', 0) + 1
        captured['ref_id'] = kwargs.get('ref_id')
        return (True, 'ok', 100)

    async def fake_refund(user_id, action, **kwargs):
        captured['refund_calls'] = captured.get('refund_calls', 0) + 1
        return (True, 'ok', 99)

    async def fake_stream(prompt, session_id):
        html = (
            '<script>alert(1)</script>'
            '<script src="https://cdn.tailwindcss.com"></script>'
            '<h1>Hi</h1>'
        )
        yield "event: step\ndata: {\"name\":\"planner\",\"status\":\"done\"}\n\n"
        yield "event: complete\ndata: " + json.dumps({'html': html}) + "\n\n"

    monkeypatch.setattr(builder_routes, 'deduct', fake_deduct)
    monkeypatch.setattr(builder_routes, 'refund', fake_refund)
    monkeypatch.setattr(builder_routes, '_stream_build_steps', fake_stream)

    resp = await builder_routes.build_stream(BuilderProjectIn(prompt='a coffee shop'), user={'id': 'user-a'})
    # Consume the SSE stream so the finally-block persists the result.
    async for _ in resp.body_iterator:
        pass

    saved = list(builder_routes.db.builder_projects.items.values())
    assert len(saved) == 1, 'a project must be persisted'
    proj = saved[0]
    assert 'cdn.tailwindcss.com' in proj['html_content'], 'stored HTML keeps styling'
    assert '<script>alert' not in proj['html_content'], 'stored HTML is sanitized'
    # The debit used the persisted project id as its idempotency key.
    assert captured['deduct_calls'] == 1
    assert captured['ref_id'] == proj['id']
    assert captured.get('refund_calls', 0) == 0


@pytest.mark.asyncio
async def test_build_stream_refunds_on_generation_failure(monkeypatch):
    captured = {}

    async def fake_deduct(user_id, action, **kwargs):
        captured['ref_id'] = kwargs.get('ref_id')
        return (True, 'ok', 100)

    async def fake_refund(user_id, action, **kwargs):
        captured['refund_ref_id'] = kwargs.get('ref_id')
        return (True, 'ok', 99)

    async def fake_stream(prompt, session_id):
        raise RuntimeError('llm down')

    monkeypatch.setattr(builder_routes, 'deduct', fake_deduct)
    monkeypatch.setattr(builder_routes, 'refund', fake_refund)
    monkeypatch.setattr(builder_routes, '_stream_build_steps', fake_stream)

    resp = await builder_routes.build_stream(BuilderProjectIn(prompt='a coffee shop'), user={'id': 'user-a'})
    async for _ in resp.body_iterator:
        pass

    assert captured.get('refund_ref_id') == captured.get('ref_id'), 'refund reuses the same idempotency key'


# ---------------------------------------------------------------------------
# #4 refine idempotency: debit and refund share the same stable ref id.
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_refine_deduct_and_refund_share_same_ref_id(monkeypatch):
    calls = {}

    async def fake_deduct(user_id, action, **kwargs):
        calls['deduct_ref_id'] = kwargs.get('ref_id')
        return (True, 'ok', 100)

    async def fake_generate(*a, **k):
        return '<h1>refined</h1>'

    async def fake_refund(user_id, action, **kwargs):
        calls['refund_ref_id'] = kwargs.get('ref_id')
        return (True, 'ok', 99)

    monkeypatch.setattr(builder_routes, 'deduct', fake_deduct)
    monkeypatch.setattr(builder_routes, '_generate_site', fake_generate)
    monkeypatch.setattr(builder_routes, 'refund', fake_refund)
    builder_routes.db.builder_projects.items['p1'] = {
        'id': 'p1', 'user_id': 'user-a', 'html_content': '<h1>x</h1>',
    }

    await builder_routes.refine_project('p1', BuilderRefineIn(prompt='make it blue'), user={'id': 'user-a'})
    assert calls['deduct_ref_id'] == 'refine:p1'


@pytest.mark.asyncio
async def test_refine_refund_uses_same_ref_id_on_failure(monkeypatch):
    calls = {}

    async def fake_deduct(user_id, action, **kwargs):
        calls['deduct_ref_id'] = kwargs.get('ref_id')
        return (True, 'ok', 100)

    async def fake_generate_fail(*a, **k):
        raise RuntimeError('boom')

    async def fake_refund(user_id, action, **kwargs):
        calls['refund_ref_id'] = kwargs.get('ref_id')
        return (True, 'ok', 99)

    monkeypatch.setattr(builder_routes, 'deduct', fake_deduct)
    monkeypatch.setattr(builder_routes, '_generate_site', fake_generate_fail)
    monkeypatch.setattr(builder_routes, 'refund', fake_refund)
    builder_routes.db.builder_projects.items['p1'] = {
        'id': 'p1', 'user_id': 'user-a', 'html_content': '<h1>x</h1>',
    }

    with pytest.raises(HTTPException) as exc:
        await builder_routes.refine_project('p1', BuilderRefineIn(prompt='x'), user={'id': 'user-a'})
    assert exc.value.status_code == 503
    assert calls['refund_ref_id'] == 'refine:p1' == calls['deduct_ref_id']


@pytest.mark.asyncio
async def test_refine_element_deduct_uses_element_scoped_ref_id(monkeypatch):
    calls = {}

    async def fake_deduct(user_id, action, **kwargs):
        calls['deduct_ref_id'] = kwargs.get('ref_id')
        return (True, 'ok', 100)

    async def fake_element(*a, **k):
        return '<h1>el</h1>'

    monkeypatch.setattr(builder_routes, 'deduct', fake_deduct)
    monkeypatch.setattr(builder_routes, 'refine_element', fake_element)
    builder_routes.db.builder_projects.items['p1'] = {
        'id': 'p1', 'user_id': 'user-a', 'html_content': '<h1>x</h1>',
    }

    await builder_routes.refine_project_element('p1', {'selector': '#hero', 'instruction': 'bluer'}, user={'id': 'user-a'})
    assert calls['deduct_ref_id'] == 'refine-elem:p1:#hero'


# ---------------------------------------------------------------------------
# #5 review gate: pages that pass all required checks are reviewable.
# ---------------------------------------------------------------------------
def _good_page():
    return (
        '<!DOCTYPE html><html><head>'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Coffee Shop</title>'
        '<meta name="description" content="Best coffee">'
        '</head><body>'
        '<header><h1>Fresh Coffee Daily</h1></header>'
        '<main><section><img src="hero.jpg" alt="Freshly brewed coffee"></section>'
        '<section><a href="#order">Order now</a></section></main>'
        '<footer>Visit us</footer>'
        '<style>@media (min-width: 640px){.x{color:red}}</style>'
        '</body></html>'
    )


def test_review_gate_ready_when_required_checks_pass():
    from builder_quality import evaluate_landing_page_quality
    report = evaluate_landing_page_quality(_good_page())
    assert report['status'] == 'ready_for_human_review'


def test_review_gate_needs_work_when_required_check_fails():
    from builder_quality import evaluate_landing_page_quality
    # Missing the required H1 and semantic landmarks.
    bad = '<!DOCTYPE html><html><head></head><body><p>hi</p></body></html>'
    report = evaluate_landing_page_quality(bad)
    assert report['status'] == 'needs_work'
