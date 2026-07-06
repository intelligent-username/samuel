# Samuel API

Samuel is an LLM-powered resume rewriter. It reads a user's resume PDF, fetches their public GitHub repositories, matches repository data against a target job description, rewrites the skills and projects sections, runs an ATS compatibility check, and streams progress live to the frontend.

## Base URL

```
http://localhost:8000
```

## Authentication

This API uses GitHub OAuth with session cookies. All endpoints except `GET /auth/login` require a valid `session` cookie. See the [Authentication guide](authentication.md) for details.

## Resource Groups

| Resource | Description |
| :--- | :--- |
| [Auth](endpoints/auth.md) | GitHub OAuth login, callback, session management, and logout |
| [GitHub](endpoints/github.md) | Sync and list cached GitHub repositories |
| [Resume](endpoints/resume.md) | Upload PDF resumes and store API keys |
| [Generate](endpoints/generate.md) | Start and stream the resume rewriting pipeline |
| [History](endpoints/history.md) | Browse past generations and download results |

## Quick Endpoint Reference

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Health check with database status |
| `GET` | `/auth/login` | Get GitHub OAuth authorization URL |
| `GET` | `/auth/callback` | Handle OAuth callback and set session |
| `GET` | `/auth/me` | Get current user profile |
| `POST` | `/auth/logout` | Clear session cookie |
| `POST` | `/github/sync` | Sync user's public GitHub repositories |
| `GET` | `/github/repos` | List cached repositories |
| `POST` | `/resume/upload` | Upload a PDF resume |
| `POST` | `/resume/key` | Save an encrypted OpenRouter API key |
| `GET` | `/resume/key-status` | Check API key availability |
| `GET` | `/resume/resumes` | List uploaded resumes |
| `POST` | `/generate/` | Start a new resume generation |
| `GET` | `/generate/{id}/stream` | SSE stream for generation progress |
| `GET` | `/generate/{id}/download` | Download the rewritten resume as PDF |
| `GET` | `/history/` | List recent generations |
| `GET` | `/history/{id}` | Get generation details |

## SSE Streaming Skill Chain

The generation pipeline runs four LLM calls in sequence through a skill chain orchestrator. The frontend connects to the SSE stream at `GET /generate/{id}/stream` after creating a generation. The stream emits typed events for each step: `step-start`, `step-done`, intermediate `output`, `done`, and `error`. The four steps are: JD Parser (extracts requirements from the job description), Project Matcher (ranks GitHub repos against those requirements), Resume Writer (rewrites skills and projects), and ATS Checker (evaluates the rewritten resume for applicant tracking system compatibility).
