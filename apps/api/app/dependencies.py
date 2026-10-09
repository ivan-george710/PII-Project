"""Shared dependencies and registration of implemented feature routers.

Future features supply their real services in their owning modules. This module
never replaces missing privacy processing with simulated or empty services.
"""

from importlib import import_module
from importlib.util import find_spec

from fastapi import FastAPI

from app.auth.permissions import require_employee, require_manager
from app.auth.sessions import current_identity
from app.config import get_settings
from app.db.session import get_db

__all__ = [
    "current_identity", "require_employee", "require_manager",
    "get_settings", "get_db", "register_feature_routers",
]


def register_feature_routers(app: FastAPI) -> None:
    """Register feature modules when present; broken implementations fail startup."""
    for name in ("chat", "uploads", "demo", "rules", "reports"):
        module_name = f"app.routes.{name}"
        if find_spec(module_name) is not None:
            app.include_router(import_module(module_name).router)
