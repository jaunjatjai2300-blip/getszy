import pytest

pytest_plugins = []

@pytest.fixture(autouse=True)
def _anyio_backend():
    yield

# Reset the LLM provider's module-level usage counters (request + token budgets)
# between tests so the free-tier guard (which accumulates estimated tokens across
# calls) stays isolated and never appears exhausted within a suite run.
@pytest.fixture(autouse=True)
def _reset_llm_provider_state():
    import llm_provider as lp
    lp._counters.clear()
    lp._TOK_MIN.clear()
    lp._TOK_DAY.clear()
    yield
    lp._counters.clear()
    lp._TOK_MIN.clear()
    lp._TOK_DAY.clear()

# Allow plain async tests without explicit @pytest.mark.asyncio on every one
try:
    import pytest_asyncio  # noqa: F401
    pytest_asyncio_mode = 'auto'
except ImportError:
    pass
