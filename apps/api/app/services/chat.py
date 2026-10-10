from uuid import UUID

from app.db.models.message import Message
from app.llm.client import ProviderMessage
from app.schemas.common import ApiError
from app.services.guard import Engine, PolicySnapshot, SanitizeRequest, SanitizeResult


def resanitize_history(
    *,
    messages: list[Message],
    organization_id: UUID,
    policy: PolicySnapshot,
    engine: Engine,
) -> list[ProviderMessage]:
    safe: list[ProviderMessage] = []
    for message in messages:
        result = SanitizeResult.model_validate(
            engine.sanitize(
                SanitizeRequest(
                    organization_id=organization_id,
                    policy=policy,
                    text=message.sanitized_text,
                )
            ).model_dump()
        )
        safe.append(ProviderMessage(role=message.role, sanitized_text=result.sanitized_text))
    return safe


def require_current_policy(policy_store, organization_id: UUID) -> PolicySnapshot:
    try:
        return PolicySnapshot.model_validate(
            policy_store.get_snapshot(organization_id).model_dump()
        )
    except Exception:
        raise ApiError(503, "POLICY_UNAVAILABLE", "Privacy policy is unavailable") from None
