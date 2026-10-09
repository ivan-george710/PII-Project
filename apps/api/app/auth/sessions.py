import hmac
import secrets
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import AuthSession, User
from app.db.session import get_db
from app.schemas.auth import SessionIdentity
from app.schemas.common import ApiError

COOKIE = "pii-session"
SESSION_SECONDS = 7 * 24 * 3600


def utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def token_hash(token):
    return sha256(token.encode()).hexdigest()


def csrf_token(token, secret):
    return hmac.new(secret.encode(), token.encode(), sha256).hexdigest()


def create_session(db, user):
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            token_hash=token_hash(token),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(seconds=SESSION_SECONDS),
        )
    )
    return token


def set_session_cookie(response, token):
    response.set_cookie(
        COOKIE,
        token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=get_settings().public_app_url.startswith("https://"),
        samesite="lax",
        path="/",
    )


def current_identity(
    request: Request, response: Response, db: Session = Depends(get_db)
):
    settings = get_settings().require_auth()
    token = request.cookies.get(COOKIE, "")
    if len(token) != 43:
        raise ApiError(401, "UNAUTHENTICATED", "Please sign in")
    session = db.get(AuthSession, token_hash(token))
    if session is None or utc(session.expires_at) <= datetime.now(UTC):
        raise ApiError(401, "UNAUTHENTICATED", "Please sign in")
    user = db.get(User, session.user_id)
    if user is None or not user.active:
        raise ApiError(403, "MEMBERSHIP_REQUIRED", "Company membership is unavailable")
    request.state.session_token = token
    identity = SessionIdentity(
        user_id=user.id,
        organization_id=user.organization_id,
        role=user.role,
        email=user.email,
        display_name=user.display_name,
    )
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        expected = csrf_token(token, settings.session_secret.get_secret_value())
        if request.headers.get("origin") != settings.public_app_url.rstrip(
            "/"
        ) or not hmac.compare_digest(
            request.headers.get("x-csrf-token", "").encode(), expected.encode()
        ):
            raise ApiError(
                403, "CSRF_INVALID", "Request origin or CSRF token is invalid"
            )
    return identity
