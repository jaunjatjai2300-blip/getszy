import pytest

pytest_plugins = []

@pytest.fixture(autouse=True)
def _anyio_backend():
    yield

# Allow plain async tests without explicit @pytest.mark.asyncio on every one
try:
    import pytest_asyncio  # noqa: F401
    pytest_asyncio_mode = 'auto'
except ImportError:
    pass
