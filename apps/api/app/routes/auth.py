from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.passwords import hash_password, verify_password
from app.auth.sessions import (
    COOKIE,
    create_session,
    csrf_token,
    current_identity,
    set_session_cookie,
    token_hash,
    utc,
)
from app.config import get_settings
from app.db.models import AuthSession, Organization, User
from app.db.session import get_db
from app.schemas.auth import (
    EmptyRequest,
    LoginRequest,
    MeResponse,
    PublicUser,
    SessionIdentity,
    SessionOrganization,
    SignupRequest,
)
from app.schemas.common import ApiError

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def session_response(identity, token, db):
    org = db.get(Organization, identity.organization_id)
    return MeResponse(
        user=PublicUser(
            id=identity.user_id, **identity.model_dump(exclude={"user_id"})
        ),
        organization=SessionOrganization(id=org.id, name=org.name),
        csrf_token=csrf_token(token, get_settings().session_secret.get_secret_value()),
    )


@router.post("/signup", response_model=MeResponse, status_code=201)
def signup(
    body: SignupRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    settings = get_settings().require_auth()
    if request.headers.get("origin") != settings.public_app_url.rstrip("/"):
        raise ApiError(403, "CSRF_INVALID", "Request origin is invalid")
    if db.scalar(select(User.id).where(User.email == body.email)):
        raise ApiError(
            409,
            "ACCOUNT_EXISTS",
            "An account already uses this email. Sign in instead.",
        )
    name = body.display_name.strip() or "New member"
    company = Organization(
        name=body.company_name.strip() or (name + "’s workspace")[:120]
    )
    db.add(company)
    db.flush()
    user = User(
        organization_id=company.id,
        email=body.email,
        display_name=name,
        role="manager",
        password_hash=hash_password(body.password.get_secret_value()),
    )
    db.add(user)
    try:
        db.flush()
        token = create_session(db, user)
        db.commit()
    except IntegrityError:
        db.rollback()
        if db.scalar(select(User.id).where(User.email == body.email)):
            raise ApiError(
                409,
                "ACCOUNT_EXISTS",
                "An account already uses this email. Sign in instead.",
            ) from None
        raise
    set_session_cookie(response, token)
    response.headers["Cache-Control"] = "no-store"
    identity = SessionIdentity(
        user_id=user.id,
        organization_id=company.id,
        role=user.role,
        email=user.email,
        display_name=user.display_name,
    )
    return session_response(identity, token, db)


@router.post("/login", response_model=MeResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    settings = get_settings().require_auth()
    if request.headers.get("origin") != settings.public_app_url.rstrip("/"):
        raise ApiError(403, "CSRF_INVALID", "Request origin is invalid")
    # Serialize attempts for each account, including across server instances.
    user = db.scalar(
        select(User).where(User.email == str(body.email)).with_for_update()
    )
    now = datetime.now(UTC)
    if user and user.locked_until and utc(user.locked_until) > now:
        raise ApiError(
            429, "LOGIN_RATE_LIMITED", "Too many attempts. Try again in 5 minutes"
        )
    valid = verify_password(
        body.password.get_secret_value(), user.password_hash if user else None
    )
    if user is None or not user.active or not valid:
        if user and user.active:
            if user.locked_until and utc(user.locked_until) <= now:
                user.failed_login_attempts = 0
                user.locked_until = None
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = now + timedelta(minutes=5)
            db.commit()
        raise ApiError(401, "INVALID_CREDENTIALS", "Email or password is incorrect")
    user.failed_login_attempts = 0
    user.locked_until = None
    # A new login replaces the browser's previous session, avoiding fixation.
    previous = request.cookies.get(COOKIE)
    if previous:
        db.execute(
            delete(AuthSession).where(AuthSession.token_hash == token_hash(previous))
        )
    db.execute(delete(AuthSession).where(AuthSession.expires_at <= now))
    token = create_session(db, user)
    db.commit()
    set_session_cookie(response, token)
    response.headers["Cache-Control"] = "no-store"
    identity = SessionIdentity(
        user_id=user.id,
        organization_id=user.organization_id,
        role=user.role,
        email=user.email,
        display_name=user.display_name,
    )
    return session_response(identity, token, db)


@router.get("/me", response_model=MeResponse)
def me(
    request: Request,
    response: Response,
    identity=Depends(current_identity),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    return session_response(identity, request.state.session_token, db)


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    body: EmptyRequest,
    identity=Depends(current_identity),
    db: Session = Depends(get_db),
):
    db.execute(
        delete(AuthSession).where(
            AuthSession.token_hash == token_hash(request.state.session_token)
        )
    )
    db.commit()
    response = Response(status_code=204)
    response.delete_cookie(
        COOKIE,
        path="/",
        secure=get_settings().public_app_url.startswith("https://"),
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
    return response
