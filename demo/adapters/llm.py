from collections.abc import AsyncIterator

from app.config import get_settings
from app.llm.client import ProviderDelta, ProviderRequest
from app.schemas.common import ApiError


class DemoLLM:
    """Deterministic development provider that records only sanitized payloads."""

    def __init__(self):
        self.captured: list[ProviderRequest] = []

    async def stream(self, request: ProviderRequest) -> AsyncIterator[ProviderDelta]:
        settings = get_settings()
        if settings.app_env == "production" or not settings.demo_adapters_enabled:
            raise ApiError(503, "PROVIDER_UNAVAILABLE", "LLM provider is unavailable")
        validated = ProviderRequest.model_validate(request.model_dump())
        self.captured.append(validated)
        yield ProviderDelta(text="I received your sanitized request.")
