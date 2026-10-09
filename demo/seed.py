"""Trusted fictional identity setup; never a public privilege-promotion endpoint."""

import argparse
import json
from pathlib import Path
from uuid import UUID

from pydantic import EmailStr, Field, TypeAdapter

from app.config import get_settings
from app.db.models import ManagerAssignment, Organization, User
from app.db.session import session_factory
from app.schemas.common import Schema

COMPANY_ID = UUID("00000000-0000-4000-8000-000000000010")


class SeedUser(Schema):
    id: UUID
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=120)
    role: str


def seed(db, name, identities, policy_store=None):
    settings = get_settings()
    if settings.app_env == "production":
        raise ValueError("Fictional seeding is forbidden in production")
    values = TypeAdapter(list[SeedUser]).validate_python(identities)
    if sorted(x.role for x in values) != ["employee", "employee", "manager"]:
        raise ValueError("Seed requires one manager and two employees")
    if not settings.demo_adapters_enabled:
        raise ValueError(
            "Explicitly enable development adapters for fictional identities"
        )
    org = db.get(Organization, COMPANY_ID)
    if org is None:
        org = Organization(id=COMPANY_ID, name=name)
        db.add(org)
        db.flush()
    elif org.name != name:
        raise ValueError("Seed target differs from existing company")
    for value in values:
        user = db.get(User, value.id)
        if user is None:
            db.add(
                User(
                    id=value.id,
                    organization_id=org.id,
                    email=str(value.email),
                    display_name=value.display_name,
                    role=value.role,
                )
            )
        elif (
            user.organization_id != org.id
            or user.email != str(value.email)
            or user.role != value.role
        ):
            raise ValueError("Seed identity conflicts with existing data")
    db.flush()
    manager = next(x for x in values if x.role == "manager")
    for value in values:
        if value.role == "employee" and db.get(ManagerAssignment, value.id) is None:
            db.add(
                ManagerAssignment(
                    employee_id=value.id, manager_id=manager.id, organization_id=org.id
                )
            )
    db.commit()
    if policy_store is not None:
        policy_store.initialize_demo_policy(org.id)
    return {
        "organization_id": str(org.id),
        "identities": len(values),
        "policy_seeded": policy_store is not None,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment", required=True, choices=["demo"])
    parser.add_argument("--organization-name", default="Demo Company")
    args = parser.parse_args()
    identities = json.loads(Path(__file__).with_name("identities.json").read_text())
    with session_factory()() as db:
        print(
            json.dumps(
                seed(
                    db,
                    args.organization_name,
                    identities,
                )
            )
        )
