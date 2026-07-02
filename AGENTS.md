# Samuel — Agent Guide

## Project Overview

**Samuel** is an LLM-based agentic resume rewriter. It reads a user's resume (PDF), fetches and caches their public GitHub repositories via GitHub's GraphQL API, semantically matches repository details against a target Job Description (using pgvector), rewrites the skills and projects sections of the resume to align with the JD, runs an ATS compatibility check, and streams progress live to the frontend using Server-Sent Events (SSE).

---

## CRITICAL RULES

### Do NOT modify UI unless explicitly asked
The frontend features a strict **Neumorphic design system** styled with CSS variables and Tailwind (see `notes/STYLE.md`). Do not touch or modify components, typography, layout, themes, spacing, or neumorphic box-shadow structures unless explicitly requested.

### Keep code minimalistic & clean
Avoid unnecessary abstractions, defensive programming for impossible states, boilerplate, or over-engineering. Write minimal, direct code following existing patterns. Do not add comments unless the logic is genuinely non-obvious.

### Data & Resume Integrity (No Hallucinations)
- **Do NOT invent** skills, experience, or projects that do not exist in the user's resume or synchronized GitHub repositories.
- **Do NOT modify** resume sections outside of the **Skills** and **Projects** sections. Other sections (e.g., Contact, Education, Work Experience timeline) must remain untouched.

### Security and Key Encryption
- **Never store raw API keys** or access tokens. The user's OpenRouter API key and GitHub OAuth token must be encrypted at rest in the database using Fernet symmetric encryption (using `ENCRYPTION_KEY` from the environment).
- **Never log** raw PDF content, full job descriptions, or decrypted API keys.
- **Never commit** `.env` files, Docker secrets, or credential material.

### GitHub API Usage
- **Do NOT** make REST calls to the GitHub API. Always use the single query GitHub GraphQL client to fetch repository info (name, description, README, stars, languages, topics).

---

## Architecture

```
User (Browser) 
  ↔ Next.js App (pnpm / App Router) [Port 3000]
  ↔ FastAPI Backend (Python 3.12 / uv) [Port 8000]
      ├── PostgreSQL 16 + pgvector Database
      ├── OpenRouter API Client (LLM Client)
      └── SSE Streaming Response
```

### Stack Components
- **Frontend:** Next.js 14+, TypeScript, Tailwind CSS, pnpm package manager.
- **Backend:** FastAPI, Python 3.12, async SQLAlchemy (2.0+), Alembic, PyMuPDF (fitz) for PDF text extraction, WeasyPrint for server-side HTML-to-PDF rendering.
- **Database:** PostgreSQL 16 with the `pgvector` extension for caching repository embeddings and user/resume state.
- **LLMs:** Hosted models via OpenRouter (using custom-supplied keys).

---

## Project Structure — Key Files

### Backend (`backend/app/`)

| File / Directory | Purpose |
| :--- | :--- |
| `main.py` | FastAPI application entrypoint, CORS config, and startup/lifespan tasks (e.g., debug file cleanup). |
| `config.py` | Environment variable definitions and secret key derivations. |
| `database.py` | SQLAlchemy async database engine and session manager. |
| `models/` | SQLAlchemy ORM database models (`user.py`, `repository.py`, `resume.py`, `generation.py`). |
| `schemas/` | Pydantic models for validation and request/response serialization. |
| `routers/` | Endpoint definitions grouped by feature (`auth.py`, `github.py`, `resume.py`, `generate.py`, `history.py`). |
| `services/` | Integration services: `github_graphql.py`, `pdf_extractor.py`, `encryption.py` (Fernet), `embedding.py`. |
| `skills/` | The core agentic skill chain (orchestrator and individual sub-agents). |
| `utils/llm.py` | Low-level OpenRouter client supporting chat completions and text embeddings. |

### Frontend (`frontend/src/`)

| File / Directory | Purpose |
| :--- | :--- |
| `app/globals.css` | Neumorphic theme CSS variables, light/dark mode settings, and card shadow styles. |
| `app/layout.tsx` | Root layout setting up font configurations and basic layout. |
| `app/page.tsx` | Login page directing users to GitHub OAuth. |
| `app/dashboard/page.tsx` | Main user workspace: resume upload, JD paste, API key input, sync button. |
| `app/dashboard/results/[id]/page.tsx` | SSE progress list and interactive preview of the rewritten resume. |
| `app/dashboard/history/page.tsx` | Displays lists of past generations with redirection options. |
| `lib/api.ts` | Frontend wrapper for fetching FastAPI backend endpoints. |
| `lib/types.ts` | Frontend TypeScript definitions mirroring backend Pydantic schemas. |

