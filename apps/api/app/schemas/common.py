from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    model_config = ConfigDict(
        extra="forbid", validate_assignment=True, from_attributes=True
    )


class HealthResponse(Schema):
    status: Literal["ok"] = "ok"
    service: Literal["pii-guard-api"] = "pii-guard-api"
    commit: str | None = None


class ApiError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


def error_body(code, message, fields=None):
    return {
        "error": {
            "code": code,
            "message": message,
            "fields": fields or [],
            "request_id": str(uuid4()),
        }
    }
