# Getszy - Production Makefile
.PHONY: up down build logs restart seed dev

# --- Docker Production ---
up:
	docker compose -f legacy-getszy/docker-compose.yml up -d

down:
	docker compose -f legacy-getszy/docker-compose.yml down

build:
	docker compose -f legacy-getszy/docker-compose.yml build --no-cache

restart:
	docker compose -f legacy-getszy/docker-compose.yml restart

logs:
	docker compose -f legacy-getszy/docker-compose.yml logs -f --tail=50

logs-backend:
	docker compose -f legacy-getszy/docker-compose.yml logs -f backend --tail=50

logs-frontend:
	docker compose -f legacy-getszy/docker-compose.yml logs -f frontend --tail=50

# --- Setup ---
init:
	@if not exist .env copy .env.example .env
	@echo "[OK] .env created — edit it with real values before running 'make up'"

seed:
	docker compose -f legacy-getszy/docker-compose.yml exec backend python -c "import asyncio; from seed import seed_if_empty, seed_courses_if_empty; asyncio.run(seed_if_empty()); asyncio.run(seed_courses_if_empty())"

# --- Status ---
status:
	docker compose -f legacy-getszy/docker-compose.yml ps

health:
	@curl -s http://localhost/api/health | python -m json.tool 2>nul || echo "Backend not reachable"

# --- Dev (local) ---
dev-backend:
	cd legacy-getszy/backend && python -m uvicorn server:app --reload --port 8000

dev-frontend:
	cd legacy-getszy/frontend && yarn start

# --- Clean ---
clean:
	docker compose -f legacy-getszy/docker-compose.yml down -v
	docker system prune -f

# --- Deploy to VPS ---
deploy:
	@echo "Push to GitHub to trigger deployment..."
	git add -A && git commit -m "deploy: $(shell date +%Y-%m-%d_%H-%M)" && git push
