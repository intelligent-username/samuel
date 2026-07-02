from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.repository import Repository
from app.models.user import User
from app.schemas import RepositoryResponse
from app.services.auth import get_session_user_id
from app.services.github_graphql import fetch_user_repos

router = APIRouter(prefix="/github", tags=["github"])


@router.post("/sync")
async def sync_repos(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        from app.services.encryption import decrypt
        try:
            token = decrypt(user.github_access_token)
        except Exception:
            token = user.github_access_token
        repos_data = await fetch_user_repos(token, user.github_username)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub sync failed: {str(e)}")

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
    return {"message": f"Synced {len(repos_data)} repositories"}


@router.get("/repos")
async def list_repos(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_session_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(Repository).where(Repository.user_id == user_id).order_by(Repository.last_push.desc())
    )
    repos = result.scalars().all()
    return [RepositoryResponse.model_validate(r) for r in repos]