# Samuel

![Saul and Daivd by Rembrandt, 1651](docs/imgs/cover.jpg)

LLM-based resume writer. Takes in GitHub repos, runs semantic matching, tailors resume, returns a new one. Agentic skill chain (parse JD → match projects → write resume → ATS check) with SSE streaming.

## Prerequisites

- Docker + Docker Compose
- [GitHub OAuth App](https://github.com/settings/developers) (register one with callback URL `http://localhost:3000/auth/callback`)
- OpenRouter API key (users supply their own)

## Quick Start

```bash
# 1. Clone and enter
git clone <repo> && cd samuel

# 2. Set GitHub OAuth credentials
export GITHUB_CLIENT_ID=your_client_id
export GITHUB_CLIENT_SECRET=your_client_secret

# 3. Start everything
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Health check | http://localhost:8000/health |

## Usage Flow

1. Open http://localhost:3000 → **Login with GitHub**
2. In dashboard, click **Sync Repos** to fetch your public repos
3. Set your **OpenRouter API key**
4. Upload your current resume as **PDF**
5. Paste a **job description**
6. Click **Generate** → watch the skill chain run live → preview and save the rewritten resume as PDF

## Development (without Docker)

```bash
# Backend
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev -- --port 3000

# Database
docker compose up -d db
```

## Commands

| Command | What |
|---------|------|
| `docker compose up --build` | Full stack |
| `cd backend && uv run pytest` | Backend tests |
| `cd backend && uv run alembic upgrade head` | Run migrations |
| `cd backend && uv run ruff check .` | Lint backend |
| `cd frontend && npm run lint` | Lint frontend |

## Architecture

```
User → Next.js → FastAPI → Orchestrator
                              ├── JD Parser (LLM)
                              ├── Project Matcher (LLM + pgvector)
                              ├── Resume Writer (LLM)
                              └── ATS Checker (LLM)
                    → SSE stream → User sees live progress
```

