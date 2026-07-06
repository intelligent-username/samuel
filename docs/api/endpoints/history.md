# History

Endpoints for browsing and retrieving past resume generations. All endpoints require authentication via the `session` cookie.

## Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/history/` | List recent generations (last 20, newest first) |
| `GET` | `/history/{id}` | Get full details for a specific generation |

## List Generations

`GET /history/`

Returns the 20 most recent generations for the authenticated user, ordered by creation date (newest first).

### Response

#### 200 OK

```json
[
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "status": "completed",
    "rewritten_resume_text": null,
    "ats_report": {
      "score": 85,
      "warnings": ["Missing industry keywords: kubernetes, terraform"]
    },
    "created_at": "2025-07-02T10:30:00Z",
    "completed_at": "2025-07-02T10:32:15Z"
  }
]
```

The list view omits `rewritten_resume_text` for brevity. Use `GET /history/{id}` for the full record.

#### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### Example

```bash
curl -X GET "http://localhost:8000/history/" \
  -H "Cookie: session=..."
```

## Get Generation Details

`GET /history/{generation_id}`

Returns the full generation record including the rewritten resume text and the ATS report.

### Path Parameters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `generation_id` | UUID | The generation ID |

### Response

#### 200 OK

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "completed",
  "rewritten_resume_text": "# John Doe\n\n## Skills\nPython, TypeScript, React, FastAPI...\n\n## Projects\n...",
  "ats_report": {
    "score": 85,
    "warnings": ["Missing industry keywords: kubernetes, terraform"],
    "improvements": ["Add Kubernetes to skills section"]
  },
  "created_at": "2025-07-02T10:30:00Z",
  "completed_at": "2025-07-02T10:32:15Z"
}
```

#### 404 Not Found

```json
{
  "detail": "Generation not found"
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
curl -X GET "http://localhost:8000/history/660e8400-e29b-41d4-a716-446655440001" \
  -H "Cookie: session=..."
```
