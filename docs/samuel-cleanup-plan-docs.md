# Samuel Issue #2 — Docs Fixes Plan

## Abstract

Some user-facing guides and API pages describe behavior the product no longer has. The pipeline now uses three smart steps plus a fixed checking loop, sends more progress updates than listed, and offers more buttons and addresses than documented. Setup pages also name old settings and show example links that do not work. This plan refreshes all guides, tables, and descriptions so every claim matches what the product actually does, without changing how the product works.

## Context and inputs

- Session bundle: `docs/samuel-cleanup-context.md`
- Consolidated findings: `docs/samuel-cleanup-explore-consolidated.md` (Docs fixes 1-8)
- Skills consulted: `spec-creator` (plan shape), `agent-orchestration-planner` (atomic DAG), `writer` + `writing-guidelines` (plain language), `documenter` (claim-to-code tracing), `docs-generator` (endpoint page structure)
- Ground truth verified read-only: `backend/app/orchestrator.py`, `backend/app/config.py`, `backend/app/routers/generate.py`, `history.py`, `github.py`, `resume.py`, `backend/app/schemas/__init__.py`, `frontend/src/lib/types.ts`, `docs/api/**`, `docs/guides/getting-started.md`, `README.md`, `docs/llm/TASK.md`, `docs/exp/pdf.md`, `backend/app/skills/ats_checker.md`

## Invariants (must hold for every subtask)

- Markdown + TSDoc/docstrings only. No code logic, no DB, no migrations (codeword `pear` not given), no UI/Neumorphic changes, no `pt/` touches, no gitignored paths except `docs/` (per `docs/samuel-cleanup-context.md`).
- Minimal surgical edits. Preserve headings and anchors. Fix claims, tables, and stale names only.
- Never log or paste raw PDFs, JDs, or decrypted keys. Never commit `.env` or secrets.
- GitHub data stays GraphQL-only (auth REST exception already documented in `docs/api/endpoints/github.md:104-106`).
- On contradiction between docs claim and code, HALT per `stop_on_failure`: report file:line, propose fix, request approval. Do not auto-rewrite code to match docs.

## Subtask DAG (agent-orchestration-planner schema)

### docs-01 — Rewrite ATS + SSE docs, deprecate LLM ats_checker prompt

- `id`: `docs-01`
- `seq`: `01`
- `title`: Rewrite ATS and SSE docs for deterministic loop
- `status`: `pending`
- `depends_on`: `[]`
- `parallel`: `true`
- `suggested_role`: `Implementer`
- `deliverables`:
  - `docs/api/endpoints/generate.md`
  - `docs/api/index.md`
  - `backend/app/skills/ats_checker.md`
- `context_files`: [`docs/samuel-cleanup-explore-consolidated.md`, `docs/samuel-cleanup-context.md`]
- `reference_files`: [`backend/app/orchestrator.py`, `backend/app/ats.py`, `backend/app/schemas/__init__.py`]
- `acceptance_criteria`:
  - `docs/api/endpoints/generate.md` states 3 LLM skills (`jd_parser`, `project_matcher`, `resume_writer` per `backend/app/orchestrator.py:87-127`) plus deterministic ATS via `ATS()` per `backend/app/orchestrator.py:131-142`, not 4 LLM calls.
  - SSE table lists `warning` per `backend/app/orchestrator.py:81`, `ats_evaluation` per `backend/app/orchestrator.py:263,353,407`, `ats_loop` per `backend/app/orchestrator.py:371`, `ats_stagnation` per `backend/app/orchestrator.py:373`, `output` per `backend/app/orchestrator.py:175`, `done` per `backend/app/orchestrator.py:176` with `exit_reason` in `single_pass|threshold_met|stagnation|max_iterations` per `backend/app/orchestrator.py:356,374,409,413`.
  - `docs/api/index.md:46-48` updated to same model; `backend/app/skills/ats_checker.md:1-37` gets deprecation header noting deterministic engine is primary and the `.md` prompt is legacy reference only.
- `verify`: Read the three deliverables; grep SSE table for `ats_loop` and `ats_stagnation`; confirm no remaining `four LLM` wording.

### docs-02 — Fix env var table and key-generation command

- `id`: `docs-02`
- `seq`: `02`
- `title`: Fix environment variable docs and Fernet command
- `status`: `pending`
- `depends_on`: `[]`
- `parallel`: `true`
- `suggested_role`: `Implementer`
- `deliverables`:
  - `docs/guides/getting-started.md`
  - `docs/api/authentication.md`
