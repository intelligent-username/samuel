# Generate

Endpoints for creating resume generations and streaming results. All endpoints require authentication via the `session` cookie.

## Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/generate/` | Start a new resume generation |
| `GET` | `/generate/{id}/stream` | SSE stream with real-time generation progress |
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
| `job_description` | string | Yes | Target job description text, minimum 10 characters |

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

Returns a Server-Sent Events (SSE) stream that runs the four-step skill chain and emits progress events in real time. The stream runs the orchestrator, which calls the LLM four times sequentially. Each step emits `step-start` and `step-done` events. When all steps complete, the stream emits a `done` event.

### Path Parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `generation_id` | UUID | The generation ID returned from `POST /generate/` |

### SSE Events

| Event | Payload | Description |
| :--- | :--- | :--- |
| `step-start` | `{"step": "jd_parser"}` | A skill step has begun |
| `step-done` | `{"step": "jd_parser"}` | A skill step has completed |
| `output` | `{"step": "...", "output": {...}}` | Intermediate output from a step |
| `done` | `{"generation_id": "...", "ats_score": 85}` | All steps completed successfully |
| `error` | `{"message": "..."}` | An error occurred during generation |

### Steps

| Step | Name | Purpose |
| :--- | :--- | :--- |
| 1 | `jd_parser` | Extract structured requirements from the job description |
| 2 | `project_matcher` | Rank cached GitHub repos against the JD requirements |
| 3 | `resume_writer` | Rewrite the skills and projects sections of the resume |
| 4 | `ats_checker` | Evaluate the rewritten resume for ATS compatibility |

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

## Download PDF

`GET /generate/{generation_id}/download`

Downloads the rewritten resume as a PDF document. Requires the generation to have a `completed` status.

### Path Parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `generation_id` | UUID | The generation ID |

### Response

#### 200 OK

Returns a PDF file with `Content-Type: application/pdf` and `Content-Disposition: attachment; filename=resume.pdf`.

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