---

## The Agentic Skill Chain

The core pipeline is driven by the master `Orchestrator` (`backend/app/skills/orchestrator.py`), which executes four sub-agent steps sequentially. It streams progress events via Server-Sent Events (SSE) and writes prompt/response debug logs to a configured directory.

```
[Job Description Text]
  │
  ▼
[Step 1: JD Parser] (jd_parser.md + jd_parser.py)
  │  ├── Role: Senior Technical Recruiter
  │  └── Output: Pydantic model `JDRequirements` (keywords, skills, seniority, requirements)
  ▼
[Step 2: Project Matcher] (project_matcher.md + project_matcher.py)
  │  ├── Role: Technical Matcher
  │  └── Output: List of GitHub repos ranked with relevance scores and match reasoning
  ▼
[Step 3: Resume Writer] (resume_writer.md + resume_writer.py)
  │  ├── Role: Senior Resume Writer
  │  └── Output: Rewritten resume text (updating ONLY the skills and projects sections)
  ▼
[Step 4: ATS Checker] (ats_checker.md + ats_checker.py)
     ├── Role: ATS Optimizer
     └── Output: `ATSReport` containing compatibility score (0-100), warnings, and improvements
```

### Skill Prompt & Runner Conventions
Each skill consists of two companion files in `backend/app/skills/`:
1. **A Prompt Template (`.md`):** Uses clear role-play instructions, explicit DOs/DON'Ts lists, structured JSON schemas, and `{{PLACEHOLDERS}}`.
2. **A Runner Class (`.py`):** Loads the markdown template, replaces placeholders, makes an async call to `LLMClient`, parses/validates the response using Pydantic, and saves local debug JSON dumps.

---

## Coding Conventions

### Backend (Python)
- **Code Style:** Checked with `ruff`. Use Python 3.12 native union type hints (e.g. `str | None`).
- **Database & Async:** Always use async SQLAlchemy engines, sessions, and database queries.
- **Pydantic Validation:** Every request and response payload must be validated via Pydantic. Use Pydantic's `response_model` option in `LLMClient.complete` for structured JSON output.
- **Testing:** Put tests under `backend/tests/`. Run via `uv run pytest`. Always mock external LLM and GitHub API requests.

### Frontend (Next.js / React)
- **Package Manager:** Use `pnpm`. Do NOT use `npm` or `yarn`. A `pnpm-lock.yaml` file must be committed.
- **TypeScript:** Fully typed components, api calls, and state variables.
- **Naming Conventions:** `PascalCase` for React components, `camelCase` for variables/functions, and `kebab-case` for file/directory names.
- **SSE Streaming:** Use the browser-native `EventSource` on the frontend to consume backend streams. Update states and animations React-side in real-time as steps transition.

---

## Data Flow & SSE Events

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend
    participant Backend
    participant LLM as OpenRouter
    database DB as PostgreSQL

    User->>Frontend: Click "Generate Resume"
    Frontend->>Backend: POST /generate/ (JD + Resume ID)
    Backend->>DB: Create Generation record (pending)
    Backend->>Frontend: Return generation_id
    Frontend->>Backend: Connect to GET /generate/{id}/stream
    Note over Backend: Starts Async Generator for SSE
    
    Backend->>Frontend: Event: step-start {"step": "jd_parser"}
    Backend->>LLM: Parse JD text
    LLM-->>Backend: Return JDRequirements JSON
    Backend->>Frontend: Event: step-done {"step": "jd_parser"}

    Backend->>Frontend: Event: step-start {"step": "project_matcher"}
    Backend->>DB: Fetch cached user repos
    Backend->>LLM: Rank repos against requirements
    LLM-->>Backend: Return ranked repos JSON
    Backend->>Frontend: Event: step-done {"step": "project_matcher"}

    Backend->>Frontend: Event: step-start {"step": "resume_writer"}
    Backend->>LLM: Rewrite skills & projects
    LLM-->>Backend: Return rewritten text
    Backend->>Frontend: Event: step-done {"step": "resume_writer"}

    Backend->>Frontend: Event: step-start {"step": "ats_checker"}
    Backend->>LLM: Evaluate ATS score & issues
    LLM-->>Backend: Return ATSReport JSON
    Backend->>Frontend: Event: step-done {"step": "ats_checker"}

    Backend->>DB: Update Generation (completed, save final data)
    Backend->>Frontend: Event: done {"generation_id": "...", "ats_score": 85}
```
