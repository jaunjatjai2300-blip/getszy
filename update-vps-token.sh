#!/bin/bash
# Rotate the VPS deploy token WITHOUT ever putting it on the command line,
# in shell history, or in a remote process list.
#
# Usage:
#   ./update-vps-token.sh <vps-ip>          # then paste the PAT and press Ctrl-D
#   gh auth token | ./update-vps-token.sh <vps-ip>
#
# The PAT is read from STDIN only. Never pass it as an argument — arguments
# leak into shell history and `ps` output on both machines.
set -euo pipefail

VPS_IP=${1:-}
if [ -z "$VPS_IP" ]; then
  echo "Usage: $0 <vps-ip>   (reads the new PAT from stdin)"
  exit 1
fi

NEW_PAT=$(cat)
if [ -z "$NEW_PAT" ]; then
  echo "ERROR: no token received on stdin" >&2
  exit 1
fi

# Escape sed metacharacters (\, /, |, &)
ESC=$(printf '%s' "$NEW_PAT" | sed -e 's/[\\/|&]/\\&/g')

# Remote script is generated locally (with the token substituted in) and
# streamed to `bash -s` over ssh stdin — no argv exposure, no history, no ps.
REMOTE=$(cat <<'SCRIPT'
set -e
UPDATED=0
for ENVF in /opt/getszy/.env /opt/getszy/legacy-getszy/.env; do
  if [ -f "$ENVF" ]; then
    sed -i "s/^GITHUB_TOKEN=.*/GITHUB_TOKEN=__NEW_TOKEN__/" "$ENVF"
    sed -i "s/^DEPLOY_WEBHOOK_TOKEN=.*/DEPLOY_WEBHOOK_TOKEN=__NEW_TOKEN__/" "$ENVF"
    chmod 600 "$ENVF"
    echo "Updated $ENVF"
    UPDATED=1
  fi
done
if [ "$UPDATED" -ne 1 ]; then
  echo "ERROR: no .env found under /opt/getszy — nothing changed" >&2
  exit 1
fi
cd /opt/getszy/legacy-getszy
# Compose interpolates .env at container *creation*; `restart` does not re-read
# it, so recreate the backend instead.
docker compose up -d backend || docker-compose up -d backend
echo "VPS token rotated in .env and backend recreated"
SCRIPT
)
REMOTE=${REMOTE//'__NEW_TOKEN__'/$ESC}

printf '%s\n' "$REMOTE" | ssh root@"$VPS_IP" 'bash -s'

# Scrub the token from this shell's memory (best effort; the value was never
# written to disk or history).
unset NEW_PAT ESC REMOTE
