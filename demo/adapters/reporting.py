"""Synthetic idempotent reporting sink and source for independent feature testing."""

from uuid import UUID

from app.config import get_settings
from app.schemas.reports import EventBatch


class DemoReportingSink:
    def __init__(self):
        self.recorded_batches: list[EventBatch] = []

    def record(self, batch: EventBatch) -> None:
        settings = get_settings()
        if (
            settings.app_env not in ("development", "test")
            or not settings.demo_adapters_enabled
        ):
            raise ValueError("Synthetic reporting requires an explicit development/test flag")

        # Check for duplicate
        for existing in self.recorded_batches:
            if (
                existing.organization_id == batch.organization_id
                and existing.submission_id == batch.submission_id
                and existing.policy_version == batch.policy_version
            ):
                return
        self.recorded_batches.append(batch)

    def get_batches(self, organization_id: UUID) -> list[EventBatch]:
        return [b for b in self.recorded_batches if b.organization_id == organization_id]
