"""Opt-in development identity dependency; no public login bypass route."""

from app.config import get_settings
from app.schemas.auth import SessionIdentity


def session_dependency(identity: SessionIdentity):
    settings = get_settings()
    if (
        settings.app_env not in ("development", "test")
        or not settings.demo_adapters_enabled
    ):
        raise ValueError("Synthetic sessions require an explicit development/test flag")
    validated = SessionIdentity.model_validate(identity.model_dump())

    def dependency():
        return validated.model_copy(deep=True)

    return dependency