- `context_files`: [`docs/samuel-cleanup-explore-consolidated.md`]
- `reference_files`: [`backend/app/config.py`]
- `acceptance_criteria`:
  - Table matches `backend/app/config.py:6-23`: `OPENROUTER_API_KEY` (not `OPENAI_API_KEY`), `GROQ_API_KEY`, `SESSION_SECRET` (not `SECRET_KEY`), `ENCRYPTION_KEY`, `ATS_PROVIDER`, `ATS_MAX_ITERATIONS` (5-7), `ATS_STAGNATION_WINDOW`, `ATS_MIN_GAIN`, `ATS_THRESHOLD_DEFAULT`, `SECURE_COOKIE`, `DEBUG_DIR`/`DEBUG_RETENTION_HOURS`, `LOG_LEVEL`; no `OPENAI_API_KEY` or `SECRET_KEY` rows remain.
  - Fernet command generates URL-safe base64 32-byte key (e.g. `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`), not `openssl rand -hex 32` per `docs/guides/getting-started.md:42`.
  - `DATABASE_URL` row notes `postgresql+asyncpg://` default per `backend/app/config.py:6`.
- `verify`: Grep deliverables for `OPENAI_API_KEY`, `SECRET_KEY`, `openssl rand -hex`; expect zero hits.

### docs-03 — Complete missing API route docs

- `id`: `docs-03`
- `seq`: `03`
- `title`: Document missing generate history resume GitHub routes
- `status`: `pending`
- `depends_on`: [`docs-01`]
- `parallel`: `false`
- `suggested_role`: `Implementer`
- `deliverables`:
  - `docs/api/endpoints/generate.md`
  - `docs/api/endpoints/history.md`
  - `docs/api/endpoints/resume.md`
  - `docs/api/endpoints/github.md`
  - `docs/api/index.md`
- `context_files`: [`docs/samuel-cleanup-explore-consolidated.md`]
- `reference_files`: [`backend/app/routers/generate.py`, `backend/app/routers/history.py`, `backend/app/routers/github.py`, `backend/app/routers/resume.py`]
- `acceptance_criteria`:
  - `generate.md` documents `POST /generate/{id}/stop` per `backend/app/routers/generate.py:243`, `POST /generate/{id}/retry` per `backend/app/routers/generate.py:273`, `GET /generate/{id}/preview-html` per `backend/app/routers/generate.py:421`; download section states `inline` default and `attachment` only with `?download=true|1` per `backend/app/routers/generate.py:368-369`; request table adds `ats_threshold` (None/0 = single-pass) and `ats_max_iterations` (5-7) per `backend/app/schemas/__init__.py:54-55`.
  - `history.md` documents `PATCH /history/{id}` per `backend/app/routers/history.py:55` and `DELETE /history/{id}` per `backend/app/routers/history.py:82`; list response notes full `GenerationResponse` shape (includes `rewritten_resume_text`) per `backend/app/routers/history.py:19-33`, correcting the omits-text claim at `docs/api/endpoints/history.md:38`.
  - `resume.md` documents `DELETE /resume/resumes/{id}` per `backend/app/routers/resume.py:132`.
  - `github.md:58` corrected to `order_by last_push desc nulls_last` per `backend/app/routers/github.py:74` (not creation date).
  - `docs/api/index.md:27-44` quick-ref table includes all seven generate/history/resume routes above.
- `verify`: Cross-check each new section header against the `@router` lines cited; curl examples use exact paths.

### docs-04 — Correct structure and endpoint tables

- `id`: `docs-04`
- `seq`: `04`
- `title`: Correct structure tables and route counts
- `status`: `pending`
- `depends_on`: [`docs-03`]
- `parallel`: `true`
- `suggested_role`: `Implementer`
- `deliverables`:
  - `docs/README.md`
  - `docs/api/index.md`
- `context_files`: [`docs/samuel-cleanup-explore-consolidated.md`]
- `reference_files`: [`backend/app/routers/generate.py`, `backend/app/routers/history.py`, `frontend/src/app/globals.css`]
- `acceptance_criteria`:
  - `docs/README.md:11-28` lists all seven routers (`auth`, `github`, `resume`, `generate`, `history` + health), `services/` additions, `utils/pdf_*` helpers, `constants.py` if present, and correct `globals.css` path plus `css/` split where applicable.
  - EventSource steps use `rewrite_N`/`ats_N` naming where the frontend actually emits them; no invented step names.
  - No conflict with `docs-03`: only table rows and directory tree touched, not endpoint prose.
