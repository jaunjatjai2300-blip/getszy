#!/bin/bash
# Usage: ./update-vps-token.sh <vps-ip> <new-pat>

VPS_IP=$1
NEW_PAT=$2

if [ -z "$VPS_IP" ] || [ -z "$NEW_PAT" ]; then
  echo "Usage: $0 <vps-ip> <new-pat>"
  exit 1
fi

ssh root@$VPS_IP << EOF
cd /opt/getszy
# Update docker-compose.yml
sed -i "s/DEPLOY_WEBHOOK_TOKEN:.*/DEPLOY_WEBHOOK_TOKEN: \"$NEW_PAT\"/" docker-compose.yml
sed -i "s/GITHUB_TOKEN:.*/GITHUB_TOKEN: \"$NEW_PAT\"/" docker-compose.yml

# If .env exists, update it too
if [ -f .env ]; then
  sed -i "s/^GITHUB_TOKEN=.*/GITHUB_TOKEN=$NEW_PAT/" .env
  sed -i "s/^DEPLOY_WEBHOOK_TOKEN=.*/DEPLOY_WEBHOOK_TOKEN=$NEW_PAT/" .env
fi

# Restart webhook listener
docker-compose restart webhook_listener
echo "VPS token updated and webhook restarted"
EOF