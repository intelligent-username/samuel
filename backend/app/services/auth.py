from datetime import timedelta

from itsdangerous import URLSafeTimedSerializer
from starlette.requests import Request

from app.config import settings

serializer = URLSafeTimedSerializer(settings.session_secret, salt="session")


def create_session_token(user_id: str) -> str:
    return serializer.dumps({"user_id": str(user_id)})


def verify_session_token(token: str) -> str | None:
    try:
        data = serializer.loads(token, max_age=int(timedelta(days=7).total_seconds()))
        return data["user_id"]
    except Exception:
        return None


def get_session_user_id(request: Request) -> str | None:
    token = request.cookies.get("session")
    if not token:
        return None
    return verify_session_token(token)