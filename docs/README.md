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
│   └── endpoints/          # Endpoint definitions:
│       ├── auth.md         # Login & authentication routes
│       ├── generate.md     # Resume rewriting & SSE progress stream routes
│       ├── github.md       # GitHub repo synchronization & query cache routes
│       ├── history.md      # User generation history routes
│       └── resume.md       # PDF upload & metadata management routes
├── exp/                    # System-level engineering expectations & constraints
│   └── pdf.md              # PDF standards & stream editor alignment guidelines
├── guides/                 # Developer guides
│   └── getting-started.md  # Guides for getting started with the project
└── imgs/                   # Pictures :)
```

---

## Document Areas

### [API Specifications](./api/index.md)

Contains route reference guides, payload JSON schemas, and security parameters. If you are developing frontend features or integrating new API hooks, start here.

### [Engineering Expectations](./exp/)

Covers baseline design requirements. Will need to refer to this when editing. Required to ensure clean cross-functionality and proper standards.

### [Developer Guides](./guides/getting-started.md)

Instructions on installing dependencies (Next.js, FastAPI, PostgreSQL), configuring credentials, and running the development environment.
