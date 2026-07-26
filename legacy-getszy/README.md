# Getszy — AI-Powered Business Builder Platform

## What is Getszy?

Getszy is an AI-powered platform that helps entrepreneurs build, launch, and scale their businesses. Use the AI chat to create products, courses, websites, and mobile apps — all without coding.

## How to Use

### 1. Sign Up
Go to [getszy.com](https://getszy.com) and create an account.

### 2. Use the AI Chat
Tell the AI what you want to build:
- "Create an e-commerce store for handmade jewelry"
- "Build a course on Instagram marketing"
- "Generate a logo for my fitness brand"
- "Create a mobile app for my restaurant"

### 3. Manage Your Business
Use the Admin Dashboard tabs to manage everything:
- **Products** — Add/edit/delete products
- **Orders** — Track customer orders
- **Courses** — Create and manage online courses
- **Analytics** — View sales and traffic data
- **Deploy** — Deploy your site with one click

### 4. Key Features
- **AI Code Generation** — Backend + Frontend generated automatically
- **Multi-Agent System** — Planner, Coder, and Reviewer agents work together
- **Codebase RAG** — AI reads your existing code to generate better results
- **Multi-Turn Memory** — AI remembers your previous conversations

## For Developers

### Local Setup
```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # Edit with your keys
uvicorn server:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URL` | MongoDB connection string | `mongodb://localhost:27017` |
| `DB_NAME` | Database name | `getszy` |
| `JWT_SECRET` | Secret key for JWT tokens | Required |
| `OLLAMA_BASE_URL` | Ollama AI server URL | `http://host.docker.internal:11434` |
| `SENTRY_DSN` | Sentry error tracking DSN | Optional |
| `LOGTAIL_TOKEN` | Logtail logging token | Optional |

### Run Tests
```bash
cd backend
pytest tests/ -v
```

### Deploy to VPS
```bash
cd /opt/getszy/legacy-getszy
git pull
docker compose build --no-cache backend
docker compose up -d
```

## Tech Stack
- **Backend:** Python 3.11 + FastAPI + MongoDB
- **Frontend:** React + Vite
- **AI:** Ollama (local) + Groq + Gemini fallback chain
- **Deploy:** Docker + Caddy on VPS
