# Samuel Lag Plan — Smoothness / Rough Edges (Issue #3)

## Abstract

Samuel feels laggy and unfinished in places: resume processing can freeze the server, GitHub syncing is slower than it should be, AI retries can stall for a long time, live progress can get stuck or spam the server, the dashboard re-renders too much work, and small popups and timers behave inconsistently. This plan fixes those rough edges with small, careful changes only. It does not change how Samuel looks, it does not change saved data, and it does not change what the app promises to other parts of the system. After the work, pages should feel responsive, progress should stay alive and then cleanly stop, and repeated actions should be fast.

## Context & Constraints

- Sources: `docs/samuel-cleanup-context.md`, `docs/samuel-cleanup-explore-consolidated.md` (Lag fixes 1–8).
- Skills consulted: `backend-latency-profiler-helper` (N+1, slow-endpoint roadmap), `vercel-react-best-practices` (`async-parallel`, `rerender-memo`, `bundle-dynamic-imports`, `client-event-listeners`, `js-cache-function-results`), `frontend-ui` (review-only, no theme change), `web-design-guidelines` (audit only), `error-triage` (CancelledError vs symptom, root-frame analysis), `spec-creator` (acceptance-criteria framing), `agent-orchestration-planner` (atomic subtask schema + DAG + barrier gates).
- Invariants: minimal surgical diffs; preserve API/SSE contracts (`POST /generate/`, `GET /generate/{id}/stream` events `step-start/step-done/ats_loop/ats_evaluation/ats_stagnation/output/done/step-error`); no Neumorphic redesign (refer `docs/guides/style-guide.html`); no DB migration (no `pear` codeword); no `pt/`; no gitignored except `docs/` + git commits; `stop_on_failure` + `report_first`; mock LLM/GitHub in tests (`uv run pytest`); `pnpm` only; `EventSource` SSE.

## Architecture Notes (read-only findings grounding the plan)

