"""FastAPI dependencies connecting session, policy, engine, reporting, storage, and LLM implementations.

Connects the real implementations through standard dependency injection according to the
interfaces defined in issues 1-4. If a feature module is not yet implemented, a documented
interface fallback/development helper is used with a clear TODO.
"""

from typing import Any

from fastapi import Depends
from sqlalchemy.orm import Session

from app.auth.permissions import require_employee, require_manager
from app.auth.sessions import current_identity
from app.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.auth import SessionIdentity

# Re-export core auth and DB dependencies for unified access
get_current_identity = current_identity
get_manager_identity = require_manager
get_employee_identity = require_employee
get_database_session = get_db
get_app_settings = get_settings


# ---------------------------------------------------------------------------
# Policy Store Dependency (Issue #4)
# Interface: get_snapshot(organization_id: UUID) -> PolicySnapshot
# ---------------------------------------------------------------------------
def get_policy_store(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """Provide the company policy snapshot service."""
    try:
        from app.services.rules import get_policy_store as _get_policy_store  # type: ignore

        return _get_policy_store(db=db)
    except ImportError:
        pass

    try:
        from demo.adapters.policy import get_policy_adapter  # type: ignore

        return get_policy_adapter()
    except ImportError:
        pass

    # TODO: Issue #4 - Connect real PolicySnapshot service from app.services.rules
    class _DefaultPolicyStore:
        def get_snapshot(self, organization_id):
            raise NotImplementedError(
                "Policy store is not yet implemented (Issue #4)"
            )

    return _DefaultPolicyStore()


# ---------------------------------------------------------------------------
# Privacy Engine Dependency (Issue #1)
# Interface: sanitize(request: SanitizeRequest) -> SanitizeResult
# ---------------------------------------------------------------------------
def get_privacy_engine(
    settings: Settings = Depends(get_settings),
) -> Any:
    """Provide the privacy sanitization engine."""
    try:
        import pii_guard  # type: ignore

        return pii_guard
    except ImportError:
        pass

    try:
        from demo.adapters.engine import get_engine_adapter  # type: ignore

        return get_engine_adapter()
    except ImportError:
        pass

    # TODO: Issue #1 - Connect real privacy engine from packages/engine (pii_guard)
    class _DefaultPrivacyEngine:
        def sanitize(self, request):
            raise NotImplementedError(
                "Privacy engine is not yet connected (Issue #1)"
            )

    return _DefaultPrivacyEngine()


# ---------------------------------------------------------------------------
# Reporting / Event Sink Dependency (Issue #4)
# Interface: record(event_batch: EventBatch) -> None
# ---------------------------------------------------------------------------
def get_event_sink(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Any:
    """Provide the idempotent PII event recording sink."""
    try:
        from app.services.reporting import get_event_sink as _get_event_sink  # type: ignore

        return _get_event_sink(db=db)
    except ImportError:
        pass

    try:
        from demo.adapters.reporting import get_reporting_adapter  # type: ignore

        return get_reporting_adapter()
    except ImportError:
        pass

    # TODO: Issue #4 - Connect real event reporting sink from app.services.reporting
    class _DefaultEventSink:
        def record(self, event_batch):
            raise NotImplementedError(
                "Event sink is not yet implemented (Issue #4)"
            )

    return _DefaultEventSink()


# ---------------------------------------------------------------------------
# File Storage Dependency (Issue #2)
# Interface: create_upload, verify_upload, read_original, write_sanitized, read_sanitized
# ---------------------------------------------------------------------------
def get_file_storage(
    settings: Settings = Depends(get_settings),
) -> Any:
    """Provide the authorized file storage adapter."""
    try:
        from app.storage.files import FileStorageService  # type: ignore

        return FileStorageService(storage_dir=settings.storage_dir)
    except ImportError:
        pass

    # TODO: Issue #2 - Connect real file storage service from app.storage.files
    class _DefaultFileStorage:
        def __init__(self, storage_dir: str):
            self.storage_dir = storage_dir

        def create_upload(self, *args, **kwargs):
            raise NotImplementedError(
                "File storage is not yet implemented (Issue #2)"
            )

    return _DefaultFileStorage(storage_dir=settings.storage_dir)


# ---------------------------------------------------------------------------
# LLM Provider Dependency (Issue #2)
# Interface: stream(request: ProviderRequest) -> AsyncIterator[ProviderDelta]
# ---------------------------------------------------------------------------
def get_llm_client(
    settings: Settings = Depends(get_settings),
) -> Any:
    """Provide the LLM provider client configured with server-side credentials."""
    try:
        from app.llm.client import get_llm_client as _get_llm_client  # type: ignore

        return _get_llm_client(settings=settings)
    except ImportError:
        pass

    try:
        from demo.adapters.llm import get_llm_adapter  # type: ignore

        return get_llm_adapter()
    except ImportError:
        pass

    # TODO: Issue #2 - Connect real LLM provider from app.llm.client
    class _DefaultLLMClient:
        async def stream(self, request):
            raise NotImplementedError(
                "LLM client is not yet implemented (Issue #2)"
            )

    return _DefaultLLMClient()
