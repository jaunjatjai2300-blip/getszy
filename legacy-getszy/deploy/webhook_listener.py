"""Getszy VPS deploy webhook listener.

Run this as a tiny systemd service on the VPS - SEPARATE from the main
Getszy backend container. It listens on :9000 and, when called with the
correct token, runs `git pull` + `docker compose up -d --build` for the
repo at REPO_DIR.

The main app's Phase 9 Deploy Dashboard 'Deploy to VPS' button POSTs to this
listener via the DEPLOY_WEBHOOK_URL env var.

Usage:
  pip install fastapi uvicorn[standard]
  WEBHOOK_TOKEN=<your-secret> REPO_DIR=/opt/getszy python3 webhook_listener.py

Or install the bundled systemd service (see deploy/README.md).
"""
import os
import subprocess
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, Header, HTTPException
import uvicorn

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('getszy-webhook')

TOKEN = os.environ.get('WEBHOOK_TOKEN', '').strip()
REPO_DIR = os.environ.get('REPO_DIR', '/opt/getszy').strip()
PORT = int(os.environ.get('WEBHOOK_PORT', '9000'))

if not TOKEN:
    log.warning('WEBHOOK_TOKEN not set - listener will REJECT all requests')

app = FastAPI(title='Getszy Webhook Listener', version='1.0')
_last_run = {'at': None, 'ok': False, 'log': ''}


@app.get('/health')
async def health():
    return {'ok': True, 'service': 'getszy-webhook', 'repo_dir': REPO_DIR, 'last_run': _last_run}


@app.post('/deploy')
async def deploy(x_token: str = Header(default=None, alias='X-Token')):
    if not TOKEN or x_token != TOKEN:
        raise HTTPException(status_code=401, detail='Invalid or missing X-Token header')
    log.info(f'Deploy triggered for {REPO_DIR}')
    started = datetime.now(timezone.utc).isoformat()
    cmd = f'cd {REPO_DIR} && git pull --ff-only && docker compose up -d --build'
    try:
        out = subprocess.run(['bash', '-lc', cmd], capture_output=True, text=True, timeout=600)
        result = {
            'ok': out.returncode == 0,
            'returncode': out.returncode,
            'started_at': started,
            'ended_at': datetime.now(timezone.utc).isoformat(),
            'stdout_tail': out.stdout[-2000:],
            'stderr_tail': out.stderr[-2000:],
        }
        _last_run.update({'at': result['ended_at'], 'ok': result['ok'], 'log': result['stderr_tail'][-500:]})
        log.info(f'Deploy {"ok" if result["ok"] else "FAILED"} rc={out.returncode}')
        return result
    except subprocess.TimeoutExpired:
        log.error('Deploy timed out after 10 minutes')
        return {'ok': False, 'error': 'Deploy timed out (10 min)'}
    except Exception as e:
        log.exception('Deploy crashed')
        return {'ok': False, 'error': str(e)}


if __name__ == '__main__':
    log.info(f'Starting Getszy webhook listener on :{PORT} for {REPO_DIR}')
    uvicorn.run(app, host='0.0.0.0', port=PORT, access_log=False)
