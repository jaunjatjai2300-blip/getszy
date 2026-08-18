# Getszy — Load & Soak Testing (Phase 3: Performance & Load Validation)

Two interchangeable harnesses that fire **real** Getszy routes to validate
throughput, latency, and resource saturation before/after launch.

## 1. Self-contained harness (`load_test.py`)

```bash
pip install httpx
python load-tests/load_test.py \
    --url https://api.getszy.com \
    --users 50 --duration 60 --ramp 10 \
    --token <JWT>            # or --email/--password to auto-login
```

Flags: `--users` (concurrency), `--duration` (s), `--ramp` (s), `--token`,
`--email`/`--password`. Exits non-zero if the 5xx error rate exceeds 2% (CI gate).

Reported: throughput (req/s), p50/p95/p99 latency, per-route counts, error %.

## 2. Locust (`locustfile.py`)

```bash
pip install locust
locust -f load-tests/locustfile.py --headless -u 50 -r 10 -t 60s --host https://api.getszy.com
# optional auth: USER_EMAIL=... USER_PASSWORD=... locust ...
```

## Journeys exercised
| Weight | Route | Why |
|--------|-------|-----|
| 30 | `GET /api/health` | baseline liveness |
| 20 | `GET /api/` | catalog/browse |
| 25 | `POST /api/ai-tools/chat/completions` | **LLM stress** (watches `ollama_inference_failures_total`) |
| 10 | `POST /api/admin/chat` | admin AI path |
| 10 | `POST /api/video-factory/project` | **render queue** (watches `video_factory_jobs_*` + `VideoFactoryQueueStalled`) |

## Thresholds → alert mapping
- **Error rate > 2%** over 5m → `HighAPIErrorRate` (critical).
- **LLM failure rate > 0.05/s** → `OllamaInferenceFailureSpike`.
- **Pending video jobs > 10 with 0 completions / 10m** → `VideoFactoryQueueStalled`.
- **No backup in > 5h during/after soak** → `BackupStale` (RPO breach).

Run a soak (e.g. `--duration 1800`) and confirm Prometheus/Grafana while live to
catch CPU/memory saturation (`LowMemoryAvailable`, `HighCPUSaturation`).
