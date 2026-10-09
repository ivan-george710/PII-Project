from typing import Literal
from uuid import UUID

from pydantic import Field, SecretStr, field_validator

from app.schemas.common import Schema


class SessionIdentity(Schema):
    user_id: UUID
    organization_id: UUID
    role: Literal["employee", "manager"]
    email: str
    display_name: str = Field(min_length=1, max_length=120)


class PublicUser(Schema):
    id: UUID
    email: str
    display_name: str
    role: Literal["employee", "manager"]
    organization_id: UUID


class SessionOrganization(Schema):
    id: UUID
    name: str


class MeResponse(Schema):
    user: PublicUser
    organization: SessionOrganization
    csrf_token: str


class EmptyRequest(Schema):
    pass


class LoginRequest(Schema):
    email: str
    password: SecretStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return str(value).lower()


class SignupRequest(LoginRequest):
    display_name: str = Field(default="", max_length=120)
    company_name: str = Field(default="", max_length=120)
