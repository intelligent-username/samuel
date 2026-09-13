# Samuel Cleanup - Explore Consolidated (2026-09-13)

Source: 3 parallel Explore agents (read-only, no bash, no pt/, no gitignored). Full raw outputs in session history.

## Dead Code (Issue 1) - Top candidates P1-P8
- P1 Kill test-only ATS shadow stack: services/matching_engine.py (evaluate_match 386 lines, zero prod importers), degraded_extractor.py (380 lines test-only), ats_config_loader.py dead loaders + config/*.json
- P2 Unify Markdown->HTML + kill WeasyPrint backup: routers/generate.py _text_to_html 513-587 vs services/pdf_renderer.py 18-90 (~90% identical), _weasyprint_backup 381 dead
- P3 Dedupe orchestrator triple-preamble + PDF fallback: orchestrator.py run 61-184 (124 lines), run_with_ats_loop 186-427 (242 lines), 3x preamble + 4x fallback chain
- P4 Remove dead ATS surface: services/ats.py SectionHeaderCriterion 127 dead, skills/ats_checker.py 19 lines dead, app/ats.py shim
- P5 Prune LLM/embedding/config: utils/llm.py embed 197 dead, Vector(1536) write-never, config openrouter_key alias, log_level/debug_retention_hours unread
- P6 Delete orphan frontend: BorromeanBanner 292 lines, BorromeanLogo 46 lines, DashboardGrid 18 lines (all zero importers)
- P7 Paper-Sheet vs PDF fork: ResumePaperSheet 241 lines + resume-parser.ts 132 lines dead if previewer stays PDF-only, PinIcon dead
- P8 Redirect stubs + dead exports: 5 redirect stubs, api.ts createGenerationStream/getPreviewHtmlUrl dead, types.ts StepEvent/DoneEvent/target_jd/has_openrouter_key dead, 6 barrel index.ts
- Contradictions: ats_max_iterations clamp vs raise, _text_to_html divergence, ATS score deterministic vs LLM-adapter, threshold None/0 duplication

## Docs (Issue 2) - Top fixes 1-8
1. Rewrite ATS docs + deprecate ats_checker.md (4 LLM -> 3 LLM + deterministic loop, SSE events warning/ats_evaluation/ats_loop/ats_stagnation/output/done)
2. Fix env vars: OPENAI_API_KEY->OPENROUTER_API_KEY (+OPENROUTER_KEY/GROQ_API_KEY), SECRET_KEY->SESSION_SECRET, add ATS_* / SECURE_COOKIE / DEBUG_*, fix Fernet command
3. Complete API routes: missing POST /generate/{id}/stop|retry, GET preview-html, PATCH|DELETE history, DELETE resume, fix download inline vs attachment, history includes full text, github ordering by last_push
4. Correct structure tables: services/ + utils/pdf_* + constants.py, globals.css path + css/ split, list all 7 routes, EventSource rewrite_N/ats_N
5. Sync types.ts with Pydantic (User/Repository/Resume/Generation/ATSReport nullability + breakdown/details)
6. Rewrite docs/llm/TASK.md + docs/exp/pdf.md (remove feedback-rewrite/dimensions/clear-history fantasy, b.py/CropBox fantasy)
7. Fix Python 3.11->3.12, repo URL placeholders, PyMuPDF primary / WeasyPrint fallback, semantic->LLM-ranked
8. Document placeholders + fallbacks honestly (extract_json/regex recovery, debug file names)

## Lag (Issue 3) - Top fixes 1-8
1. Offload blocking PDF/font/file I/O off event loop (asyncio.to_thread, cache SKILL_FILE reads, lru_cache fallback)
2. Fix GitHub sync N+1 (bulk select where in_, 100 sequential SELECTs -> 1)
3. Bound LLM fallback chain (27 serial attempts x120s -> Groq-first + 1 OpenRouter + overall wait_for + CancelledError propagate)
4. Dedupe orchestrator preamble + parallelize fetches (gather user+repos, cap top 30 stars)
5. Harden SSE client (kill zombie 2.5s poll, exponential backoff, AbortController, reuse helper)
6. Memoize dashboard + debounce persistence + lazy 3D (useMemo visibleRepos/Resumes, debounce sessionStorage 500ms, lazy Borromean3DViewer, pause rAF, reduce 140px instance)
7. Dedupe text->HTML + filename + fallback-PDF helpers (single canonical modules + lru_cache)
8. Centralize constants + cleanup timers + missing Esc handlers (JD_MAX 24000, 70/100, 5..7, timeouts, useRef timers)

Invariants: no pt/, no gitignored (except docs/ + git commits allowed), no DB migrations (no pear), no Neumorphic redesign, minimal surgical diffs, stop_on_failure/report_first.
