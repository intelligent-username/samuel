# Authentication

Samuel uses GitHub OAuth for authentication. The backend manages sessions with HTTP-only cookies. No API keys or tokens are required for auth endpoints.

## How It Works

The backend redirects the user to GitHub for authorization, receives a callback with an authorization code, exchanges it for a GitHub access token, and creates a local user record. It then sets a `session` cookie on the response. All subsequent requests include this cookie automatically when the frontend uses `credentials: "include"`.

## OAuth Flow

1. The user clicks "Login with GitHub" on the frontend.
2. The frontend calls `GET /auth/login`.
3. The backend generates a random state value, sets it as an `oauth_state` cookie (HTTP-only, 10-minute expiry), and returns a GitHub authorization URL.
4. The browser redirects to GitHub's authorization page.
5. GitHub prompts the user to authorize the application with the `read:user` and `public_repo` scopes.
6. GitHub redirects the browser to `http://localhost:3000/auth/callback?code=xxx&state=yyy`.
7. The frontend forwards the `code` and `state` parameters to `GET /auth/callback`.
8. The backend validates the `state` parameter against the `oauth_state` cookie to prevent CSRF attacks. If they do not match, it returns a 400 error.
9. The backend exchanges the `code` for a GitHub access token via `https://github.com/login/oauth/access_token`.
10. The backend fetches the user's GitHub profile via the REST API and upserts a record in the database.
11. The backend clears the `oauth_state` cookie and sets a `session` cookie (HTTP-only, 7-day expiry, `SameSite=Lax`).
12. The frontend redirects to the dashboard. All subsequent API calls include the `session` cookie.

## Session Cookie

The `session` cookie is HTTP-only and uses `SameSite=Lax`. The frontend includes it in requests by setting `credentials: "include"` on all fetch calls. The backend validates the session token on every authenticated endpoint. If the cookie is missing or invalid, the endpoint returns a 401 response.

## Logout

`POST /auth/logout` clears the `session` cookie. No server-side session store is invalidated. The frontend should redirect to the login page after calling this endpoint.

## State Parameter and CSRF Protection

The `state` parameter prevents CSRF attacks on the OAuth callback. The backend generates a cryptographically random token, stores it in the `oauth_state` cookie, and validates it when the callback arrives. The cookie expires after 10 minutes. If the state validation fails, the callback returns a 400 error with no session created.

## Required GitHub Scopes

| Scope | Purpose |
| :--- | :--- |
| `read:user` | Read the user's GitHub profile (username and ID) |
| `public_repo` | Read the user's public repositories for project matching |
