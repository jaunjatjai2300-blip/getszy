"""Basic API tests for getszy backend."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# ===== Auth Tests =====
class TestAuth:
    def test_jwt_secret_required(self):
        """JWT_SECRET must be set in env."""
        import os
        with patch.dict(os.environ, {}, clear=True):
            # Remove JWT_SECRET if present
            os.environ.pop('JWT_SECRET', None)
            with pytest.raises(RuntimeError, match='JWT_SECRET'):
                # Re-import to trigger the check
                import importlib
                import auth
                importlib.reload(auth)

    def test_hash_password(self):
        from auth import hash_password, verify_password
        hashed = hash_password('test123')
        assert hashed != 'test123'
        assert verify_password('test123', hashed)
        assert not verify_password('wrong', hashed)


# ===== Subscription Tests =====
class TestSubscription:
    def test_pricing_set(self):
        from subscription import PRICING
        pro = next(p for p in PRICING if p['id'] == 'pro')
        elite = next(p for p in PRICING if p['id'] == 'elite')
        assert pro['price_monthly'] == 799
        assert elite['price_monthly'] == 1999

    def test_plan_features(self):
        from subscription import plan_features
        free = plan_features('free')
        pro = plan_features('pro')
        elite = plan_features('elite')
        assert free['studio_builds'] == 0
        assert pro['studio_builds'] == 10
        assert elite['studio_builds'] == 9999
        assert free['advanced_courses'] is False
        assert pro['advanced_courses'] is True


# ===== Builder Sanitizer Tests =====
class TestBuilderSanitize:
    def test_strip_script_tags(self):
        from routes_builder import _sanitize
        html = '<p>Hello</p><script>alert("xss")</script><p>World</p>'
        result = _sanitize(html)
        assert '<script>' not in result
        assert 'Hello' in result
        assert 'World' in result

    def test_strip_event_handlers(self):
        from routes_builder import _sanitize
        html = '<img src="x" onerror="alert(1)">'
        result = _sanitize(html)
        assert 'onerror' not in result

    def test_strip_iframe(self):
        from routes_builder import _sanitize
        html = '<iframe src="evil.com"></iframe><p>Safe</p>'
        result = _sanitize(html)
        assert '<iframe' not in result
        assert 'Safe' in result

    def test_strip_javascript_uri(self):
        from routes_builder import _sanitize
        html = '<a href="javascript:alert(1)">Click</a>'
        result = _sanitize(html)
        assert 'javascript:' not in result

    def test_keep_safe_html(self):
        from routes_builder import _sanitize
        html = '<div class="container"><h1>Title</h1><p>Content</p></div>'
        result = _sanitize(html)
        assert '<div' in result
        assert '<h1>' in result
        assert '<p>' in result


# ===== Provider Tests =====
class TestProviders:
    def test_pollinations_always_available(self):
        from creator.providers import active_provider
        result = active_provider('image')
        assert result['name'] == 'pollinations'
        assert result['status'] == 'live'

    def test_pending_provider_has_guide(self):
        from creator.providers import active_provider
        with patch.dict('os.environ', {}, clear=True):
            import os
            os.environ.pop('FAL_KEY', None)
            os.environ.pop('HF_TOKEN', None)
            os.environ.pop('REPLICATE_TOKEN', None)
            os.environ.pop('GPU_HOST', None)
            result = active_provider('video')
            assert result['status'] == 'pending_provider'
            assert 'setup_guide' in result


# ===== Builder Extract HTML Tests =====
class TestExtractHtml:
    def test_extract_from_markdown(self):
        from routes_builder import _extract_html
        raw = '```html\n<!DOCTYPE html><html><head></head><body><p>Hi</p></body></html>\n```'
        result = _extract_html(raw)
        assert result.startswith('<!DOCTYPE html')
        assert '</html>' in result

    def test_extract_bare_html(self):
        from routes_builder import _extract_html
        raw = '<html><head></head><body><p>Hi</p></body></html>'
        result = _extract_html(raw)
        assert '<!DOCTYPE html>' in result
        assert '</html>' in result
