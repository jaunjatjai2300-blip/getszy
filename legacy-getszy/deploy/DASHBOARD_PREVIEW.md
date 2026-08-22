# Customer Dashboard Preview Deployment

This preview procedure exists so the customer dashboard can be reviewed before it is placed on the production release branch. The preview is a separate frontend container, a separate Compose project, and a separate hostname. It does **not** reuse the production frontend container or production Compose lifecycle.

## Safety model

The preview is served at `https://preview.<DOMAIN>`. Its Caddy route proxies `GET`, `HEAD`, and `OPTIONS` API requests to the normal backend only for UI rendering. It rejects all state-changing API methods except `POST /api/auth/login`, which is required to establish a session for a real customer account. Therefore preview users can sign in and inspect their dashboard, but cannot create, edit, publish, delete, generate billable assets, or trigger external integrations from the preview hostname.

Do not use this preview stack for payment, content generation, integration connection, or publication testing. Those functions require a separate staging backend and database before they can be tested safely.

## Prerequisites

The production Caddy route must already have been deployed from `release/getszy-production-hardening` and validated inside the existing Caddy container. The preview DNS record must resolve directly to the VPS:

```text
preview.getszy.com  ->  <VPS public IPv4 address>
```

The preview service attaches to the existing Docker network named `getszy` and advertises the explicit network alias `getszy-dashboard-preview`. It has no host ports, database volumes, Redis volumes, or production service dependencies.

## Start or refresh the preview

Run the following in a shell on the VPS. It creates or refreshes an isolated checkout and starts **only** the preview frontend service.

```bash
set -euo pipefail
PREVIEW_ROOT=/root/getszy-dashboard-preview
BRANCH=feature/customer-dashboard-preview
REPOSITORY=https://github.com/jaunjatjai2300-blip/getszy.git

if [ -d "$PREVIEW_ROOT/.git" ]; then
  cd "$PREVIEW_ROOT"
  git fetch origin "$BRANCH"
  git checkout "$BRANCH"
  git pull --ff-only origin "$BRANCH"
elif [ ! -e "$PREVIEW_ROOT" ]; then
  git clone --branch "$BRANCH" --single-branch "$REPOSITORY" "$PREVIEW_ROOT"
else
  echo "Refusing to use $PREVIEW_ROOT because it exists but is not a Git checkout." >&2
  exit 1
fi

cd "$PREVIEW_ROOT/legacy-getszy"
docker compose -p getszy-dashboard-preview \
  -f docker-compose.dashboard-preview.yml config
docker compose -p getszy-dashboard-preview \
  -f docker-compose.dashboard-preview.yml up -d --build

docker compose -p getszy-dashboard-preview \
  -f docker-compose.dashboard-preview.yml ps
```

This build uses the preview branch's `Dockerfile.frontend` and serves the static React build through a non-root Nginx container named `getszy-dashboard-preview`. The command neither rebuilds nor restarts the production frontend, backend, MongoDB, Redis, Caddy, backups, or monitoring services.

## Preview verification

First verify the explicit Docker alias from the live Caddy container:

```bash
cd /root/getszy-production/legacy-getszy
docker compose exec caddy getent hosts getszy-dashboard-preview
```

The output must show an internal Docker address in the `172.*` range, not `127.0.0.1`. Then perform the public checks:

```bash
curl -fsS --max-time 20 https://getszy.com/api/health; echo
curl -fsSI --max-time 20 https://preview.getszy.com/
curl -sS -o /dev/null -w '%{http_code}\n' \
  -X POST https://preview.getszy.com/api/builder/projects
```

Expected results are: production health JSON, a successful `200` or redirect-to-login response for the preview page, and `405` for the preview mutation test.

Open `https://preview.getszy.com` in a private/incognito browser window and sign in with a non-admin customer account. Review Neo, Video Studio, Creator Studio, Build Studio, AI Tools, Agents, and Integrations. In Build Studio, inspect an existing build preview only; do not attempt to create or publish anything. The workspace must visibly state **Private preview** and **Not deployed**.

## Stop the preview

```bash
cd /root/getszy-dashboard-preview/legacy-getszy
docker compose -p getszy-dashboard-preview \
  -f docker-compose.dashboard-preview.yml down
```

Stopping the preview does not stop or delete the production Getszy containers, database volumes, Redis, backups, or monitoring services.
