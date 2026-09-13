# Getting Started

Run Samuel locally with Docker and generate your first rewritten resume within minutes.

## Prerequisites

- Docker and Docker Compose installed on your machine
- A GitHub account to register an OAuth App
- An OpenRouter API key for LLM access

## Step 1: Clone the Repository

```bash
git clone https://github.com/<owner>/<repo>.git
cd samuel
```

## Step 2: Register a GitHub OAuth App

1. Go to GitHub Settings > Developer settings > OAuth Apps and click "New OAuth App".
2. Set the Application name to "Samuel (Local)".
3. Set the Homepage URL to `http://localhost:3000`.
4. Set the Authorization callback URL to `http://localhost:3000/auth/callback`.
5. Click "Register application".
6. Copy the Client ID and generate a Client Secret. Save both for the next step.

## Step 3: Configure Environment Variables

Copy the example environment file and fill in the required values.

```bash
cp .env.example .env
```

Open `.env` and set these variables:

| Variable | Description |
| :--- | :--- |
| `GITHUB_CLIENT_ID` | Your GitHub OAuth App client ID |
| `GITHUB_CLIENT_SECRET` | Your GitHub OAuth App client secret |
| `OPENROUTER_API_KEY` | Server default key for LLM access (users can also save their own key in the dashboard) |
| `GROQ_API_KEY` | Server default key for Groq LLM fallback |
| `SESSION_SECRET` | Random string for session signing |
| `ENCRYPTION_KEY` | Fernet key for encrypting stored tokens (generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) |
| `DATABASE_URL` | PostgreSQL connection string (`postgresql+asyncpg://samuel:samuel_dev_only@localhost:5432/samuel` by default) |
| `ATS_PROVIDER` | ATS engine name (default `llm`) |
| `ATS_MAX_ITERATIONS` | Max ATS retry loop count, 5-7 (default 6) |
| `ATS_STAGNATION_WINDOW` | Score window used for early break (default 3) |
| `ATS_MIN_GAIN` | Min relative gain to keep retrying (default 0.03) |
| `ATS_THRESHOLD_DEFAULT` | Default ATS target score 0-100 (default 80) |
| `SECURE_COOKIE` | Set `true` in production so cookies require HTTPS |
| `DEBUG_DIR` | Directory for prompt and response debug logs |
| `DEBUG_RETENTION_HOURS` | Hours to keep debug logs (default 24) |
| `LOG_LEVEL` | Log level (default `INFO`) |

## Step 4: Start the Application

```bash
docker compose up --build
```

This starts three services: the PostgreSQL database on port 5432, the FastAPI backend on port 8000, and the Next.js frontend on port 3000.

## Step 5: Log In with GitHub

Open `http://localhost:3000` in your browser. Click "Login with GitHub" and authorize the application. You are redirected to the dashboard.

## Step 6: Prepare Your Data

1. Click "Sync Repositories" to fetch your public GitHub repos.
2. Upload your resume as a PDF file.
3. Enter your OpenRouter API key in the settings field.
4. Paste a job description into the text area.

## Step 7: Generate Your Rewritten Resume

Click "Generate Resume". The frontend shows the progress of each step: JD parsing, LLM-ranked project matching, resume rewriting, and deterministic ATS checking. When the process completes, you can download the rewritten resume as a PDF and review the ATS score and warnings.

PDF output uses PyMuPDF in-place rewrite as primary. WeasyPrint render runs only when no source PDF bytes exist.

## Development Without Docker

To run the services individually for development:

**Backend** (requires Python 3.12 and `uv`):

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

**Frontend** (requires Node.js and `pnpm`):

```bash
cd frontend
pnpm install
pnpm dev
```

**Database**: You need a running PostgreSQL 16 instance with the `pgvector` extension enabled. Set the `DATABASE_URL` environment variable to point to it.

## Troubleshooting

| Problem | Likely Cause | Solution |
| :--- | :--- | :--- |
| OAuth callback returns 400 "State mismatch" | The `oauth_state` cookie expired or is missing | Click "Login with GitHub" again from the frontend |
| Repository sync returns 502 | GitHub token is expired or revoked | Log out and log in again to refresh the token |
| Generation fails with "API key not set" | No OpenRouter API key configured | Save a key via the dashboard or set `OPENROUTER_API_KEY` in `.env` |
| PDF download returns 501 | No source PDF bytes and WeasyPrint fallback missing | Upload a source PDF first, or install WeasyPrint for fallback renders |
| Frontend shows CORS errors | Backend is not running or origin mismatch | Ensure the backend runs on port 8000 and the frontend on port 3000 |
| Database connection error | PostgreSQL is not running or `DATABASE_URL` is wrong | Check Docker Compose logs and verify the connection string |
