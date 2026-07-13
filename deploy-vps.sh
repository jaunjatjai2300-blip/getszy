#!/bin/bash
# ================================================================
# GETSZY VPS Deploy Script
# Run this on your VPS to deploy latest changes
# Usage: bash deploy-vps.sh
# ================================================================
set -e

REPO_DIR="/opt/getszy"
LEGACY_DIR="$REPO_DIR/legacy-getszy"

echo "=== GETSZY Deploy $(date) ==="

# 1. Pull latest code
cd "$REPO_DIR"
git pull origin main

# 2. Verify Ollama is running and qwen model is available
echo "--- Checking Ollama ---"
if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Ollama is running"
    if curl -sf http://localhost:11434/api/tags | grep -q "qwen"; then
        echo "Qwen model found"
    else
        echo "WARNING: qwen model not found. Pulling..."
        ollama pull qwen2.5:7b
    fi
else
    echo "WARNING: Ollama not responding on port 11434"
    echo "Make sure Ollama is running: systemctl start ollama"
fi

# 3. Copy .env if not exists
if [ ! -f "$LEGACY_DIR/.env" ]; then
    echo "Creating .env from template..."
    cp "$LEGACY_DIR/.env.example" "$LEGACY_DIR/.env"
    echo "EDIT $LEGACY_DIR/.env with real values before continuing!"
    exit 1
fi

# 4. Rebuild and restart containers
cd "$LEGACY_DIR"
echo "--- Building containers ---"
docker compose build --no-cache

echo "--- Restarting services ---"
docker compose down
docker compose up -d

# 5. Wait for health
echo "--- Waiting for backend health check ---"
for i in $(seq 1 30); do
    if curl -sf http://localhost/api/health > /dev/null 2>&1; then
        echo "Backend is healthy!"
        break
    fi
    echo "Waiting... ($i/30)"
    sleep 5
done

# 6. Verify Ollama connectivity from backend
echo "--- Verifying Ollama connectivity ---"
docker exec getszy-backend python -c "
import httpx, os
url = os.environ.get('OLLAMA_BASE_URL', 'http://host.docker.internal:11434')
model = os.environ.get('OLLAMA_MODEL', 'qwen2.5:7b')
try:
    r = httpx.get(f'{url}/api/tags', timeout=10)
    models = [m['name'] for m in r.json().get('models', [])]
    print(f'Ollama models: {models}')
    if any('qwen' in m for m in models):
        print('Qwen model verified OK')
    else:
        print('WARNING: qwen not in Ollama models list')
except Exception as e:
    print(f'ERROR connecting to Ollama: {e}')
" 2>&1 || echo "Could not verify Ollama from backend container"

# 7. Show status
echo "--- Service Status ---"
docker compose ps

echo ""
echo "=== Deploy complete ==="
echo "Site: https://getszy.com"
echo "API: https://getszy.com/api/health"
echo "Logs: cd $LEGACY_DIR && docker compose logs -f --tail=50"
