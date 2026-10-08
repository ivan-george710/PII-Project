"""Trusted operator command to map real WorkOS users to company roles."""

import argparse
import json
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import EmailStr, Field, TypeAdapter
from sqlalchemy import select

from app.auth.workos import get_gateway
from app.db.models import Organization, User
from app.db.session import session_factory
from app.schemas.common import Schema


class ProvisionUser(Schema):
    workos_user_id: str = Field(pattern=r"^user_[A-Za-z0-9]+$", max_length=100)
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    role: Literal["employee", "manager"]


def provision(db, gateway, organization_id, name, workos_organization_id, identities):
    values = TypeAdapter(list[ProvisionUser]).validate_python(identities)
    if not values or len({v.workos_user_id for v in values}) != len(values):
        raise ValueError("Provide distinct users")
    for value in values:
        remote = gateway.client.user_management.get_user(id=value.workos_user_id)
        if remote.email != value.email:
            raise ValueError("WorkOS email mapping mismatch")
        members = gateway.client.organization_membership.list_organization_memberships(
            user_id=value.workos_user_id,
            organization_id=workos_organization_id,
            statuses=["active"],
        )
        if not members.data:
            raise ValueError("Active WorkOS organization membership required")
    org = db.get(Organization, organization_id)
    if org is None:
        org = Organization(
            id=organization_id, name=name, workos_organization_id=workos_organization_id
        )
        db.add(org)
        db.flush()
    elif org.workos_organization_id != workos_organization_id:
        raise ValueError("Company mapping conflict")
    for value in values:
        user = db.scalar(
            select(User).where(User.workos_user_id == value.workos_user_id)
        )
        if user is not None:
            if user.organization_id != organization_id or user.role != value.role:
                raise ValueError(
                    "Existing company/role mapping conflict; change it deliberately in the database"
                )
        else:
            db.add(
                User(organization_id=organization_id, **value.model_dump(mode="json"))
            )
    db.commit()
    return {"organization_id": str(org.id), "users": len(values)}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--organization-id", required=True, type=UUID)
    p.add_argument("--name", required=True)
    p.add_argument("--workos-organization-id", required=True)
    p.add_argument("--identities", required=True)
    a = p.parse_args()
    if not 1 <= len(a.name.strip()) <= 120:
        raise ValueError("Company name must be 1–120 characters")
    with session_factory()() as db:
        print(
            json.dumps(
                provision(
                    db,
                    get_gateway(),
                    a.organization_id,
                    a.name.strip(),
                    a.workos_organization_id,
                    json.loads(Path(a.identities).read_text()),
                )
            )
        )
