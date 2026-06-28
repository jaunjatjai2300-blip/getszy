# Getszy VPS Auto-Deploy Webhook Setup

This small companion service lets you trigger a full **`git pull && docker compose up -d --build`** on your VPS from the Phase 9 Deploy Dashboard's "Deploy to VPS" button.

Runs SEPARATELY from the main Getszy backend container so it can manage the parent compose stack.

## 1. Install dependencies (on VPS)

### AlmaLinux / RHEL / Rocky Linux
```bash
ssh root@31.97.237.222
dnf install -y python3-pip
python3 -m pip install fastapi 'uvicorn[standard]'
```

### Ubuntu / Debian
```bash
apt-get update && apt-get install -y python3-pip
python3 -m pip install fastapi 'uvicorn[standard]'
```

> NOTE: On some minimal images `pip3` may not be aliased on PATH. Always
> prefer `python3 -m pip` for portability.

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

> IMPORTANT: Install Python dependencies (Step 1) BEFORE enabling the service.
> Otherwise systemd will report "active (running)" but immediately crash because
> uvicorn/fastapi are missing. Check with `journalctl -u getszy-webhook -n 30`
> if anything looks off.

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

## Alternative: Run webhook listener as Docker container (no pip needed)

If you don't want to install Python/pip on the host, use the bundled
`Dockerfile.webhook`:

```bash
cd /opt/getszy
docker build -f deploy/Dockerfile.webhook -t getszy-webhook deploy/

docker run -d --name getszy-webhook --restart=always \
  -p 9000:9000 \
  -e WEBHOOK_TOKEN="<your-secret>" \
  -e REPO_DIR=/repo \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /opt/getszy:/repo \
  getszy-webhook

# Verify
curl http://localhost:9000/health
```

To update later: `docker pull` (if pushed to a registry) or rebuild + restart
the container. The systemd approach is preferred for tighter host
integration, but Docker keeps your host clean.

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
