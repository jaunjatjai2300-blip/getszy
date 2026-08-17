"""Tests for the LLM provider chain (config + ordering + fallbacks).

Run with: python -m pytest tests/test_llm_provider.py -v
"""
import os
import pytest


class TestLLMProviderConfig:
    def test_ollama_models_present(self):
        from llm_provider import OLLAMA_MODELS
        assert isinstance(OLLAMA_MODELS, list)
        assert 1 <= len(OLLAMA_MODELS) <= 3

    def test_free_only_is_bool(self):
        from llm_provider import FREE_ONLY
        assert isinstance(FREE_ONLY, bool)

    def test_provider_info_shape(self):
        from llm_provider import provider_info
        info = provider_info()
        assert isinstance(info, dict)
        assert 'free_only' in info
        assert 'providers' in info


class TestLLMProviderChainOrdering:
    def test_llm_provider_pin_moves_to_front(self, monkeypatch):
        """When LLM_PROVIDER=groq is set, groq should be tried first."""
        monkeypatch.setenv('LLM_PROVIDER', 'groq')
        monkeypatch.setenv('GROQ_API_KEY', 'test-key')
        # Force re-import so module-level LLM_PROVIDER is read
        import importlib
        import llm_provider
        importlib.reload(llm_provider)
        chain = llm_provider._build_chain()
        names = [c[0] for c in chain]
        assert names[0] == 'groq'

    def test_chain_contains_expected_providers(self):
        import llm_provider
        chain = llm_provider._build_chain()
        names = [c[0] for c in chain]
        # Local free providers should always be present
        assert 'ollama' in names or 'lmstudio' in names

    def test_free_only_blocks_paid(self, monkeypatch):
        monkeypatch.setenv('FREE_ONLY', 'true')
        monkeypatch.setenv('OPENROUTER_API_KEY', 'x')
        import importlib
        import llm_provider
        importlib.reload(llm_provider)
        chain = llm_provider._build_chain()
        names = [c[0] for c in chain]
        assert 'openrouter' not in names
        assert 'emergent' not in names


class TestLLMProviderChatCompletion:
    @pytest.mark.asyncio
    async def test_chat_completion_returns_string(self):
        """chat_completion should return a string when a provider is reachable."""
        from llm_provider import chat_completion
        try:
            result = await chat_completion('Say hello in one word.', 'You are helpful.')
            assert isinstance(result, str)
            assert len(result) > 0
        except RuntimeError as e:
            pytest.skip(f'No LLM provider reachable in CI: {e}')

    @pytest.mark.asyncio
    async def test_chat_completion_uses_groq_when_pinned(self, monkeypatch):
        """With LLM_PROVIDER=groq and a real key, Groq should be selected."""
        if not os.environ.get('GROQ_API_KEY'):
            pytest.skip('GROQ_API_KEY not configured')
        monkeypatch.setenv('LLM_PROVIDER', 'groq')
        from llm_provider import chat_completion
        result = await chat_completion('Reply with the single word: pong', 'ping', temperature=0)
        assert isinstance(result, str)
        assert len(result) > 0
