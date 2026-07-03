from datetime import timedelta

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from starlette.requests import Request

from app.config import settings

serializer = URLSafeTimedSerializer(settings.session_secret, salt="session")


def create_session_token(user_id: str) -> str:
    """Create a signed session token for the given user ID (7-day expiry)."""
    return serializer.dumps({"user_id": str(user_id)})


def verify_session_token(token: str) -> str | None:
    """Verify a signed session token and return the user_id, or None if invalid/expired."""
    try:
        data = serializer.loads(token, max_age=int(timedelta(days=7).total_seconds()))
        return data["user_id"]
    except (BadSignature, SignatureExpired):
        return None


def get_session_user_id(request: Request) -> str | None:
    """Extract and verify the user_id from the session cookie in the request."""
    token = request.cookies.get("session")
    if not token:
        return None
    return verify_session_token(token)
