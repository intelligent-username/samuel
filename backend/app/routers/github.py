import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.repository import Repository
from app.models.user import User
from app.schemas import RepositoryResponse
from app.services.auth import get_session_user_id
from app.services.encryption import decrypt
from app.services.github_graphql import fetch_user_repos

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/github", tags=["github"])


@router.post("/sync")
async def sync_repos(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    """Fetch and cache GitHub repositories for the authenticated user."""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        token = decrypt(user.github_access_token)
    except Exception as e:
        logger.error("Failed to decrypt GitHub token for user %s: %s", user.id, e)
        raise HTTPException(status_code=500, detail="Failed to decrypt stored credentials")

    try:
        repos_data, avatar_url = await fetch_user_repos(token, user.github_username)
    except Exception as e:
        logger.exception("GitHub sync error")
        raise HTTPException(status_code=502, detail=f"GitHub sync failed: {type(e).__name__}: {e}")

    now = datetime.now(timezone.utc)
    for repo_info in repos_data:
        existing = await db.execute(
            select(Repository).where(
                Repository.user_id == user.id,
                Repository.github_repo_id == repo_info["github_repo_id"],
            )
        )
        repo = existing.scalar_one_or_none()
        if repo:
            for key, val in repo_info.items():
                setattr(repo, key, val)
            repo.last_fetched_at = now
        else:
            repo = Repository(user_id=user.id, last_fetched_at=now, **repo_info)
            db.add(repo)

    await db.commit()
    return {"message": f"Synced {len(repos_data)} repositories", "avatar_url": avatar_url}


@router.get("/repos")
async def list_repos(request: Request, db: AsyncSession = Depends(get_db)) -> list:
    """List all cached GitHub repositories for the authenticated user."""
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(Repository).where(Repository.user_id == user_id).order_by(Repository.repo_created_at.desc().nulls_last())
    )
    repos = result.scalars().all()
    return [RepositoryResponse.model_validate(r) for r in repos]
