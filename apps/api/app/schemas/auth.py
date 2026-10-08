from typing import Literal
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.common import Schema


class SessionIdentity(Schema):
    user_id: UUID
    organization_id: UUID
    role: Literal["employee", "manager"]
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)


class PublicUser(Schema):
    id: UUID
    email: EmailStr
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
