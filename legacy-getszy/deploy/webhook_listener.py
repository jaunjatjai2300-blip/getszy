"""Getszy VPS deploy webhook listener.

Run this as a tiny systemd service on the VPS - SEPARATE from the main
Getszy backend container. It listens on :9000 and, when called with the
correct token, syncs the repo at REPO_DIR to origin/main and runs
`docker compose up -d --build`.

Repository sync policy (deterministic deploy mirror):
  /opt/getszy is a DEPLOY CHECKOUT, not a working tree — it must always be
  an exact mirror of origin/main. Before syncing we verify that HEAD is an
  ancestor of (or equal to) origin/main; if the checkout has diverged
  (e.g. hotfix commits made on the server, or an old Checkout behind a
  history rewrite), the listener says so in its own log AND resets to
  origin/main, because silently merging local state back into a deploy
  container is how "works on prod only" bugs get born.

The main app's Phase 9 Deploy Dashboard 'Deploy to VPS' button POSTs to this
listener via the DEPLOY_WEBHOOK_URL env var.

Usage:
  pip install fastapi uvicorn[standard]
  WEBHOOK_TOKEN=<your-secret> REPO_DIR=/opt/getszy python3 webhook_listener.py

Or install the bundled systemd service (see deploy/README.md). After
updating this file on disk, `systemctl restart getszy-webhook` to load it.
"""
import os
import hmac
import time
import subprocess
import logging
from collections import defaultdict, deque
from datetime import datetime, timezone
from fastapi import FastAPI, Header, HTTPException, Request
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('getszy-webhook')

TOKEN = os.environ.get('WEBHOOK_TOKEN', '').strip()
REPO_DIR = os.environ.get('REPO_DIR', '/opt/getszy').strip()
PORT = int(os.environ.get('WEBHOOK_PORT', '9000'))
# Bind to loopback by default so the listener is only reachable via the local
# reverse proxy; set WEBHOOK_BIND=0.0.0.0 (or a specific interface) to expose it.
BIND = os.environ.get('WEBHOOK_BIND', '127.0.0.1').strip()

# Simple in-memory rate limiting: max attempts per minute per client IP
# (deque of monotonic timestamps). Guards the token probe surface.
RATE_LIMIT_MAX = int(os.environ.get('WEBHOOK_RATE_LIMIT', '20'))
RATE_LIMIT_WINDOW = 60.0
_attempts = defaultdict(deque)


def _rate_limited(ip: str) -> bool:
    now = time.monotonic()
    seen = _attempts[ip]
    while seen and now - seen[0] > RATE_LIMIT_WINDOW:
        seen.popleft()
    if len(seen) >= RATE_LIMIT_MAX:
        return True
    seen.append(now)
    return False

if not TOKEN:
    log.warning('WEBHOOK_TOKEN not set - listener will REJECT all requests')

app = FastAPI(title='Getszy Webhook Listener', version='1.1')
_last_run = {'at': None, 'ok': False, 'log': ''}


@app.get('/health')
async def health():
    # Intentionally does not expose repo_dir (internal path disclosure).
    return {'ok': True, 'service': 'getszy-webhook', 'last_run': _last_run}


def _sync_repo() -> subprocess.CompletedProcess:
    """Fetch origin/main and hard-reset the deploy checkout onto it.

    Returns the subprocess result of the sync command chain. A deploy
    checkout must mirror origin/main exactly, so any divergence (local
    commits on the server) is logged loudly and reset away.
    """
    cmd = (
        f'cd {REPO_DIR} && '
        f'git fetch origin main && '
        # Loud, human-readable note when the checkout had local commits that
        # diverge from origin/main, then reset to the exact mirror state.
        'if git merge-base --is-ancestor HEAD origin/main; then '
        '  git reset --hard origin/main; '
        'else '
        '  echo "WARN: /opt/getszy had local commits diverging from origin/main — deploying a server-side hotfix was reset away; see: git reflog"; '
        '  git reset --hard origin/main; '
        'fi'
    )
    return subprocess.run(['bash', '-lc', cmd], capture_output=True, text=True, timeout=300)


@app.post('/deploy')
async def deploy(request: Request, x_token: str = Header(default=None, alias='X-Token')):
    client_ip = request.client.host if request.client else 'unknown'
    if _rate_limited(client_ip):
        log.warning(f'Rate limit breached by {client_ip} — returning 429')
        raise HTTPException(status_code=429, detail='Too many requests')
    if not TOKEN or not hmac.compare_digest(x_token or '', TOKEN):
        log.warning(f'401 token probe from {client_ip}')
        raise HTTPException(status_code=401, detail='Invalid or missing X-Token header')
    log.info(f'Deploy triggered for {REPO_DIR}')
    started = datetime.now(timezone.utc).isoformat()
    # REPO_DIR is the git root (/opt/getszy); docker-compose.yml lives in the
    # legacy-getszy subdir, so build from there. NOTE: do NOT `docker compose
    # restart caddy` here — Caddy proxies this webhook's response, so restarting
    # it mid-request severs the connection and the caller sees HTTP 000. The
    # backend rebuild above already recreates getszy-backend; Caddy reconnects
    # automatically.
    cmd = f'cd {REPO_DIR}/legacy-getszy && docker compose up -d --build'
    try:
        pull = _sync_repo()
        if pull.returncode != 0:
            result = {
                'ok': False,
                'returncode': pull.returncode,
                'started_at': started,
                'ended_at': datetime.now(timezone.utc).isoformat(),
                'stdout_tail': pull.stdout[-2000:],
                'stderr_tail': pull.stderr[-2000:],
            }
            _last_run.update({'at': result['ended_at'], 'ok': False, 'log': result['stderr_tail'][-500:]})
            log.error(f'Repo sync FAILED rc={pull.returncode}: {pull.stderr[-500:]}')
            return result
        out = subprocess.run(['bash', '-lc', cmd], capture_output=True, text=True, timeout=600)
        result = {
            'ok': out.returncode == 0,
            'returncode': out.returncode,
            'started_at': started,
            'ended_at': datetime.now(timezone.utc).isoformat(),
            'stdout_tail': (pull.stdout + out.stdout)[-2000:],
            'stderr_tail': (pull.stderr + out.stderr)[-2000:],
        }
        _last_run.update({'at': result['ended_at'], 'ok': result['ok'], 'log': result['stderr_tail'][-500:]})
        log.info(f'Deploy {"ok" if result["ok"] else "FAILED"} rc={out.returncode}')
        return result
    except subprocess.TimeoutExpired:
        log.error('Deploy timed out (10 min)')
        return {'ok': False, 'error': 'Deploy timed out (10 min)'}
    except Exception as e:
        log.exception('Deploy crashed')
        return {'ok': False, 'error': str(e)}


if __name__ == '__main__':
    log.info(f'Starting Getszy webhook listener on {BIND}:{PORT} for {REPO_DIR}')
    uvicorn.run(app, host=BIND, port=PORT, access_log=False)
