"""Authenticated Locust smoke/load workload for Getszy.

Example (use a dedicated, funded staging test account; never a production owner):
  USER_EMAIL=loadtest@example.invalid USER_PASSWORD='...' \
  locust -f load-tests/locustfile.py --headless --host https://staging.example.com -u 50 -r 10 -t 5m

Alternatively set LOAD_TEST_TOKEN to a short-lived staging bearer token. Without
one of these credentials, protected workloads are skipped rather than recording
misleading 401 responses as application performance.
"""
import os

try:
    from locust import HttpUser, between, task
except ImportError:  # pragma: no cover
    raise SystemExit("locust is required: pip install locust")


class GetszyUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        self.auth_headers = {}
        supplied_token = os.environ.get("LOAD_TEST_TOKEN", "").strip()
        if supplied_token:
            self.auth_headers = {"Authorization": f"Bearer {supplied_token}"}
            return

        email = os.environ.get("USER_EMAIL", "").strip()
        password = os.environ.get("USER_PASSWORD", "")
        if not email or not password:
            return
        with self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            timeout=10,
            name="/api/auth/login",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"login failed: HTTP {response.status_code}")
                return
            token = response.json().get("access_token") or response.json().get("token")
            if not token:
                response.failure("login response has no access token")
                return
            self.auth_headers = {"Authorization": f"Bearer {token}"}

    @task(30)
    def health(self):
        self.client.get("/api/health", name="/api/health")

    @task(20)
    def root(self):
        self.client.get("/api/", name="/api/")

    @task(25)
    def ai_chat(self):
        if not self.auth_headers:
            return
        self.client.post(
            "/api/ai-tools/chat/completions",
            headers=self.auth_headers,
            json={"messages": [{"role": "user", "content": "Load-test health check: reply briefly."}], "max_tokens": 32},
            timeout=60,
            name="/api/ai-tools/chat/completions",
        )

    @task(10)
    def video_project(self):
        if not self.auth_headers:
            return
        # auto_run=False avoids triggering paid AI rendering during a normal web
        # workload. Dedicated AI stress scenarios must explicitly enable it.
        self.client.post(
            "/api/video-factory/project",
            headers=self.auth_headers,
            json={"prompt": "A short staging product demo for load validation.", "language": "hinglish", "fast": True, "auto_run": False},
            timeout=30,
            name="/api/video-factory/project",
        )

    @task(5)
    def list_video_projects(self):
        if not self.auth_headers:
            return
        self.client.get(
            "/api/video-factory/projects",
            headers=self.auth_headers,
            timeout=15,
            name="/api/video-factory/projects",
        )
