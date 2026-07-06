# Auth

Endpoints for GitHub OAuth login, session management, and logout.

## Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/auth/login` | Get the GitHub OAuth authorization URL |
| `GET` | `/auth/callback` | Handle OAuth callback, exchange code for token, set session |
| `GET` | `/auth/me` | Return the authenticated user's profile |
| `POST` | `/auth/logout` | Clear the session cookie |

## Get Authorization URL

`GET /auth/login`

Initiates GitHub OAuth by returning a URL to redirect the user to. Sets an `oauth_state` cookie for CSRF protection.

### Response

#### 200 OK

```json
{
  "authorization_url": "https://github.com/login/oauth/authorize?client_id=...&redirect_uri=http://localhost:3000/auth/callback&scope=read:user+public_repo&state=..."
}
```

### Example

```bash
curl -X GET "http://localhost:8000/auth/login"
```

## Handle OAuth Callback

`GET /auth/callback`

Completes the OAuth flow. Validates the state parameter, exchanges the code for a GitHub access token, fetches the user profile, upserts a database record, and sets a `session` cookie.

### Query Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `code` | string | Yes | Authorization code from GitHub |
| `state` | string | Yes | CSRF token from the initial login request |

### Response

#### 200 OK

```json
{
  "message": "authenticated",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "github_id": 12345678,
    "github_username": "johndoe",
    "created_at": "2025-01-15T10:30:00Z"
  }
}
```

#### 400 Bad Request

State mismatch or code exchange failure.

```json
{
  "detail": "State mismatch -- possible CSRF"
}
```

### Example

```bash
curl -X GET "http://localhost:8000/auth/callback?code=abc123&state=def456" \
  -H "Cookie: oauth_state=def456"
```

## Get Current User

`GET /auth/me`

Returns the authenticated user's profile. Requires a valid `session` cookie.

### Response

#### 200 OK

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "github_id": 12345678,
  "github_username": "johndoe",
  "created_at": "2025-01-15T10:30:00Z"
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
curl -X GET "http://localhost:8000/auth/me" \
  -H "Cookie: session=..."
```

## Logout

`POST /auth/logout`

Clears the `session` cookie. No request body required.

### Response

#### 200 OK

```json
{
  "message": "logged out"
}
```

### Example

```bash
curl -X POST "http://localhost:8000/auth/logout" \
  -H "Cookie: session=..."
```
