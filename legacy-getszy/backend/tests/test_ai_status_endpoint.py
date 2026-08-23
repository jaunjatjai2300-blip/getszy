"""Customer-facing AI health surface — supports the dashboard badge and live
provider-failure monitoring. The endpoint is cheap (no DB, no per-call LLM)."""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('MONGO_URL', 'mongodb://127.0.0.1:27017')
os.environ.setdefault('JWT_SECRET', 'test-only-ai-status-secret')

import routes_builder as rb


@pytest.mark.asyncio
async def test_ai_status_surface_is_usable():
    """The public health surface must report usable providers and a valid mode."""
    status = await rb.ai_status()
    assert isinstance(status['healthy'], bool)
    assert status['mode'] in ('free', 'standard')
    assert isinstance(status['providers'], list)
    # If healthy, the chain must list at least one provider (never silently dead).
    if status['healthy']:
        assert status['active_chain']
        assert status['providers']
