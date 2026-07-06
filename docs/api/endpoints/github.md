# GitHub

Endpoints for synchronizing and listing cached GitHub repositories. All endpoints require authentication via the `session` cookie.

## Endpoints

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/github/sync` | Fetch and cache the user's public GitHub repositories |
| `GET` | `/github/repos` | List all cached repositories |

## Sync Repositories

`POST /github/sync`

Fetches the authenticated user's public GitHub repositories via the GitHub GraphQL API and caches them in the database. Existing repositories are updated. New repositories are inserted. The response includes the number of synced repositories and the user's avatar URL.

### Response

#### 200 OK

```json
{
  "message": "Synced 24 repositories",
  "avatar_url": "https://avatars.githubusercontent.com/u/12345678?v=4"
}
```

#### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

#### 502 Bad Gateway

GitHub API request failed.

```json
{
  "detail": "GitHub sync failed: ..."
}
```

### Example

```bash
curl -X POST "http://localhost:8000/github/sync" \
  -H "Cookie: session=..."
```

## List Cached Repositories

`GET /github/repos`

Returns all cached repositories for the authenticated user, sorted by repository creation date (newest first).

### Response

#### 200 OK

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "my-project",
    "description": "A useful open source tool",
    "stars": 42,
    "languages": {
      "Python": 80,
      "JavaScript": 20
    },
    "topics": ["cli", "automation"],
    "url": null,
    "homepage_url": null,
    "forks": 5,
    "is_archived": false,
    "is_private": false,
    "last_push": "2025-06-01T12:00:00Z",
    "repo_created_at": "2024-03-15T10:00:00Z",
    "readme_text": null,
    "last_fetched_at": "2025-07-02T10:30:00Z"
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
curl -X GET "http://localhost:8000/github/repos" \
  -H "Cookie: session=..."
```

## Notes

The sync endpoint uses the GitHub GraphQL API (`fetch_user_repos`) to gather repository names, descriptions, README content, star counts, languages, and topics in a single query. The auth flow uses GitHub REST endpoints (`/user`, `/login/oauth/access_token`), which is the only exception to the GraphQL requirement.
