import os
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from cryptography.fernet import Fernet
from pydantic import Field, SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: Literal["development", "test", "production"] = (
        "production" if os.getenv("VERCEL") else "development"
    )
    database_url: SecretStr = SecretStr("sqlite:///./pii-guard.db")
    public_app_url: str = "http://localhost:5173"
    workos_api_key: SecretStr | None = None
    workos_client_id: str | None = Field(default=None, pattern=r"^client_[A-Za-z0-9]+$")
    workos_issuer: str | None = None
    workos_cookie_password: SecretStr | None = None
    workos_redirect_uri: str = "http://localhost:5173/api/v1/auth/callback"
    demo_adapters_enabled: bool = False

    @model_validator(mode="after")
    def production(self):
        origin = urlsplit(self.public_app_url)
        if (
            origin.scheme not in ("http", "https")
            or not origin.hostname
            or origin.username
            or origin.password
            or origin.query
            or origin.fragment
            or origin.path not in ("", "/")
        ):
            raise ValueError("PUBLIC_APP_URL must be an HTTP(S) origin")
        if self.app_env == "production":
            if self.demo_adapters_enabled:
                raise ValueError("Demo sessions are forbidden in production")
            if not self.database_url.get_secret_value().startswith(
                ("postgresql://", "postgresql+psycopg://")
            ):
                raise ValueError("Production requires PostgreSQL")
            if not self.public_app_url.startswith("https://"):
                raise ValueError("Production requires HTTPS")
        if self.workos_cookie_password:
            try:
                Fernet(self.workos_cookie_password.get_secret_value())
            except Exception:
                raise ValueError(
                    "WORKOS_COOKIE_PASSWORD must be a Fernet key"
                ) from None
        if (
            self.workos_redirect_uri
            != self.public_app_url.rstrip("/") + "/api/v1/auth/callback"
        ):
            raise ValueError("WorkOS callback must match PUBLIC_APP_URL")
        return self

    @property
    def sqlalchemy_url(self):
        value = self.database_url.get_secret_value()
        return (
            value.replace("postgresql://", "postgresql+psycopg://", 1)
            if value.startswith("postgresql://")
            else value
        )

    def require_workos(self):
        from app.schemas.common import ApiError

        if not all(
            (self.workos_api_key, self.workos_client_id, self.workos_cookie_password)
        ):
            raise ApiError(503, "AUTH_UNAVAILABLE", "WorkOS settings are missing")
        return self


@lru_cache
def get_settings():
    try:
        return Settings()
    except ValidationError:
        from app.schemas.common import ApiError

        raise ApiError(
            503, "CONFIGURATION_ERROR", "Required application settings are invalid"
        ) from None
