"""Tests for Auth endpoints (Signup, Login, Me).

Run with: python -m pytest tests/test_auth.py -v
"""
import pytest
import httpx
import os

BASE_URL = os.environ.get('TEST_API_URL', 'https://getszy.com/api')


@pytest.fixture
def client():
    with httpx.Client(base_url=BASE_URL, timeout=30) as c:
        yield c


@pytest.fixture
def test_user():
    """Create a test user and return credentials."""
    import uuid
    email = f'test_{uuid.uuid4().hex[:8]}@example.com'
    return {
        'name': 'Test User',
        'email': email,
        'password': 'TestPass123!',
    }


@pytest.mark.integration
class TestAuthSignup:
    def test_signup_success(self, client, test_user):
        """Valid signup should return token and user."""
        r = client.post('/auth/signup', json=test_user)
        assert r.status_code == 200
        data = r.json()
        assert 'token' in data
        assert data['user']['email'] == test_user['email']
        assert data['user']['role'] == 'customer'

    def test_signup_duplicate_email(self, client, test_user):
        """Duplicate email should return 400."""
        client.post('/auth/signup', json=test_user)
        r = client.post('/auth/signup', json=test_user)
        assert r.status_code == 400
        assert 'already registered' in r.json()['detail']

    def test_signup_weak_password(self, client, test_user):
        """Short password should return 400."""
        test_user['password'] = '123'
        r = client.post('/auth/signup', json=test_user)
        assert r.status_code == 400

    def test_signup_no_uppercase(self, client, test_user):
        """Password without uppercase should return 400."""
        test_user['password'] = 'alllowercase1'
        r = client.post('/auth/signup', json=test_user)
        assert r.status_code == 400

    def test_signup_invalid_email(self, client):
        """Invalid email should return 422."""
        r = client.post('/auth/signup', json={
            'name': 'Test', 'email': 'not-an-email', 'password': 'TestPass123!'
        })
        assert r.status_code == 422


@pytest.mark.integration
class TestAuthLogin:
    def test_login_success(self, client, test_user):
        """Valid login should return token."""
        client.post('/auth/signup', json=test_user)
        r = client.post('/auth/login', json={
            'email': test_user['email'],
            'password': test_user['password'],
        })
        assert r.status_code == 200
        assert 'token' in r.json()

    def test_login_wrong_password(self, client, test_user):
        """Wrong password should return 401."""
        client.post('/auth/signup', json=test_user)
        r = client.post('/auth/login', json={
            'email': test_user['email'],
            'password': 'WrongPassword123!',
        })
        assert r.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Non-existent email should return 401."""
        r = client.post('/auth/login', json={
            'email': 'noone@example.com',
            'password': 'TestPass123!',
        })
        assert r.status_code == 401


@pytest.mark.integration
class TestAuthMe:
    def test_me_with_token(self, client, test_user):
        """Valid token should return user profile."""
        client.post('/auth/signup', json=test_user)
        login = client.post('/auth/login', json={
            'email': test_user['email'],
            'password': test_user['password'],
        })
        token = login.json()['token']
        r = client.get('/auth/me', headers={'Authorization': f'Bearer {token}'})
        assert r.status_code == 200
        assert r.json()['email'] == test_user['email']

    def test_me_without_token(self, client):
        """No token should return 401."""
        r = client.get('/auth/me')
        assert r.status_code == 401

    def test_me_invalid_token(self, client):
        """Invalid token should return 401."""
        r = client.get('/auth/me', headers={'Authorization': 'Bearer invalidtoken123'})
        assert r.status_code == 401
