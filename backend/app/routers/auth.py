import secrets
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas import UserResponse
from app.services.auth import create_session_token, get_session_user_id
from app.services.encryption import encrypt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


@router.get("/login")
async def login(response: Response) -> dict:
    """Initiate GitHub OAuth login by returning the authorize URL."""
    state = secrets.token_urlsafe(16)
    response.set_cookie(key="oauth_state", value=state, httponly=True, max_age=600, samesite="lax")
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": "http://localhost:3000/auth/callback",
        "scope": "read:user public_repo",
        "state": state,
    }
    url = f"{GITHUB_AUTHORIZE_URL}?client_id={params['client_id']}&redirect_uri={params['redirect_uri']}&scope={params['scope']}&state={params['state']}"
    return {"authorization_url": url}


@router.get("/callback")
async def callback(
    code: str, state: str, request: Request, response: Response, db: AsyncSession = Depends(get_db)
) -> dict:
    """Handle GitHub OAuth callback: exchange code, fetch user, upsert DB record, set session cookie."""
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="State mismatch — possible CSRF")

    response.delete_cookie("oauth_state")
    token_resp = await _exchange_code(code)
    if "access_token" not in token_resp:
        raise HTTPException(status_code=400, detail="Failed to exchange code")

    access_token = token_resp["access_token"]
    github_user = await _fetch_github_user(access_token)

    result = await db.execute(select(User).where(User.github_id == github_user["id"]))
    user = result.scalar_one_or_none()

    if user:
        user.github_access_token = encrypt(access_token)
        user.github_username = github_user["login"]
    else:
        user = User(
            github_id=github_user["id"],
            github_username=github_user["login"],
            github_access_token=encrypt(access_token),
        )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    session_token = create_session_token(str(user.id))
    response.set_cookie(
        key="session", value=session_token, httponly=True,
        max_age=7 * 24 * 3600, samesite="lax", secure=settings.secure_cookie,
    )
    return {"message": "authenticated", "user": UserResponse.model_validate(user)}


@router.get("/me")
async def me(request: Request, db: AsyncSession = Depends(get_db)) -> UserResponse:
    """Return the currently authenticated user's profile."""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


@router.post("/logout")
async def logout(response: Response) -> dict:
    """Clear the session cookie to log the user out."""
    response.delete_cookie("session")
    return {"message": "logged out"}


async def _exchange_code(code: str) -> dict:
    """Exchange an OAuth authorization code for an access token from GitHub."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        return resp.json()


async def _fetch_github_user(access_token: str) -> dict:
    """Fetch the authenticated GitHub user's profile via REST API."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()
