# Generate

Endpoints for creating resume generations and streaming results. All endpoints require authentication via the `session` cookie.

## Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/generate/` | Start a new resume generation |
| `GET` | `/generate/{id}/stream` | SSE stream with real-time generation progress |
| `POST` | `/generate/{id}/stop` | Stop a running generation |
| `POST` | `/generate/{id}/retry` | Reset a failed generation to pending |
| `GET` | `/generate/{id}/preview-html` | Preview the rewritten resume as styled HTML |
| `GET` | `/generate/{id}/download` | Download the rewritten resume as a PDF |

## Start Generation

`POST /generate/`

Creates a new generation record in `pending` status and returns its ID. The frontend then connects to the SSE stream to run the skill chain. Validates resume ownership and API key availability before creating the record.

### Request Body

```json
{
  "resume_id": "550e8400-e29b-41d4-a716-446655440000",
  "job_description": "We are looking for a senior software engineer with 5+ years of experience in Python..."
}
```

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `resume_id` | UUID | Yes | ID of an uploaded resume (must belong to the user) |
| `job_description` | string | Yes | Target job description text, 10-24000 chars |
| `ats_threshold` | int or null | No | ATS target 0-100. None or 0 means single pass with no retry loop |
| `ats_max_iterations` | int or null | No | Max ATS retry iterations, 5-7 |

### Response

#### 200 OK

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "pending",
  "rewritten_resume_text": null,
  "ats_report": null,
  "created_at": "2025-07-02T10:30:00Z",
  "completed_at": null
}
```

#### 400 Bad Request

OpenRouter API key is not set.

```json
{
  "detail": "OpenRouter API key not set. Save it first via POST /resume/key"
}
```

#### 404 Not Found

Resume not found or belongs to another user.

```json
{
  "detail": "Resume not found"
}
```

#### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### Example

```bash
curl -X POST "http://localhost:8000/generate/" \
  -H "Cookie: session=..." \
  -H "Content-Type: application/json" \
  -d '{
    "resume_id": "550e8400-e29b-41d4-a716-446655440000",
    "job_description": "We are looking for a senior software engineer with 5+ years of experience in Python..."
  }'
```

## Stream Generation

`GET /generate/{generation_id}/stream`

Returns a Server-Sent Events (SSE) stream that runs the rewrite pipeline and emits progress events in real time. The pipeline uses three LLM skills (`jd_parser`, `project_matcher`, `resume_writer` per `backend/app/orchestrator.py:87-127`) plus a deterministic ATS check via `ATS()` per `backend/app/orchestrator.py:131-142`. Each LLM step emits `step-start` and `step-done` events. The ATS stage emits `ats_evaluation` per run and, when a threshold is set, `ats_loop` and `ats_stagnation` events. The stream ends with `output` and `done` events.

### Path Parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `generation_id` | UUID | The generation ID returned from `POST /generate/` |

### SSE Events

| Event | Payload | Description |
| :--- | :--- | :--- |
| `step-start` | `{"step": "jd_parser"}` | A pipeline step has begun |
| `step-done` | `{"step": "jd_parser"}` | A pipeline step has completed |
| `warning` | `{"message": "..."}` | Section fallback notice when Skills/Projects headers are missing |
| `ats_evaluation` | `{"score": 82, "threshold": 80, "will_retry": false, "iteration": 1}` | Deterministic ATS score for one iteration |
| `ats_loop` | `{"iteration": 2, "score": 78, "threshold": 80}` | Retry iteration started because score is below threshold |
| `ats_stagnation` | `{"window": 3, "min_gain": 0.03, "scores_slice": [...]}` | Loop stopped early because scores stopped improving |
| `output` | rewritten resume text | Final rewritten resume text |
| `done` | `{"generation_id": "...", "ats_score": 85, "ats_scores": [...], "exit_reason": "...", "iterations": [...]}` | Pipeline completed. `exit_reason` is one of `single_pass`, `threshold_met`, `stagnation`, `max_iterations` |
| `error` | `{"message": "..."}` | An error occurred during generation |

`exit_reason` values: `single_pass` when `ats_threshold` is None or 0, `threshold_met` when score reaches threshold, `stagnation` when early break triggers, `max_iterations` when the loop hits `ats_max_iterations` (5-7).

### Steps

| Step | Name | Type | Purpose |
| :--- | :--- | :--- | :--- |
| 1 | `jd_parser` | LLM | Extract structured requirements from the job description |
| 2 | `project_matcher` | LLM | Rank cached GitHub repos against the JD requirements |
| 3 | `resume_writer` | LLM | Rewrite the skills and projects sections of the resume |
| 4 | `ats_checker` | Deterministic | Score the rewritten resume with `ATS()` and retry until threshold or max iterations |

### Example

```bash
curl -X GET "http://localhost:8000/generate/660e8400-e29b-41d4-a716-446655440001/stream" \
  -H "Cookie: session=..."
