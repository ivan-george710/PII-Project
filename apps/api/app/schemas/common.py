from typing import Generic, Literal, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Schema(BaseModel):
    model_config = ConfigDict(
        extra="forbid", validate_assignment=True, from_attributes=True
    )


class HealthResponse(Schema):
    status: Literal["ok"] = "ok"
    service: Literal["pii-guard-api"] = "pii-guard-api"
    commit: str | None = None


T = TypeVar("T")


class PaginatedResponse(Schema, Generic[T]):
    items: list[T]
    next_cursor: str | None = Field(default=None, max_length=512)


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        fields: list[dict] | None = None,
    ):
        self.status = status
        self.code = code
        self.message = message
        self.fields = fields or []


def error_body(
    code: str, message: str, fields: list[dict] | None = None
) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "fields": fields or [],
            "request_id": str(uuid4()),
        }
    }
