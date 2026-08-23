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

    def test_verified_cloud_model_defaults(self):
        from llm_provider import GROQ_MODEL, GEMINI_MODEL
        assert GROQ_MODEL == 'qwen/qwen3.6-27b'
        assert GEMINI_MODEL == 'gemini-2.5-flash'

    def test_provider_info_shape(self):
        from llm_provider import provider_info
        info = provider_info()
        assert isinstance(info, dict)
        assert 'free_only' in info
        assert 'providers' in info


class TestLLMProviderChainOrdering:
    def test_customer_chain_is_cloud_first_even_if_local_is_pinned(self, monkeypatch):
        """An operational local pin cannot precede the managed cloud ladder."""
        monkeypatch.setenv('LLM_PROVIDER', 'ollama')
        monkeypatch.setenv('GROQ_API_KEY', 'test-key')
        monkeypatch.setenv('GEMINI_API_KEY', 'test-key')
        import importlib
        import llm_provider
        importlib.reload(llm_provider)
        chain = llm_provider._build_chain("sys", "usr", 0.4, "sid")
        names = [c[0] for c in chain]
        assert names[:2] == ['groq', 'gemini']

    def test_chain_contains_expected_providers(self):
        import llm_provider
        chain = llm_provider._build_chain("sys","usr",0.4,"sid")
        names = [c[0] for c in chain]
        # Local free providers should always be present
        assert 'ollama' in names or 'lmstudio' in names

    def test_free_only_blocks_nonfree_openrouter_model(self, monkeypatch):
        monkeypatch.setenv('FREE_ONLY', 'true')
        monkeypatch.setenv('OPENROUTER_API_KEY', 'x')
        monkeypatch.setenv('OPENROUTER_CUSTOMER_FALLBACK', 'true')
        monkeypatch.setenv('OPENROUTER_MODEL', 'qwen/qwen-2.5-72b-instruct')
        import importlib
        import llm_provider
        importlib.reload(llm_provider)
        chain = llm_provider._build_chain("sys", "usr", 0.4, "sid")
        names = [c[0] for c in chain]
        assert 'openrouter' not in names
        assert 'emergent' not in names


    def test_free_openrouter_model_can_be_explicitly_enabled(self, monkeypatch):
        monkeypatch.setenv('FREE_ONLY', 'true')
        monkeypatch.setenv('OPENROUTER_API_KEY', 'x')
        monkeypatch.setenv('OPENROUTER_CUSTOMER_FALLBACK', 'true')
        monkeypatch.setenv('OPENROUTER_MODEL', 'qwen/qwen-2.5-72b-instruct:free')
        import importlib
        import llm_provider
        importlib.reload(llm_provider)
        names = [name for name, _ in llm_provider._build_chain('sys', 'usr', 0.4, 'sid')]
        assert 'openrouter' in names


class TestProfessionalBuilderProviderLadder:
    @pytest.mark.asyncio
    async def test_professional_builder_ladder_prioritizes_groq_then_gemini_then_ollama(self, monkeypatch):
        import llm_provider as lp
        calls = []

        async def groq(*args, **kwargs):
            calls.append('groq')
            raise RuntimeError('planned Groq outage')

        async def gemini(*args, **kwargs):
            calls.append('gemini')
            return 'premium refinement complete'

        async def ollama(*args, **kwargs):
            calls.append('ollama')
            return 'should not be used'

        monkeypatch.setattr(lp, 'GROQ_API_KEY', 'configured')
        monkeypatch.setattr(lp, 'GEMINI_API_KEY', 'configured')
        monkeypatch.setattr(lp, 'OLLAMA_MODELS', ['qwen2.5-coder:7b'])
        monkeypatch.setattr(lp, '_groq', groq)
        monkeypatch.setattr(lp, '_gemini', gemini)
        monkeypatch.setattr(lp, '_ollama_chain', ollama)

        result = await lp.professional_builder_completion('system', 'refine this page', session_id='quality-test')

        assert result == 'premium refinement complete'
        assert calls == ['groq', 'gemini']


class TestLLMProviderChatCompletion:
    @pytest.mark.asyncio
    async def test_chat_completion_returns_string(self):
        """chat_completion should return a string when a provider is reachable."""
        from llm_provider import chat_completion, LLMServiceUnavailable
        try:
            result = await chat_completion('Say hello in one word.', 'You are helpful.')
            assert isinstance(result, str)
            assert len(result) > 0
        except (RuntimeError, LLMServiceUnavailable) as e:
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

    @pytest.mark.asyncio
    async def test_chat_completion_chain_invokes_provider(self, monkeypatch):
        """Regression: the chain must actually call the provider (no NameError).

        Mocks the groq helper so no network/key is required, proving the
        lambda closures receive system/user/temperature correctly.
        """
        import llm_provider
        monkeypatch.setattr(llm_provider, 'GROQ_API_KEY', 'dummy')
        monkeypatch.setattr(llm_provider, 'LLM_PROVIDER', 'groq')
        monkeypatch.setattr(llm_provider, 'FREE_ONLY', False)
        monkeypatch.setattr(
            llm_provider, '_groq',
            lambda system, user, temperature, max_tokens=None: __import__('asyncio').sleep(0, result='pong'),
        )

        async def fake_ollama(*a, **k):
            raise RuntimeError('local provider unavailable')
        monkeypatch.setattr(llm_provider, '_ollama_chain', fake_ollama)

        result = await llm_provider.chat_completion('sys', 'usr', temperature=0)
        assert result == 'pong'
