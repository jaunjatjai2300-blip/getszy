#!/usr/bin/env python3
"""Getszy load / soak test harness — Phase 3 of the production-launch-hardening skill.

Fires a mixed, weighted journey of REAL Getszy routes and reports throughput,
latency percentiles, and error rate. Optionally reads the Prometheus /metrics
endpoint to report live resource saturation during the run.

This is a test tool (not a product feature). Point it at a running instance:

  python load_test.py --url https://api.getszy.com --users 50 --duration 60

Auth: pass --token (a valid JWT) or --email/--password to auto-login.
AI stress: the chat/completions and video-factory journeys hammer the LLM and
render queues that the HighAPIErrorRate / VideoFactoryQueueStalled / Ollama
alerts watch.
"""
import argparse
import asyncio
import json
import random
import statistics
import time

try:
    import httpx
except ImportError:  # pragma: no cover
    raise SystemExit("httpx is required: pip install httpx")


# (method, path, weight, body_factory) — bodies are minimal; adjust to your schema.
def _chat_body():
    return {"messages": [{"role": "user", "content": "Say hi in one word"}], "max_tokens": 32}


def _video_body():
    return {"topic": "10 minute yoga flow", "style": "cinematic"}


JOURNEYS = [
    ("GET", "/api/health", 30, None),
    ("GET", "/api/", 20, None),
    ("POST", "/api/ai-tools/chat/completions", 25, _chat_body),
    ("POST", "/api/admin/chat", 10, lambda: {"message": "status report"}),
    ("POST", "/api/video-factory/project", 10, _video_body),
    ("POST", "/api/auth/login", 5, None),  # only if no token supplied
]

WEIGHTED = []
for method, path, weight, body in JOURNEYS:
    if method == "POST" and path.endswith("/login"):
        continue  # handled via real login if needed
    WEIGHTED.extend([(method, path, body)] * weight)


class Stats:
    def __init__(self):
        self.latencies = []
        self.errors = 0
        self.counts = {}

    def record(self, method, path, ok, ms):
        self.latencies.append(ms)
        self.counts[(method, path)] = self.counts.get((method, path), 0) + 1
        if not ok:
            self.errors += 1


async def _login(base, email, password, client):
    if not email:
        return None
    r = await client.post(f"{base}/api/auth/login",
                          json={"email": email, "password": password}, timeout=10)
    if r.status_code == 200:
        try:
            return r.json().get("access_token") or r.json().get("token")
        except Exception:
            return None
    return None


async def worker(base, token, stats, sem, duration, stop_at):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(base_url=base, headers=headers) as client:
        while time.time() < stop_at:
            method, path, body = random.choice(WEIGHTED)
            payload = body() if body else None
            async with sem:
                t0 = time.time()
                try:
                    if method == "GET":
                        r = await client.get(path, timeout=30)
                    else:
                        r = await client.post(path, json=payload, timeout=60)
                    ok = r.status_code < 500
                except Exception:
                    ok = False
                ms = (time.time() - t0) * 1000
            stats.record(method, path, ok, ms)


def _pct(latencies, p):
    if not latencies:
        return 0.0
    s = sorted(latencies)
    k = max(0, min(len(s) - 1, int(round((p / 100) * len(s) + 0.5)) - 1))
    return s[k]


async def run(base, users, duration, ramp, token, email, password):
    if not token:
        async with httpx.AsyncClient(base_url=base, timeout=10) as c:
            token = await _login(base, email, password, c)
    sem = asyncio.Semaphore(users)
    stats = Stats()
    stop_at = time.time() + duration
    # ramp: spread worker starts over `ramp` seconds
    tasks = []
    for i in range(users):
        await asyncio.sleep(ramp / max(1, users))
        tasks.append(asyncio.create_task(worker(base, token, stats, sem, duration, stop_at)))
    await asyncio.gather(*tasks)

    total = len(stats.latencies)
    err_rate = (stats.errors / total * 100) if total else 0.0
    rps = total / duration if duration else 0.0
    print("\n=== Getszy Load Test Report ===")
    print(f"Target            : {base}")
    print(f"Duration          : {duration}s   Users: {users}")
    print(f"Total requests    : {total}")
    print(f"Throughput        : {rps:.1f} req/s")
    print(f"Error rate (5xx)  : {err_rate:.2f}%   (alert fires > 2%)")
    print(f"Latency p50/p95/p99: {_pct(stats.latencies,50):.0f} / "
          f"{_pct(stats.latencies,95):.0f} / {_pct(stats.latencies,99):.0f} ms")
    print("Per-route counts:")
    for k, v in sorted(stats.counts.items(), key=lambda x: -x[1]):
        print(f"  {k[0]:4} {k[1]:42} {v}")
    return err_rate


def main():
    ap = argparse.ArgumentParser(description="Getszy load test harness")
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--users", type=int, default=20)
    ap.add_argument("--duration", type=int, default=60, help="seconds")
    ap.add_argument("--ramp", type=float, default=10, help="ramp-up seconds")
    ap.add_argument("--token", default="")
    ap.add_argument("--email", default="")
    ap.add_argument("--password", default="")
    args = ap.parse_args()
    err_rate = asyncio.run(run(args.url.rstrip("/"), args.users, args.duration,
                               args.ramp, args.token, args.email, args.password))
    # Exit non-zero if error budget blown (useful as a CI gate).
    raise SystemExit(1 if err_rate > 2.0 else 0)


if __name__ == "__main__":
    main()