```

Stream output:

```
event: step-start
data: {"step": "jd_parser"}

event: step-done
data: {"step": "jd_parser"}

event: step-start
data: {"step": "project_matcher"}

event: step-done
data: {"step": "project_matcher"}

event: step-start
data: {"step": "resume_writer"}

event: step-done
data: {"step": "resume_writer"}

event: step-start
data: {"step": "ats_checker"}

event: step-done
data: {"step": "ats_checker"}

event: done
data: {"generation_id": "660e8400-e29b-41d4-a716-446655440001", "ats_score": 85}
```

## Stop Generation

`POST /generate/{generation_id}/stop`

Stops a running generation, cancels the active task, and marks the record as failed.

```bash
curl -X POST "http://localhost:8000/generate/660e8400-e29b-41d4-a716-446655440001/stop" \
  -H "Cookie: session=..."
```

## Retry Generation

`POST /generate/{generation_id}/retry`

Resets a failed generation to `pending` so it can run again. Clears rewritten text, ATS report, and completion time.

```bash
curl -X POST "http://localhost:8000/generate/660e8400-e29b-41d4-a716-446655440001/retry" \
  -H "Cookie: session=..."
```

## Preview HTML

`GET /generate/{generation_id}/preview-html`

Returns styled HTML of the rewritten resume for the in-app previewer. Requires rewritten text to exist.

```bash
curl -X GET "http://localhost:8000/generate/660e8400-e29b-41d4-a716-446655440001/preview-html" \
  -H "Cookie: session=..."
```

## Download PDF

`GET /generate/{generation_id}/download`

Downloads the rewritten resume as a PDF document. Requires the generation to have a `completed` status.

### Path Parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `generation_id` | UUID | The generation ID |

### Response

#### 200 OK

Returns a PDF file with `Content-Type: application/pdf`. Display defaults to `inline`. It uses `attachment` only with `?download=true` or `?download=1`. The filename comes from the generation title or falls back to `generated_resume.pdf`.

#### 400 Bad Request

Generation is not completed or no rewritten text is available.

```json
{
  "detail": "Generation not completed yet"
}
```

#### 404 Not Found

```json
{
  "detail": "Generation not found"
}
```

### Example

```bash
curl -X GET "http://localhost:8000/generate/660e8400-e29b-41d4-a716-446655440001/download" \
  -H "Cookie: session=..." \
  -o rewritten-resume.pdf
```

## Fallbacks

The pipeline degrades in three known ways. Each one is logged and visible in the stream or download.

- Section fallback: when Skills or Projects headers are missing, the orchestrator emits a `warning` event and rewrites from full text. See `backend/app/orchestrator.py:81`.
- PDF asset fallback: when the record has no PDF bytes, the download path rewrites the bundled `app/assets/resume.pdf` instead of failing. See `backend/app/routers/generate.py:348-361`.
- Filename fallback: `_sanitize_pdf_filename` strips path and reserved chars and falls back to `generated_resume.pdf` when the title is empty. See `backend/app/routers/generate.py:460-470`.
