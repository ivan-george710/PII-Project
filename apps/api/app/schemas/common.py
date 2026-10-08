from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    status: Literal["ok"] = "ok"
    service: Literal["pii-guard-api"] = "pii-guard-api"
    commit: str | None = None
