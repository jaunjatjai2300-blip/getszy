"""Locust load test for Getszy — run with:  locust -f locustfile.py --headless -u 50 -r 10 -t 60s

Hits the same real routes as load_test.py. Set HOST env or pass --host.
"""
import random

try:
    from locust import HttpUser, task, between
except ImportError:  # pragma: no cover
    raise SystemExit("locust is required: pip install locust")


class GetszyUser(HttpUser):
    wait_time = between(0.5, 2.0)
    token = None

    def on_start(self):
        # Optional auto-login; set USER_EMAIL/USER_PASSWORD env if you want auth.
        import os
        email = os.environ.get("USER_EMAIL")
        pw = os.environ.get("USER_PASSWORD")
        if email:
            r = self.client.post("/api/auth/login",
                                 json={"email": email, "password": pw}, timeout=10)
            if r.status_code == 200:
                GetszyUser.token = r.json().get("access_token") or r.json().get("token")

    @task(30)
    def health(self):
        self.client.get("/api/health")

    @task(20)
    def root(self):
        self.client.get("/api/")

    @task(25)
    def ai_chat(self):
        self.client.post("/api/ai-tools/chat/completions",
                         json={"messages": [{"role": "user", "content": "hi"}],
                               "max_tokens": 32},
                         timeout=60)

    @task(10)
    def admin_chat(self):
        self.client.post("/api/admin/chat",
                         json={"message": "status"}, timeout=60)

    @task(10)
    def video_project(self):
        self.client.post("/api/video-factory/project",
                         json={"topic": "quick demo", "style": "cinematic"}, timeout=120)

    def on_stop(self):
        GetszyUser.token = None
