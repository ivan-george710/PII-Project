from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.common import Schema


class OrganizationUpdate(Schema):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name", mode="before")
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value


class OrganizationResponse(Schema):
    id: UUID
    name: str
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def utc(cls, value):
        return (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )


class UserSummary(Schema):
    id: UUID
    email: str
    display_name: str
    role: Literal["employee", "manager"]


class AssignmentInput(Schema):
    manager_id: UUID


class AssignmentResponse(Schema):
    employee_id: UUID
    manager_id: UUID
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def utc(cls, value):
        return (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )


class UsersPage(Schema):
    items: list[UserSummary]
    next_cursor: str | None


class AssignmentsPage(Schema):
    items: list[AssignmentResponse]
    next_cursor: str | None
