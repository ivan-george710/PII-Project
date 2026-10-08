import hmac
from hashlib import sha256

from fastapi import Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.workos import get_gateway
from app.config import get_settings
from app.db.models import Organization, User
from app.db.session import get_db
from app.schemas.auth import SessionIdentity
from app.schemas.common import ApiError

COOKIE = "wos-session"


def csrf_token(cookie, secret):
    return hmac.new(secret.encode(), cookie.encode(), sha256).hexdigest()


def current_identity(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    gateway=Depends(get_gateway),
):
    cookie = request.cookies.get(COOKIE)
    if not cookie:
        raise ApiError(401, "UNAUTHENTICATED", "Please sign in")
    try:
        remote = gateway.authenticate(cookie)
    except ApiError:
        raise
    except Exception:
        raise ApiError(401, "UNAUTHENTICATED", "Please sign in") from None
    user = db.scalar(
        select(User).where(
            User.workos_user_id == remote.user["id"], User.active.is_(True)
        )
    )
    if not user:
        raise ApiError(403, "MEMBERSHIP_REQUIRED", "Company membership is unavailable")
    org = db.get(Organization, user.organization_id)
    if (
        org.workos_organization_id
        and remote.organization_id != org.workos_organization_id
    ):
        raise ApiError(403, "MEMBERSHIP_REQUIRED", "Company membership is unavailable")
    request.state.workos_session_id = remote.session_id
    if getattr(remote, "replacement_cookie", None):
        response.set_cookie(
            COOKIE,
            remote.replacement_cookie,
            max_age=7 * 24 * 3600,
            httponly=True,
            secure=get_settings().public_app_url.startswith("https://"),
            samesite="lax",
            path="/",
        )
    identity = SessionIdentity(
        user_id=user.id,
        organization_id=user.organization_id,
        role=user.role,
        email=user.email,
        display_name=user.display_name,
    )
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        settings = get_settings().require_workos()
        expected = csrf_token(
            remote.session_id, settings.workos_cookie_password.get_secret_value()
        )
        if request.headers.get("origin") != settings.public_app_url.rstrip(
            "/"
        ) or not hmac.compare_digest(request.headers.get("x-csrf-token", ""), expected):
            raise ApiError(
                403, "CSRF_INVALID", "Request origin or CSRF token is invalid"
            )
    return identity
