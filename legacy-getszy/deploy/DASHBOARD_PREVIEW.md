# Customer Dashboard Preview Deployment

This preview procedure exists so the customer dashboard can be reviewed before it is placed on the production release branch. The preview is a separate frontend container, a separate Compose project, and a separate hostname. It does **not** reuse the production frontend container or production Compose lifecycle.

## Safety model

The preview is served at `https://preview.<DOMAIN>`. Its Caddy route proxies `GET`, `HEAD`, and `OPTIONS` API requests to the normal backend only for UI rendering. It rejects all state-changing API methods except `POST /api/auth/login`, which is required to establish a session for a real customer account. Therefore preview users can sign in and inspect their dashboard, but cannot create, edit, publish, delete, generate billable assets, or trigger external integrations from the preview hostname.

Do not use this preview stack for payment, content generation, integration connection, or publication testing. Those functions require a separate staging backend and database before they can be tested safely.

## One-time DNS requirement

Create an `A` record before starting the preview:

```text
preview.getszy.com  ->  <your VPS public IPv4 address>
```

Wait until the record resolves to the VPS. Caddy will obtain the HTTPS certificate when it receives the hostname and DNS is correct.

## Start or refresh the preview

Run the following from the repository root on the VPS after the preview branch has been pushed and checked out:

```bash
cd /root/getszy-dashboard-preview

git fetch origin feature/customer-dashboard-preview
git checkout feature/customer-dashboard-preview
git pull --ff-only origin feature/customer-dashboard-preview

cd legacy-getszy

docker compose -p getszy-dashboard-preview -f docker-compose.dashboard-preview.yml up -d --build

docker compose up -d --force-recreate caddy

docker compose -p getszy-dashboard-preview -f docker-compose.dashboard-preview.yml ps
curl -i https://preview.getszy.com/
```

The first `docker compose` command starts only `getszy-dashboard-preview`. The second command reloads Caddy so it receives the additional preview hostname block. It does not rebuild the production backend or production frontend.

## Preview verification

1. Open `https://preview.getszy.com` in an incognito/private browser window.
2. Sign in with a non-admin customer account.
3. Visit each dashboard tab: Neo, Video Studio, Creator Studio, Build Studio, AI Tools, Agents, and Integrations.
4. In Build Studio, create nothing. Inspect an existing build preview only if one already exists. Verify desktop, tablet, and mobile preview modes. The panel must visibly state **Private preview** and **Not deployed**.
5. Verify a write operation is blocked with HTTP 405 at the preview hostname:

```bash
curl -i -X POST https://preview.getszy.com/api/builder/projects
```

Expected result: `405` and a message that the dashboard preview is read-only.

## Stop the preview

```bash
cd /root/getszy-dashboard-preview/legacy-getszy
docker compose -p getszy-dashboard-preview -f docker-compose.dashboard-preview.yml down
```

Stopping the preview does not stop or delete the production Getszy containers, database volumes, Redis, backups, or monitoring services.
