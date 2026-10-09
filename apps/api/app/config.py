import os
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: Literal["development", "test", "production"] = (
        "production" if os.getenv("VERCEL") else "development"
    )
    database_url: SecretStr = SecretStr("sqlite:///./pii-guard.db")
    public_app_url: str = "http://localhost:5173"
    session_secret: SecretStr | None = None
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
                raise ValueError("DEMO_ADAPTERS_ENABLED must be false in production")
            if not self.database_url.get_secret_value().startswith(
                ("postgresql://", "postgresql+psycopg://")
            ):
                raise ValueError("DATABASE_URL must use PostgreSQL in production")
            if not self.public_app_url.startswith("https://"):
                raise ValueError("PUBLIC_APP_URL must use HTTPS in production")
        if self.session_secret and len(self.session_secret.get_secret_value()) < 32:
            raise ValueError("SESSION_SECRET must contain at least 32 characters")
        return self

    @property
    def sqlalchemy_url(self):
        value = self.database_url.get_secret_value()
        return (
            value.replace("postgresql://", "postgresql+psycopg://", 1)
            if value.startswith("postgresql://")
            else value
        )

    def require_auth(self):
        from app.schemas.common import ApiError

        if not self.session_secret:
            raise ApiError(503, "AUTH_UNAVAILABLE", "Session settings are missing",
                fields=[{"path": "SESSION_SECRET", "message": "Required setting"}])
        return self


@lru_cache
def get_settings():
    try:
        return Settings()
    except ValidationError as error:
        from app.schemas.common import ApiError

        # Return only known setting names; never serialize Pydantic error inputs.
        names = set()
        for detail in error.errors(include_input=False):
            if detail["loc"]:
                names.add(str(detail["loc"][0]).upper())
            else:
                for name in ("PUBLIC_APP_URL", "DATABASE_URL", "SESSION_SECRET", "DEMO_ADAPTERS_ENABLED"):
                    if name in detail["msg"]:
                        names.add(name)
        raise ApiError(
            503, "CONFIGURATION_ERROR", "Required application settings are invalid",
            fields=[{"path": name, "message": "Invalid setting"} for name in sorted(names)],
        ) from None
