# Getszy

**AI-powered business-builder platform** — e-commerce storefront + AI academy +
AI video/media factory + website builder, running as a single FastAPI + React
monorepo under [`legacy-getszy/`](legacy-getszy/).

## Architecture

| Layer    | Stack                                                                      |
| -------- | -------------------------------------------------------------------------- |
| Backend  | FastAPI + Motor (async MongoDB, replica set) + Redis + Prometheus metrics  |
| Frontend | React 19 + Vite + Radix UI + Tailwind CSS + react-query / SWR              |
| Auth     | bcrypt + HS256 JWT (Redis `jti` revocation), roles: visitor/customer/admin |
| AI       | Multi-provider fallback chain: Groq, Gemini, OpenRouter, Ollama, LM Studio |
| Media    | FFmpeg video pipeline, TTS, image generation, stock-photo sourcing         |
| Payments | Razorpay subscriptions, credits, referrals                                 |
| Deploy   | Docker Compose (Mongo, Redis, Backend, Frontend, Caddy auto-TLS) + VPS     |

```
legacy-getszy/
├── backend/          FastAPI app (server.py entry; 70+ route modules)
├── frontend/         React 19 + Vite SPA (src/, public assets)
├── deploy/           Caddyfile + nginx-spa.conf
├── docker-compose.yml
├── Dockerfile.backend / Dockerfile.frontend
└── docs/tests/monitoring/
```

## Local development

```bash
# backend
cd legacy-getszy/backend
pip install -r requirements.txt
python -m uvicorn server:app --reload --port 8000

# frontend (Vite dev server on :3000, /api proxied to :8000)
cd legacy-getszy/frontend
yarn install
yarn dev
```

Copy `legacy-getszy/.env.example` to `legacy-getszy/.env` and fill in real
values (`JWT_SECRET` and `INTEGRATION_ENCRYPTION_KEY` are validated at startup —
placeholders are rejected).

## Frontend commands

| Command          | Purpose                                |
| ---------------- | -------------------------------------- |
| `yarn dev`       | Vite dev server (port 3000)            |
| `yarn build`     | Production build → `dist/`             |
| `yarn preview`   | Serve the production build locally     |
| `yarn test`      | Vitest unit tests                      |

Environment variables are **Vite-prefixed** (`VITE_BACKEND_URL`,
`VITE_SENTRY_DSN`, `VITE_SENTRY_ENV`) and imported via
`import.meta.env.VITE_*`.

## Deployment

- CI/CD: `.github/workflows/ci.yml` — pytest (against a live local server),
  Bandit + Safety security scans, Vite build, then a **blocking** deploy job
  that calls the VPS webhook and verifies `/api/health` before going green.
- VPS: `bash deploy-vps.sh` (pulls latest, rebuilds Compose stack, waits for
  health, verifies Ollama connectivity).
- Local ops: `make up / down / logs / health` (see `Makefile`).

## Security notes

- All secrets are env-driven; `.env` is gitignored and never committed.
- `/metrics` and API docs are blocked at the Caddy edge (public domain).
- Runtime media (generated videos/audio, sourced stock photos) lives in Docker
  volumes / gitignored directories — never committed to git.
- See `AUDIT_REPORT.md`, `SECURITY_FINDING_RECORD.md` and `PURGE_SECRETS.md`
  for the security-review history.

## License

MIT — see [LICENSE](LICENSE).
