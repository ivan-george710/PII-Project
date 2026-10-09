from functools import lru_cache
from types import SimpleNamespace

import jwt
from workos import WorkOSClient
from workos.session import seal_session_from_auth_response, unseal_data

from app.config import get_settings
from app.schemas.common import ApiError


class WorkOSGateway:
    def __init__(self, settings):
        self.settings = settings.require_workos()
        self.client = WorkOSClient(
            api_key=settings.workos_api_key.get_secret_value(),
            client_id=settings.workos_client_id,
            jwt_issuer=settings.workos_issuer
            or [
                "https://api.workos.com/user_management/" + settings.workos_client_id,
                "https://api.workos.com",
            ],
        )

    def authorization_url(self, state, challenge):
        return self.client.user_management.get_authorization_url(
            provider="authkit",
            redirect_uri=self.settings.workos_redirect_uri,
            state=state,
            code_challenge=challenge,
            code_challenge_method="S256",
        )

    def exchange(self, code, verifier):
        response = self.client.user_management.authenticate_with_code(
            code=code, code_verifier=verifier
        )
        # SDK models expose to_dict rather than Pydantic model_dump.
        user = response.user.to_dict()
        return seal_session_from_auth_response(
            access_token=response.access_token,
            refresh_token=response.refresh_token,
            user=user,
            cookie_password=self.settings.workos_cookie_password.get_secret_value(),
        )

    def authenticate(self, cookie):
        session = self.client.user_management.load_sealed_session(
            session_data=cookie,
            cookie_password=self.settings.workos_cookie_password.get_secret_value(),
        )
        result = session.authenticate()
        replacement_cookie = None
        if (
            not result.authenticated
            and getattr(result.reason, "value", "") == "invalid_jwt"
        ):
            refreshed = session.refresh()
            if refreshed.authenticated:
                replacement_cookie = refreshed.sealed_session
                result = session.authenticate()
        if not result.authenticated or not result.user:
            raise ApiError(401, "UNAUTHENTICATED", "Please sign in")
        validated_cookie = replacement_cookie or cookie
        claims = jwt.decode(
            unseal_data(
                validated_cookie,
                self.settings.workos_cookie_password.get_secret_value(),
            )["access_token"],
            options={"verify_signature": False},
        )
        # The SDK already checked signature, expiry and issuer; bind its claims to this app/user too.
        if (
            claims.get("client_id") != self.settings.workos_client_id
            or claims.get("sub") != result.user["id"]
        ):
            raise ApiError(401, "UNAUTHENTICATED", "Please sign in")
        # Check the user still exists, not only the cached sealed-cookie identity.
        self.client.user_management.get_user(id=result.user["id"])
        active_sessions = self.client.user_management.list_sessions(
            id=result.user["id"], limit=100
        )
        if not any(
            item.id == result.session_id and item.status == "active"
            for item in active_sessions
        ):
            raise ApiError(401, "UNAUTHENTICATED", "Please sign in")
        if result.organization_id:
            memberships = (
                self.client.organization_membership.list_organization_memberships(
                    user_id=result.user["id"], organization_id=result.organization_id
                )
            )
            if not any(m.status == "active" for m in memberships.data):
                raise ApiError(
                    403, "MEMBERSHIP_REQUIRED", "Company membership is unavailable"
                )
        return SimpleNamespace(
            user=result.user,
            organization_id=result.organization_id,
            session_id=result.session_id,
            replacement_cookie=replacement_cookie,
        )

    def revoke(self, session_id):
        self.client.user_management.revoke_session(session_id=session_id)


@lru_cache
def get_gateway():
    return WorkOSGateway(get_settings())