- `verify`: Diff shows only `docs/README.md` tree/table plus `docs/api/index.md` resource-group table.

### docs-05 — Sync types.ts TSDoc with Pydantic nullability

- `id`: `docs-05`
- `seq`: `05`
- `title`: Sync frontend types TSDoc with Pydantic schemas
- `status`: `pending`
- `depends_on`: `[]`
- `parallel`: `true`
- `suggested_role`: `Implementer`
- `deliverables`:
  - `frontend/src/lib/types.ts`
- `context_files`: [`docs/samuel-cleanup-explore-consolidated.md`]
- `reference_files`: [`backend/app/schemas/__init__.py`, `frontend/src/lib/types.ts`]
- `acceptance_criteria`:
  - TSDoc-only edit (no type logic change): `Repository.topics`/`languages`/`last_push` marked nullable to match `backend/app/schemas/__init__.py:25-26`; `Generation.ats_report` documented as `{score, details, raw_report}` dict per `backend/app/orchestrator.py:261` (not `ATSReport` with `issues/warnings`), `ats_scores`/`iterations`/`ats_exit_reason` nullability matches `backend/app/schemas/__init__.py:98-102`.
  - Dead `StepEvent`/`DoneEvent`/`target_jd`/`has_openrouter_key` in `frontend/src/lib/types.ts:35,67-82` annotated `@deprecated` or `@remarks unused — pending dead-code removal`, not deleted.
  - `pnpm run lint` passes for the touched file (type-only comment change).
- `verify`: `git diff --stat` shows only `frontend/src/lib/types.ts`; no exported type signatures changed.

### docs-06 — Rewrite TASK.md and pdf.md fantasies

- `id`: `docs-06`
- `seq`: `06`
- `title`: Rewrite TASK and PDF expectation docs
- `status`: `pending`
- `depends_on`: `[]`
- `parallel`: `true`
- `suggested_role`: `Implementer`
- `deliverables`:
  - `docs/llm/TASK.md`
  - `docs/exp/pdf.md`
- `context_files`: [`docs/samuel-cleanup-explore-consolidated.md`]
- `reference_files`: [`backend/app/orchestrator.py`, `backend/app/services/pdf_extractor.py`]
- `acceptance_criteria`:
  - `docs/llm/TASK.md:31,37` no longer promises interactive `rewrite this` feedback, dimension editing, or history clearing; steps match `jd_parser -> project_matcher -> resume_writer -> deterministic ATS` per `backend/app/orchestrator.py:87-142`.
  - `docs/exp/pdf.md:20-24` no longer references `b.py`/`CropBox`/`first_line_x` stream-editor; states in-place `rewrite_pdf_layout()` primary with `render_resume_to_pdf()`/WeasyPrint fallback only when no source PDF exists per `backend/app/orchestrator.py:155-163,251-257`.
  - Plain language per `writer` skill; no new features promised.
- `verify`: Grep deliverables for `b.py`, `CropBox`, `clear-history`, `dimensions`; expect zero hits.

### docs-07 — Fix version URL and rendering-priority wording

- `id`: `docs-07`
- `seq`: `07`
- `title`: Fix Python version URLs and rendering priority
- `status`: `pending`
- `depends_on`: [`docs-02`]
- `parallel`: `false`
- `suggested_role`: `Implementer`
- `deliverables`:
  - `README.md`
  - `docs/guides/getting-started.md`
- `context_files`: [`docs/samuel-cleanup-explore-consolidated.md`]
- `reference_files`: [`backend/pyproject.toml`, `backend/app/services/pdf_extractor.py`, `backend/app/services/pdf_renderer.py`]
- `acceptance_criteria`:
  - `README.md:11` states `Python 3.12` (not `3.11+`); `README.md:23` and `docs/guides/getting-started.md:14` replace `your-org/samuel` and `intelligent-username/Samuel` placeholders with the real repo URL or a clearly-marked `<owner>/<repo>` token.
  - Rendering priority states PyMuPDF in-place primary, WeasyPrint fallback (not equal alternatives), matching `rewrite_pdf_layout` primary vs `render_resume_to_pdf` fallback per `backend/app/services/pdf_renderer.py:112`.
  - `README.md:5` and layout metadata replace `semantic matching` with `LLM-ranked matching` matching `ProjectMatcherSkill` behavior.
