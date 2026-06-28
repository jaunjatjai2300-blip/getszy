# Getszy VPS Auto-Deploy Webhook Setup

This small companion service lets you trigger a full **`git pull && docker compose up -d --build`** on your VPS from the Phase 9 Deploy Dashboard's "Deploy to VPS" button.

Runs SEPARATELY from the main Getszy backend container so it can manage the parent compose stack.

## 1. Install dependencies (on VPS)

```bash
ssh root@31.97.237.222
pip3 install fastapi 'uvicorn[standard]'
```

## 2. Generate a secret token

```bash
openssl rand -hex 24
# Example output: 7a4c9f8b... (copy this)
```

Keep this **secret** - it's the only thing protecting deploys.

## 3. Install the systemd unit

```bash
cd /opt/getszy
# Edit the unit file - replace CHANGE_ME with the token above
nano deploy/getszy-webhook.service

sudo cp deploy/getszy-webhook.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now getszy-webhook
sudo systemctl status getszy-webhook
```

Should show `active (running)`. Verify:

```bash
curl http://localhost:9000/health
# {"ok": true, "service": "getszy-webhook", ...}
```

## 4. Expose via Caddy (HTTPS)

Edit `/opt/getszy/deploy/Caddyfile` and add a route inside your existing `getszy.com` block:

```
handle /hooks/deploy {
    reverse_proxy host.docker.internal:9000
}
```

(Or use the VPS IP if Caddy can't see `host.docker.internal`.)

Reload Caddy:

```bash
docker compose restart caddy
```

Test from anywhere:

```bash
curl -X POST -H "X-Token: <your-secret>" https://getszy.com/hooks/deploy
```

A successful response means the deploy ran.

## 5. Configure the main backend

Add to `docker-compose.yml` backend `environment:` block:

```yaml
DEPLOY_WEBHOOK_URL: "https://getszy.com/hooks/deploy"
DEPLOY_WEBHOOK_TOKEN: "<your-secret>"
```

Then `docker compose up -d backend`.

In the admin Deploy dashboard's `Deploy to VPS` button will now hit your listener.

---

## Optional: pull a better local code model

The Copilot + Code AI work best with a real coding LLM. If your VPS already runs Ollama and has 16 GB+ free RAM:

```bash
# On the VPS host (not inside the backend container):
ollama pull qwen2.5-coder:14b
# ~9 GB download, takes 10-20 min depending on bandwidth.

# Switch Getszy to use it:
# Edit docker-compose.yml backend environment block:
#   OLLAMA_MODEL: "qwen2.5-coder:14b"
docker compose restart backend
```

Revert by setting `OLLAMA_MODEL` back to `qwen2.5:7b`.