- Blocking I/O on event loop: `backend/app/services/pdf_extractor.py:24,47` (`fitz.open` sync); `backend/app/skills/jd_parser.py:10,27`, `project_matcher.py:9,46`, `resume_writer.py:11,42` (`SKILL_FILE.read_text()` per call); `services/degraded_extractor.py:54,65,78`, `services/ats_config_loader.py:14` (sync JSON reads).
- GitHub N+1: `backend/app/routers/github.py:46-60` — one `select(Repository).where(user_id, github_repo_id)` per repo inside `for repo_info in repos_data` (100 repos = 100 sequential SELECTs + 1 commit).
- LLM chain unbounded: `backend/app/utils/llm.py:73-195` — `_RETRYABLE` + `for attempt in range(3)` per model × 4 Groq + 5 OpenRouter ≈ 27 serial attempts × `timeout=120`; no overall `wait_for`; `CancelledError` swallowed by `except HTTPError`/`Exception` paths; `embed()` dead but out of scope for lag (Issue #1).
- Orchestrator preamble ×3 + serial fetches: `backend/app/orchestrator.py:68-76,192-199,277-284` (`_get_generation` + `select(User)` + `extract_sections` + `_get_repos` repeated in `run`, `run_with_ats_loop`); `_get_repos:449-453` unbounded `order_by(stars)` full-table load.
- SSE zombie poll: `frontend/src/hooks/useGenerationStream.ts:246-252` — `onerror → setInterval(checkStatus,2500)` never backs off, no `AbortController`, `pollInterval` leaked across reconnects; canonical helper `frontend/src/lib/api.ts:87-89` (`createGenerationStream`) unused by hook (hardcoded `new EventSource` at `:71-74`); `parseEventData:76-88` regex-replace fallback hides contract breaks.
- Dashboard waste: `frontend/src/app/dashboard/page.tsx:91-95` writes `sessionStorage` every keystroke; `:97-103` `visibleRepos` filter+sort recomputed every render; `:105-155` `Promise.all` fetch is fine but `visibleResumes:159` unmemoized; `Borromean3DViewer.tsx:63-64` forces `pixelRatio ≥2.5` + `2048×2048` canvas + `TubeGeometry(512,32)` + `uSegs 240/vSegs 64` always mounted at 360px, `requestAnimationFrame` never pauses offscreen.
- Helper triplication: `routers/generate.py:_text_to_html (~513-587)` ≈ `services/pdf_renderer.py:18-90` (~90% identical); filename sanitize + fallback-PDF logic scattered; no `lru_cache`.
- Magic numbers + timers: `JD_MAX 24000` hardcoded in `routers/generate.py:74-81` + `dashboard/page.tsx:76`; `70/100` clamp at `dashboard/page.tsx:63`; `5..7` ATS iterations, `2.5s` poll, `2000ms` copied-toast (`results/[id]/page.tsx:120`), rename-timeout (`history/GenerationCard.tsx:53`), no `useRef` cleanup in several spots; `Esc` present in `AtsDetailsModal:27`, `ResumeUploadSection:53`, `ResumePreviewer:67-74`, `GenerationCard:112` but missing in `JobDescriptionDrawer` + `RepoDetailModal`.

## Atomic Subtasks (agent-orchestration-planner schema)

### `lag-01` — Offload blocking PDF/font/file I/O off event loop
- status: pending
- depends_on: []
- parallel: true
- deliverables:
  - `backend/app/services/pdf_extractor.py`
  - `backend/app/skills/jd_parser.py`
  - `backend/app/skills/project_matcher.py`
- reference_files: `backend/app/skills/resume_writer.py`, `backend/app/utils/pdf_layout.py`, `backend/app/utils/pdf_fonts.py`
- changes:
  - Wrap `fitz.open` + `page.get_text()` (`extract_text_from_pdf`) and `rewrite_pdf_layout` body in `await asyncio.to_thread(...)`; keep async signatures unchanged.
  - Cache skill prompts at import: `_PROMPT = SKILL_FILE.read_text()` once per module (do not re-read per request); add `@lru_cache` on degraded/ATS JSON loaders only if touched by lag path.
  - No new threads, no new deps.
- acceptance:
  - Event loop never blocks >50ms on PDF/skill read (manual: concurrent `POST /generate/` + `GET /github/repos` stays responsive; `ruff` clean).
  - Byte-identical PDF/text output on fixture resume before/after.
  - No API/SSE contract change.

### `lag-02` — Fix GitHub sync N+1 with bulk select
- status: pending
- depends_on: []
- parallel: true
- deliverables:
  - `backend/app/routers/github.py`
- reference_files: `backend/app/models/repository.py`, `backend/app/services/github_graphql.py`
- changes:
  - Replace per-repo `select(...where(user_id, github_repo_id))` loop with single `select(Repository).where(Repository.user_id==user.id, Repository.github_repo_id.in_(ids))`, build `existing_by_id` dict, then update-or-add in memory + single `commit()`. Preserve `last_fetched_at=now` semantics and `order_by(last_push.desc().nulls_last())` in `list_repos`.
- acceptance:
  - N+1 eliminated: sync of 100 repos issues ≤3 SQL statements (1 User select + 1 bulk Repository select + 1 commit), verified by SQLAlchemy echo/log count in test with mocked `fetch_user_repos`.
  - Sync result identical (same upserted rows, same `avatar_url` response).
  - No DB migration; no REST→GraphQL change.

### `lag-03` — Bound LLM fallback chain with overall timeout
- status: pending
- depends_on: []
- parallel: true
- deliverables:
  - `backend/app/utils/llm.py`
- reference_files: `backend/app/skills/jd_parser.py`, `backend/app/orchestrator.py`
- changes:
  - Groq-first + max 1 OpenRouter fallback model attempt per `complete()` (cap total attempts; keep `GROQ_MODELS`/`OPENROUTER_MODELS` order, do not reorder vendor priority).
  - Wrap `complete()` in `asyncio.wait_for(timeout=90)` (or settings-driven if already present; do not add new env var); let `asyncio.CancelledError` propagate (re-raise, do not log-and-swallow); keep per-request `timeout=120` httpx but rely on overall bound.
  - Per `error-triage`: treat timeout as root frame, retryable 429/5xx as symptom — no extra retry loops.
- acceptance:
  - Worst-case `complete()` wall time ≤95s (measured with mocked httpx timeouts), down from ~27×120s serial; `CancelledError` propagates to orchestrator/SSE `step-error` instead of hanging.
  - Success-path output unchanged (same model priority on happy path).
  - No prompt-template change.

### `lag-04` — Dedupe orchestrator preamble and parallelize fetches
- status: pending
- depends_on: [`lag-02`]
- parallel: false
- deliverables:
  - `backend/app/orchestrator.py`
- reference_files: `backend/app/services/pdf_extractor.py`, `backend/app/models/repository.py`
- changes:
  - Extract `_load_context()` helper doing `_get_generation()` once; `asyncio.gather` user-fetch + repos-fetch where independent; reuse across `run`/`run_with_ats_loop` (delete 2 of 3 preamble copies).
  - Cap matcher input to top 30 by `stars` (slice after `_get_repos`, do not change `_get_repos` ordering contract).
- acceptance:
  - Preamble code appears once; generation start latency reduced by overlap (user+repos fetched concurrently, verified by test with mocked DB latency).
  - Matcher receives ≤30 repos; SSE event order unchanged (`step-start jd_parser → step-done …`).
  - No DB schema change.

### `lag-05` — Harden SSE client (kill zombie poll, backoff, reuse helper)
- status: pending
- depends_on: []
- parallel: true
- deliverables:
  - `frontend/src/hooks/useGenerationStream.ts`
  - `frontend/src/lib/api.ts`
- reference_files: `frontend/src/app/dashboard/results/[id]/page.tsx`
- changes:
  - Reuse `createGenerationStream(generationId)` from `lib/api.ts` instead of inline `new EventSource`; add `AbortController` + cleanup closing both ES and controller on unmount/`done`.
  - Replace fixed `setInterval(checkStatus,2500)` zombie poll with exponential backoff (1s→2s→4s…max 30s, jitter allowed) + clear on `step-start/step-done/done`; ensure single outstanding `fetchGeneration` fallback.
  - Keep `parseEventData` but remove silent regex-repair for non-JSON (return `{}` + `console.warn`); preserve all existing event listeners and state shapes.
- acceptance:
  - Zombie poll cleared: closing tab/unmount issues 0 further `GET /history/{id}`; network tab shows ≤1 fallback poll per backoff window, backoff intervals 1s/2s/4s verified.
  - Disconnect→reconnect recovers without duplicate `steps`; `done`/`step-error` still close stream exactly once.
  - No SSE contract change; no theme change.

### `lag-06` — Memoize dashboard, debounce persistence, lazy-load 3D
- status: pending
- depends_on: []
- parallel: true
- deliverables:
  - `frontend/src/app/dashboard/page.tsx`
  - `frontend/src/components/Borromean3DViewer.tsx`
- reference_files: `frontend/src/lib/api.ts`, `frontend/src/components/DashboardSidebar.tsx`
- changes (per `vercel-react-best-practices`: `rerender-memo`, `bundle-dynamic-imports`, `client-event-listeners`):
  - `useMemo` for `visibleRepos`/`visibleResumes`; debounce `sessionStorage.setItem("samuel_job_desc")` 500ms with `useRef` timer + cleanup (same for `localStorage` threshold write if trivial).
  - `next/dynamic(() => import("@/components/Borromean3DViewer"), { ssr:false })` lazy-load; cap `getOptimalPixelRatio` to `min(devicePixelRatio,2)`; pause `requestAnimationFrame` via `IntersectionObserver` when offscreen; reduce default `height` instance 360→140 where used as decorative loader (keep prop API).
- acceptance:
  - Typing JD does not re-sort/filter repos per keystroke (React profiler: `visibleRepos` recompute only when `repos/removedIds` change); `sessionStorage` writes ≤2/sec during fast typing.
  - Initial dashboard JS excludes `three` (dynamic chunk); offscreen 3D emits 0 `rAF`; FPS stable on scroll.
  - No visual/theme change (same Neumorphic tokens, same layout).

### `lag-07` — Dedupe text→HTML, filename, fallback-PDF helpers
- status: pending
- depends_on: [`lag-01`]
- parallel: false
- deliverables:
  - `backend/app/services/pdf_renderer.py`
  - `backend/app/routers/generate.py`
- reference_files: `backend/app/utils/llm.py`
- changes:
  - Promote `services/pdf_renderer._text_to_html` to canonical; `routers/generate.py` imports and deletes its fork (preserve import graph, update call sites). Add `@lru_cache(maxsize=128)` on pure `_text_to_html` + filename-sanitize helper; centralize fallback-PDF bytes path.
- acceptance:
  - Single `_text_to_html` definition (`grep -r "def _text_to_html"` returns 1); cached repeat call hits `lru_cache` (cache_info hit ≥1 on double-render test).
  - Rendered HTML/PDF bytes identical on fixtures.
  - No new public endpoint.

### `lag-08` — Centralize constants, cleanup timers, add missing Esc
- status: pending
- depends_on: [`lag-05`, `lag-06`]
- parallel: false
- deliverables:
  - `backend/app/constants.py`
  - `frontend/src/app/dashboard/page.tsx`
  - `frontend/src/components/RepoDetailModal.tsx`
- reference_files: `frontend/src/components/JobDescriptionDrawer.tsx`, `backend/app/routers/generate.py`, `frontend/src/components/history/GenerationCard.tsx`
- changes:
  - Move `JD_MAX=24000`, ATS clamp `70/100`, iteration bounds `5..7`, SSE/poll timeouts into `backend/app/constants.py` (backend) + single `frontend/src/lib/constants.ts` only if already exists — otherwise local `const` export in `dashboard/page.tsx` reused by `JobDescriptionInput` (do not create new barrel file).
  - `useRef` timers with `clearTimeout/clearInterval` cleanup for copied-toast/rename/persistence; add `Esc`-to-close + focus-return in `RepoDetailModal` + `JobDescriptionDrawer` mirroring `AtsDetailsModal:27` pattern.
- acceptance:
  - `grep -r "24000"` returns only constants + 2 import sites; `grep -r "setTimeout|setInterval"` each paired with cleanup in same file.
  - `Esc` closes both modals and returns focus; keyboard audit passes; no theme change.

## DAG & Batches

```text
Batch 1 (parallel, no deps — dispatch together):
  lag-01 ─┐
  lag-02 ─┼─► barrier gate (verify: ruff + pytest mocked + tsc)
  lag-03 ─┤
  lag-05 ─┤
  lag-06 ─┘

Batch 2 (dependent — after Batch 1 barrier):
  lag-04 (after lag-02)
  lag-07 (after lag-01)

Batch 3 (final — after Batch 2 barrier):
  lag-08 (after lag-05, lag-06)

Auditor last: standards + SSE contract + no-theme + no-DB-migration check.
```

- Validation: seqs `lag-01..lag-08` unique; every `depends_on` references existing id; zero cycles (Batch 1 → Batch 2 → Batch 3, no back-edges); each subtask has 1–3 deliverables + measurable acceptance.
- Contracts preserved: HTTP status codes, `GenerationResponse` shape, SSE event names/payload keys, `RepositoryResponse` ordering.

## Verification (per subtask + global)

- Backend: `uv run pytest -q` with mocked LLM (`httpx`) + mocked `fetch_user_repos`; `ruff check` clean; SQL statement count assertion for `lag-02`; wall-time assertion (≤95s) for `lag-03` with fake clock/mocked sleeps.
- Frontend: `pnpm tsc --noEmit`, `pnpm lint` (if present); manual: throttle network, kill SSE mid-run (backoff + resume), type JD fast (debounce), background tab (rAF paused), `Esc` on each modal; confirm no Neumorphic token diff (`git diff -- globals.css` empty unless unrelated).
- Global: `git status/diff/log` review; no `pt/` touch; no `.env`/secrets; no migration files; SSE event sequence matches `docs/samuel-cleanup-context.md §5`.

## Risks

- `to_thread` misuse hiding exceptions → mitigate by awaiting directly, no `ensure_future` without await.
- Capping LLM attempts could surface 400s faster → acceptable: fail fast to `step-error` per `stop_on_failure` instead of silent 4-min hang.
- Top-30 cap could drop a relevant repo → acceptable per consolidated plan; stars ordering already the product contract.
- `three` lazy-load flash → skeleton placeholder same size, no layout shift (CLS <0.1).

## To-Do
- [ ] Execute `lag-01` per §lag-01 (to_thread + cached skill prompts) — see implementation details in §Atomic Subtasks above
- [ ] Execute `lag-02` per §lag-02 (GitHub bulk select, N+1 eliminated) — see implementation details in §Atomic Subtasks above
- [ ] Execute `lag-03` per §lag-03 (bounded LLM chain + CancelledError propagate) — see implementation details in §Atomic Subtasks above
- [ ] Execute `lag-04` per §lag-04 (orchestrator dedupe + gather + top-30 cap) — see implementation details in §Atomic Subtasks above
- [ ] Execute `lag-05` per §lag-05 (SSE harden, zombie poll cleared, backoff) — see implementation details in §Atomic Subtasks above
- [ ] Execute `lag-06` per §lag-06 (memoize + debounce 500ms + lazy 3D + rAF pause) — see implementation details in §Atomic Subtasks above
- [ ] Execute `lag-07` per §lag-07 (canonical text→HTML + lru_cache) — see implementation details in §Atomic Subtasks above
- [ ] Execute `lag-08` per §lag-08 (constants + timer cleanup + Esc handlers) — see implementation details in §Atomic Subtasks above
