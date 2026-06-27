# Deploying getszy.com to your VPS

## VPS Requirements
- AlmaLinux 9 (or Rocky / CentOS 9 / Ubuntu 22.04 — minor tweaks)
- 8 vCPU · 32 GB RAM · 100 GB+ NVMe (matches your VPS)
- Public IP + domain DNS access

## Stack
- **Caddy** — reverse proxy + auto Let's Encrypt SSL
- **Mongo 7** — database (Docker volume persistent)
- **FastAPI backend** — Dockerized
- **React frontend** — Built static + Nginx (Dockerized)
- **Ollama** — native install on host, port 11434 (for future VPS LLM swap)

## Network Flow
```
[Internet] → Caddy:443 (SSL termination)
            ├─→ /api/* → backend:8001
            └─→ / → frontend:80 (nginx → React build)

backend → mongo:27017
backend → host.docker.internal:11434 (Ollama, when LLM_PROVIDER=ollama)
```

## One-shot setup
See `deploy/setup-vps.sh` for a single bootstrap script.

## DNS
At your domain registrar / Cloudflare, add:
- `A` record  `getszy.com`  → `31.97.237.222`
- `A` record  `www.getszy.com`  → `31.97.237.222`

Caddy will fetch SSL certs automatically once DNS resolves.

## Switch to local VPS LLM (free, no Emergent credits used)
When Ollama is healthy on the host:
```bash
# In /opt/getszy/.env
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5:7b
```
Then: `docker compose up -d --force-recreate backend`

## Updating the app
```bash
cd /opt/getszy
git pull
docker compose up -d --build
```

## Backups
- Mongo data lives in the `mongo_data` Docker volume.
- Snapshot weekly: `docker run --rm -v getszy_mongo_data:/data -v $(pwd):/b alpine tar czf /b/mongo-backup-$(date +%F).tgz /data`
