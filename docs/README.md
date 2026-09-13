# Documentation

This documentation covers the high-level expectation for the project.

---

## Directory Structure

Here is a breakdown of the documentation directories and their purposes:

```text
docs/
├── README.md               # Main index (this file)
├── api/                    # API specifications & backend route documentation
│   ├── index.md            # API overview & root configurations
│   ├── authentication.md   # OAuth flow, JWT session handling, & token encryption
│   └── endpoints/          # Endpoint definitions (one file per router):
│       ├── auth.md         # Login & authentication routes (`backend/app/routers/auth.py`)
│       ├── generate.md     # Resume rewriting & SSE progress stream routes (`backend/app/routers/generate.py`)
│       ├── github.md       # GitHub repo synchronization & query cache routes (`backend/app/routers/github.py`)
│       ├── history.md      # User generation history routes (`backend/app/routers/history.py`)
│       └── resume.md       # PDF upload & metadata management routes (`backend/app/routers/resume.py`)
├── exp/                    # System-level engineering expectations & constraints
│   └── pdf.md              # PDF read/write path (PyMuPDF primary, WeasyPrint fallback)
├── guides/                 # Developer guides
│   └── getting-started.md  # Guides for getting started with the project
├── llm/                    # Pipeline behavior notes
│   └── TASK.md             # JD parse, project rank, rewrite, ATS check
└── imgs/                   # Pictures :)
```

Backend layout relevant to these docs:

```text
backend/app/
├── main.py                 # App entrypoint, CORS, `GET /health`
├── constants.py            # Skills/Projects header sets and section boundary regex
├── routers/                # auth, github, resume, generate, history (see `main.py:160-164`)
├── services/               # auth, encryption, github_graphql, pdf_extractor, pdf_renderer,
│                           # ats, ats_base, ats_llm_adapter, ats_registry, ats_stagnation
└── utils/                  # llm (OpenRouter/Groq client, `extract_json`),
                            # pdf_layout, pdf_fonts, pdf_draw
```

Frontend styles:

```text
frontend/src/app/globals.css        # Font imports plus `css/` split
frontend/src/app/css/               # tokens, base, classes, ids, dashboard, editor, markdown, results
```

The frontend listens with native `EventSource` at `GET /generate/{id}/stream`. The backend emits `resume_writer` and `ats_checker` step events. The hook maps them to `rewrite_N` and `ats_N` display keys. See `frontend/src/hooks/useGenerationStream.ts:93-94,112`.

---

## Document Areas

### [API Specifications](./api/index.md)

Contains route reference guides, payload JSON schemas, and security parameters. If you are developing frontend features or integrating new API hooks, start here.

### [Engineering Expectations](./exp/)

Covers baseline design requirements. Will need to refer to this when editing. Required to ensure clean cross-functionality and proper standards.

### [Developer Guides](./guides/getting-started.md)

Instructions on installing dependencies (Next.js, FastAPI, PostgreSQL), configuring credentials, and running the development environment.
