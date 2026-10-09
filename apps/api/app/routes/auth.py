import base64
import hashlib
import hmac
import secrets

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse, Response
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.auth.sessions import COOKIE, csrf_token, current_identity
from app.auth.workos import get_gateway
from app.config import get_settings
from app.db.models import Organization
from app.db.session import get_db
from app.schemas.auth import EmptyRequest, MeResponse, PublicUser, SessionOrganization
from app.schemas.common import ApiError

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
ALLOWED_RETURN_PATHS = {"/", "/chat", "/company/setup"}


def serializer(settings):
    return URLSafeTimedSerializer(
        settings.workos_cookie_password.get_secret_value(), salt="workos-login"
    )


def set_cookie(response, name, value, settings, max_age):
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        httponly=True,
        secure=settings.public_app_url.startswith("https://"),
        samesite="lax",
        path="/",
    )


@router.get("/login")
def login(return_to: str = Query("/", max_length=255), gateway=Depends(get_gateway)):
    if return_to not in ALLOWED_RETURN_PATHS:
        raise ApiError(422, "VALIDATION_ERROR", "Invalid return path")
    settings = get_settings().require_workos()
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    response = RedirectResponse(
        gateway.authorization_url(state, challenge), status_code=302
    )
    set_cookie(
        response,
        "wos-login",
        serializer(settings).dumps(
            {"state": state, "verifier": verifier, "return_to": return_to}
        ),
        settings,
        600,
    )
    return response


@router.get("/callback")
def callback(
    request: Request,
    code: str = Query(max_length=2048),
    state: str = Query(max_length=200),
    db: Session = Depends(get_db),
    gateway=Depends(get_gateway),
):
    settings = get_settings().require_workos()
    try:
        flow = serializer(settings).loads(
            request.cookies.get("wos-login", ""), max_age=600
        )
        if not hmac.compare_digest(state, flow["state"]):
            raise ValueError()
    except (BadSignature, ValueError, KeyError):
        raise ApiError(
            400, "AUTH_STATE_INVALID", "Sign-in expired or state is invalid"
        ) from None
    try:
        cookie = gateway.exchange(code, flow["verifier"])
        check = Request(
            {
                "type": "http",
                "method": "GET",
                "headers": [(b"cookie", (COOKIE + "=" + cookie).encode())],
            }
        )
        current_identity(check, Response(), db, gateway)
    except ApiError:
        raise
    except Exception:
        raise ApiError(401, "AUTH_FAILED", "Sign-in could not be completed") from None
    response = RedirectResponse(flow["return_to"], status_code=302)
    response.delete_cookie("wos-login", path="/")
    set_cookie(response, COOKIE, cookie, settings, 7 * 24 * 3600)
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/me", response_model=MeResponse)
def me(
    request: Request,
    response: Response,
    identity=Depends(current_identity),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    org = db.get(Organization, identity.organization_id)
    return MeResponse(
        user=PublicUser(
            id=identity.user_id, **identity.model_dump(exclude={"user_id"})
        ),
        organization=SessionOrganization(id=org.id, name=org.name),
        csrf_token=csrf_token(
            request.state.workos_session_id,
            get_settings().workos_cookie_password.get_secret_value(),
        ),
    )


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    body: EmptyRequest,
    identity=Depends(current_identity),
    gateway=Depends(get_gateway),
):
    try:
        gateway.revoke(request.state.workos_session_id)
    except Exception:
        raise ApiError(
            503, "AUTH_UNAVAILABLE", "Sign-out could not be completed; retry"
        ) from None
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, path="/")
    response.headers["Cache-Control"] = "no-store"
    return response
