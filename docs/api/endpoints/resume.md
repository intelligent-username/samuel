# Resume

Endpoints for uploading PDF resumes and managing OpenRouter API keys. All endpoints require authentication via the `session` cookie.

## Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/resume/upload` | Upload a PDF resume and extract its text |
| `POST` | `/resume/key` | Save an encrypted OpenRouter API key |
| `GET` | `/resume/key-status` | Check whether an API key is available |
| `GET` | `/resume/resumes` | List all uploaded resumes |

## Upload Resume

`POST /resume/upload`

Uploads a PDF file, extracts its text content using PyMuPDF, and stores both the file and the extracted text in the database. Accepts only PDF files up to 10 MB.

### Request

Multipart form data with a single field `file`.

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `file` | file | Yes | PDF file, max 10 MB |

### Response

#### 200 OK

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "original_filename": "resume.pdf",
  "extracted_text": "John Doe\nSoftware Engineer\n...",
  "created_at": "2025-07-02T10:30:00Z"
}
```

#### 400 Bad Request

File is not a PDF or text extraction failed.

```json
{
  "detail": "Only PDF files are supported"
}
```

#### 413 Payload Too Large

File exceeds 10 MB.

```json
{
  "detail": "File too large (max 10 MB)"
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
curl -X POST "http://localhost:8000/resume/upload" \
  -H "Cookie: session=..." \
  -F "file=@resume.pdf"
```

## Save API Key

`POST /resume/key`

Saves the user's OpenRouter API key in the database. The key is encrypted at rest using Fernet symmetric encryption with `ENCRYPTION_KEY` from the environment. The key is never returned in any response.

### Request Body

```json
{
  "api_key": "sk-or-v1-..."
}
```

### Response

#### 200 OK

```json
{
  "message": "API key saved"
}
```

#### 400 Bad Request

```json
{
  "detail": "api_key is required"
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
curl -X POST "http://localhost:8000/resume/key" \
  -H "Cookie: session=..." \
  -H "Content-Type: application/json" \
  -d '{"api_key": "sk-or-v1-..."}'
```

## Check API Key Status

`GET /resume/key-status`

Checks whether an OpenRouter API key is available for use. Returns two booleans: `has_key` (key exists in the user record or environment) and `env_configured` (key exists in the server environment variables). Never returns the key itself.

### Response

#### 200 OK

```json
{
  "has_key": true,
  "env_configured": false
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
curl -X GET "http://localhost:8000/resume/key-status" \
  -H "Cookie: session=..."
```

## List Resumes

`GET /resume/resumes`

Returns all uploaded resumes for the authenticated user, ordered by upload date (newest first). Each entry includes the extracted text.

### Response

#### 200 OK

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "original_filename": "resume.pdf",
    "extracted_text": "John Doe\nSoftware Engineer\n...",
    "created_at": "2025-07-02T10:30:00Z"
  }
]
```

#### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### Example

```bash
curl -X GET "http://localhost:8000/resume/resumes" \
  -H "Cookie: session=..."
```
