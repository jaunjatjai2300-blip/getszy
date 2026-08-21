#!/usr/bin/env bash
# Getszy production bootstrap.
# Run from a trusted terminal as root or a user with sudo access.
set -Eeuo pipefail

REPOSITORY_URL="https://github.com/jaunjatjai2300-blip/getszy.git"
RELEASE_BRANCH="release/getszy-production-hardening"
REPO_DIR="${GETSZY_REPO_DIR:-$HOME/getszy-production}"
APP_DIR="$REPO_DIR/legacy-getszy"

if [ "${EUID}" -eq 0 ]; then
  SUDO=""
else
  SUDO="sudo"
fi

info() { printf '\n==> %s\n' "$*"; }
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

set_env() {
  # Replace or append KEY=value without printing the secret.
  key="$1"
  value="$2"
  file="$3"
  if grep -q "^${key}=" "$file"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >> "$file"
  fi
}

random_hex() {
  openssl rand -hex 32
}

fernet_key() {
  # Fernet requires 32 random bytes encoded using URL-safe Base64.
  openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n'
}

require_value() {
  key="$1"
  file="$2"
  value="$(grep -E "^${key}=" "$file" | tail -n 1 | cut -d= -f2- || true)"
  case "$value" in
    ""|*CHANGE_ME*|*REPLACE_ME*|*yourdomain.com*|*your-alert-sink.com*|*your_groq_key_here*)
      fail "Set a real ${key} value in ${file} before starting production services."
      ;;
  esac
}

info "Starting Getszy production bootstrap"

if ! command -v git >/dev/null 2>&1; then
  info "Installing Git"
  $SUDO apt-get update -y 2>/dev/null || $SUDO dnf makecache -y
  $SUDO apt-get install -y git 2>/dev/null || $SUDO dnf install -y git
fi

if ! command -v docker >/dev/null 2>&1; then
  info "Installing Docker Engine"
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  $SUDO sh /tmp/get-docker.sh
  rm -f /tmp/get-docker.sh
  if [ "${EUID}" -ne 0 ]; then
    $SUDO usermod -aG docker "$USER"
    info "Docker was installed. Log out and log back in once, then rerun this command."
    exit 0
  fi
fi

if ! docker compose version >/dev/null 2>&1; then
  fail "Docker Compose v2 is required. Install the docker-compose-plugin, then rerun this command."
fi

mkdir -p "$REPO_DIR"
if [ ! -d "$REPO_DIR/.git" ]; then
  info "Cloning Getszy release branch"
  git clone --branch "$RELEASE_BRANCH" --single-branch "$REPOSITORY_URL" "$REPO_DIR"
else
  info "Updating Getszy release branch"
  git -C "$REPO_DIR" fetch origin "$RELEASE_BRANCH"
  git -C "$REPO_DIR" checkout "$RELEASE_BRANCH"
  git -C "$REPO_DIR" pull --ff-only origin "$RELEASE_BRANCH"
fi

[ -f "$APP_DIR/docker-compose.yml" ] || fail "Application Compose file was not found at ${APP_DIR}. The repository layout is unexpected."
cd "$APP_DIR"

if [ ! -f .env ]; then
  info "Creating a secure first-run environment file at ${APP_DIR}/.env"
  umask 077
  cp .env.example .env
  set_env JWT_SECRET "$(random_hex)" .env
  set_env INTEGRATION_ENCRYPTION_KEY "$(fernet_key)" .env
  set_env BACKUP_ENCRYPTION_KEY "$(fernet_key)" .env
  set_env GRAFANA_PASSWORD "$(random_hex)" .env
  set_env SEED_ADMIN_PASSWORD "REPLACE_ME_WITH_A_LONG_UNIQUE_PASSWORD" .env
  set_env SEED_CUSTOMER_PASSWORD "REPLACE_ME_WITH_A_LONG_UNIQUE_PASSWORD" .env
  set_env ALERT_WEBHOOK_URL "REPLACE_ME_WITH_A_REAL_SLACK_DISCORD_OR_PAGERDUTY_WEBHOOK" .env
  set_env LLM_PROVIDER "groq" .env
  set_env GROQ_API_KEY "REPLACE_ME_WITH_YOUR_GROQ_API_KEY" .env

  cat <<EOF

First-run setup is intentionally paused. No containers were started.

Edit the production file now:
  nano ${APP_DIR}/.env

At minimum set these values:
  DOMAIN, SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD,
  SEED_CUSTOMER_EMAIL, SEED_CUSTOMER_PASSWORD,
  GROQ_API_KEY, ALERT_WEBHOOK_URL.

Also configure BACKUP_S3_BUCKET and its limited backup-writer credentials before public launch.
After saving, rerun the same bootstrap command. It will validate and start Getszy.
EOF
  exit 0
fi

info "Validating mandatory production configuration"
require_value DOMAIN .env
require_value JWT_SECRET .env
require_value INTEGRATION_ENCRYPTION_KEY .env
require_value BACKUP_ENCRYPTION_KEY .env
require_value GRAFANA_PASSWORD .env
require_value SEED_ADMIN_EMAIL .env
require_value SEED_ADMIN_PASSWORD .env
require_value SEED_CUSTOMER_EMAIL .env
require_value SEED_CUSTOMER_PASSWORD .env
require_value ALERT_WEBHOOK_URL .env

DOMAIN_VALUE="$(grep -E '^DOMAIN=' .env | tail -n 1 | cut -d= -f2- || true)"
LLM_PROVIDER_VALUE="$(grep -E '^LLM_PROVIDER=' .env | tail -n 1 | cut -d= -f2- || true)"
case "$LLM_PROVIDER_VALUE" in
  groq) require_value GROQ_API_KEY .env ;;
  gemini) require_value GEMINI_API_KEY .env ;;
  openrouter) require_value OPENROUTER_API_KEY .env ;;
  ollama) info "Using host Ollama; confirm it is running at the configured OLLAMA_BASE_URL." ;;
  *) fail "LLM_PROVIDER must be groq, gemini, openrouter, or ollama." ;;
esac

info "Rendering Compose configuration"
docker compose config >/tmp/getszy-compose.rendered.yml

docker compose pull
docker compose up -d --build --remove-orphans

docker compose -f docker-compose.monitoring.yml config >/tmp/getszy-monitoring.rendered.yml
docker compose -f docker-compose.monitoring.yml up -d --remove-orphans

info "Waiting for backend health"
for _ in $(seq 1 30); do
  if curl -fsS -H "Host: ${DOMAIN_VALUE}" http://127.0.0.1/api/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl -fsS -H "Host: ${DOMAIN_VALUE}" http://127.0.0.1/api/health; then
  docker compose ps
  docker compose logs --tail=120 backend caddy
  fail "Getszy did not become healthy. Review the logs above before retrying."
fi

cat <<EOF

Getszy services are running.

Application directory: ${APP_DIR}
Health URL: https://${DOMAIN_VALUE}/api/health
Status: docker compose ps
Backend logs: docker compose logs -f backend
Monitoring status: docker compose -f docker-compose.monitoring.yml ps

Next mandatory checks before public launch:
1. Confirm DNS for DOMAIN points to this VPS and test HTTPS health.
2. Confirm /docs and /openapi.json return 404 publicly.
3. Send and resolve a test Alertmanager alert.
4. Run an encrypted backup and staging restore drill.
EOF
