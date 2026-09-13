# Session Context: Samuel Cleanup - Dead Code, Docs, Lag

Session ID: 2026-09-13-samuel-cleanup
Status: in_progress

## 1. Requirements & Scope (verbatim user intent reproduced)

User prompt reproduced:
"Alright, ultra thorough mode. You're going to be working for a while now. For each of the following tasks, call an explore subagent to collect info, consolidate the info, then call parallel Architect agents to make plans for implementing the fixes to the issues, and then call parallel Builder agents (as many as necessary) to implement the plans. The builder agents should make incremental commits at the end of each of their tasks, and they should be called for 'big' tasks, i.e. each one should write roughly 1000 lines of code. Once all of the issues are fixed and all of the builders are done, call a Checker agent to check all of their work. Use a large variety of skills, as many as possible, within the context, in order to do the best job possible. Always deploy subagents. Once done, report back to me. This task should take HOURS at the MINIMUM. So remember these instructions in detail and fix the following numbered issues: 1) Dead code. Some code is there but not used; other code is duplicated; other code is defined in contradictory ways; other code can be consolidated into a single function; other code needs to be broken up into multiple functions. Use all necessary skills to get rid of all redundancies in the code in all forms. 2) Inaccurate documentation. There are comments, Docs, etc. etc. throughout the repo that are just outdated. Update them. 3) Lag. The project is overall laggy and the experience isn't 'smooth'. There are many so-called rough edges, semi-incomplete features, hard-coded fixes, and so on. Find, investigate, and fix them all. Proceed very carefully. ONLY and SPECIFICALLY do the things I told you to do, nothing else. Don't touch the pt/ folder or anything else ignored by a .gitignore. Minimum required changes only, since these are existing features. Read this prompt, re-produce it, and then proceed. When orchestrating agents, use your agent orchestration skills and give them thorough prompts (almost writing an introductory paragraph each time). Make sure you don't use any commands where you need to ask for permission, only do things you are explicitly allowed to do. So no bash commands. Same with the other agents, they shouldn't do anything that requires user approval. No commands. Not even mkdir. Nothing."

Consolidated tasks:
1. Dead code / redundancy: unused, duplicated, contradictory definitions, consolidate to single function, split oversized functions.
2. Inaccurate documentation: outdated comments, docs, guides.
3. Lag / rough edges: laggy experience, semi-incomplete features, hard-coded fixes.

User clarifications (2026-09-13 Q&A):
- Full pipeline approved: Explore -> Architect -> Builder -> Checker with barrier gates.
- Context bundles/plans live in docs/ (not notes/ which is gitignored).
- Git commits allowed as explicit exception to no-bash rule (builders may commit incrementally).
- Change size: semi-minimum - allow large changes only if necessary, prefer minimal surgical fixes.
- Priority: all three issues, in order 1,2,3.

Non-goals / out-of-scope:
- Do NOT touch pt/ folder or anything ignored by .gitignore (notes/, issues/, plans/, .cache/, node_modules/, .next/, __pycache__, .venv/, postgres_data/, logs/, secrets/, etc.). Exception: docs/ allowed, git commits allowed.
- Do NOT modify database, write schema modifications, or perform migrations. No destructive or non-destructive DB changes (codeword "pear" not given).
- Do NOT modify UI Neumorphic design unless explicitly required for lag fix (per AGENTS.md). Minimum changes only.
- Do NOT invent skills/experience/projects; do NOT touch resume sections outside Skills/Projects logic.
- Do NOT store raw keys, log raw PDFs/JDs/keys, commit .env/secrets.
- GitHub data only via GraphQL client (except auth router REST exception).

## 2. Standards to Follow

- AGENTS.md: minimalistic clean code, ruff + Python 3.12 union hints, async SQLAlchemy, Pydantic validation, mock LLM/GitHub in tests (uv run pytest), pnpm only, typed TS, PascalCase components / camelCase vars / kebab-case files, EventSource SSE.
- Backend style: load linting skill; Frontend: vercel-react-best-practices, frontend-ui (review only, no theme change), web-design-guidelines for audit.
- Docs: writer, writing-guidelines, documenter, docs-generator.
- Other skills to consider: simplify-code, error-triage, backend-latency-profiler-helper, input-validation-sanitization-auditor (audit only), coverage-strategist (no new coverage mandates), spec-creator for plans.

## 3. Reference Files

- Backend: backend/app/main.py, config.py, database.py, orchestrator.py, ats.py, constants.py, routers/*.py, services/*.py, skills/*.py, utils/*.py, models/*.py, schemas/*.py
- Frontend: frontend/src/app/**/*.tsx, components/**/*.tsx, lib/*.ts, hooks/*.ts, styles/
- Docs: docs/README.md, docs/guides/*, docs/api/*, docs/llm/*, README.md, AGENTS.md, backend/app/skills/*.md (prompt templates)
- Config: frontend/package.json, backend/pyproject.toml, docker-compose.yml

## 4. External Documentation Fetched

- None yet. If builders need current library docs (Next.js 14, FastAPI, SQLAlchemy 2.0), use context7 or api-doc-understander skills read-only.

## 5. Components & Architecture

- Pipeline: JD Parser -> Project Matcher -> Resume Writer -> ATS Checker via orchestrator.py + SSE (POST /generate/, GET /generate/{id}/stream)
- Frontend workspace: dashboard, resume upload, JD paste, sync, results/[id] SSE progress, history
- DB: PostgreSQL 16 + pgvector (read-only reference, no migrations)

## 6. Invariants & Constraints

- No bash except `git status/diff/log/commit` (user-approved exception). No mkdir, no installs, no deploys, no DB commands.
- Subagents: use Read/Glob/Grep/Write/Edit only; never touch pt/ or gitignored paths; never commit .env/secrets.
- stop_on_failure + report_first: on build/test/lint error, HALT, report location/cause, propose fix, request approval.
- Minimal surgical edits; preserve imports; update import references if moving code.
- All plans in docs/samuel-cleanup-*.md (not notes/).

## 7. Exit Criteria & Definition of Done

- [ ] Explore reports for dead-code, docs, lag consolidated
- [ ] Architect plans (atomic subtasks, DAG, deliverables, acceptance criteria) in docs/
- [ ] Builders implement per plan with incremental git commits, minimal diffs
- [ ] Checker audit passes (standards, imports, no secrets, no DB changes, no ignored-path touches)
- [ ] Final CEO report to user