- `verify`: Grep for `3.11`, `your-org`, `intelligent-username`, `semantic matching`; expect zero hits in deliverables.

### docs-08 — Document placeholders and fallbacks honestly

- `id`: `docs-08`
- `seq`: `08`
- `title`: Document JSON recovery and PDF fallbacks
- `status`: `pending`
- `depends_on`: [`docs-03`]
- `parallel`: `true`
- `suggested_role`: `Implementer`
- `deliverables`:
  - `docs/api/endpoints/generate.md`
  - `backend/app/routers/generate.py`
  - `backend/app/utils/llm.py`
- `context_files`: [`docs/samuel-cleanup-explore-consolidated.md`]
- `reference_files`: [`backend/app/routers/generate.py`, `backend/app/utils/llm.py`, `backend/app/orchestrator.py`]
- `acceptance_criteria`:
  - Docstring-only edits in `backend/app/routers/generate.py:381-386,513-514` (`_weasyprint_backup`, `_text_to_html`) and `extract_json` in `backend/app/utils/llm.py` describe JSON-in-markdown recovery via regex fallback per `backend/app/routers/generate.py:515-533` and debug dump filenames under `settings.debug_dir` per `backend/app/orchestrator.py:36`.
  - `generate.md` fallback callout lists: section-fallback `warning` event per `backend/app/orchestrator.py:81`, asset fallback `app/assets/resume.pdf` per `backend/app/orchestrator.py:149-153`, and `_sanitize_pdf_filename` behavior per `backend/app/routers/generate.py:500-510`.
  - No logic changed: `git diff` for the two `.py` files shows comment/docstring lines only.
- `verify`: `git diff --numstat` plus `git diff | grep "^[+-]" | grep -v "^[+-]\s*#\|^[+-]\s*\"\"\"\|^[+-]\s*///"` returns empty (no code lines changed).

## Validation

- Unique `seq`: `01,02,03,04,05,06,07,08` — no duplicates.
- Every `depends_on` references an existing id (`docs-01`, `docs-02`, `docs-03`); no self-edges; no cycles (`01,02,05,06` roots; `03` after `01`; `04,08` after `03`; `07` after `02`).
- Every subtask has >=1 deliverable and >=1 testable acceptance criterion with `file:line` grounding.
- Parallel flags respect file contention: shared `generate.md` chain is `docs-01 -> docs-03 -> docs-08`; shared `getting-started.md` chain is `docs-02 -> docs-07`; shared `index.md` chain is `docs-01 -> docs-03 -> docs-04`.

## Verification (post-implementation)

- Grep sweeps: `four LLM`, `OPENAI_API_KEY`, `SECRET_KEY`, `openssl rand -hex`, `your-org`, `intelligent-username`, `3.11`, `semantic matching`, `b.py`, `CropBox` — zero hits in `docs/`, `README.md`.
- Endpoint cross-check: every `@router` in `backend/app/routers/*.py` has a matching row in `docs/api/index.md` and a section in its endpoint file.
- SSE cross-check: every `yield {"event":` in `backend/app/orchestrator.py` appears in `docs/api/endpoints/generate.md` SSE table.
- Style: `writer` + `writing-guidelines` pass (short sentences, no AI tells); `docs-generator` structure (overview, per-endpoint request/response/curl) intact.

## To-Do

- [ ] Execute `docs-01` per its deliverables and acceptance criteria above, then show state of list
- [ ] Execute `docs-02` per its deliverables and acceptance criteria above, then show state of list
- [ ] Execute `docs-05` per its deliverables and acceptance criteria above, then show state of list
- [ ] Execute `docs-06` per its deliverables and acceptance criteria above, then show state of list
- [ ] Execute `docs-03` (needs `docs-01` done) per its section above, then show state of list
- [ ] Execute `docs-04` (needs `docs-03` done) per its section above, then show state of list
- [ ] Execute `docs-08` (needs `docs-03` done) per its section above, then show state of list
- [ ] Execute `docs-07` (needs `docs-02` done) per its section above, then show state of list
- [ ] Run Verification sweeps and endpoint/SSE cross-checks, then show final list
