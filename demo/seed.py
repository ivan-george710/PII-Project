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


def seed(
    db, name, identities, user_map=None, workos_organization_id=None, policy_store=None
):
    settings = get_settings()
    if settings.app_env == "production":
        raise ValueError("Fictional seeding is forbidden in production")
    values = TypeAdapter(list[SeedUser]).validate_python(identities)
    if sorted(x.role for x in values) != ["employee", "employee", "manager"]:
        raise ValueError("Seed requires one manager and two employees")
    if not user_map and not settings.demo_adapters_enabled:
        raise ValueError(
            "Supply a trusted WorkOS user map, or explicitly enable development adapters"
        )
    if user_map:
        if set(user_map) != {str(u.email) for u in values}:
            raise ValueError("Map must contain exactly the seed identities")
        if len(set(user_map.values())) != len(values):
            raise ValueError("Each identity must map to a distinct WorkOS user")
        from app.auth.workos import get_gateway

        client = get_gateway().client
        for value in values:
            remote = client.user_management.get_user(id=user_map[str(value.email)])
            if remote.email != value.email:
                raise ValueError("WorkOS user map email mismatch")
            if workos_organization_id:
                memberships = (
                    client.organization_membership.list_organization_memberships(
                        user_id=remote.id,
                        organization_id=workos_organization_id,
                        statuses=["active"],
                    )
                )
                if not memberships.data:
                    raise ValueError("WorkOS organization membership missing")
    org = db.get(Organization, COMPANY_ID)
    if org is None:
        org = Organization(
            id=COMPANY_ID, name=name, workos_organization_id=workos_organization_id
        )
        db.add(org)
        db.flush()
    elif org.name != name or org.workos_organization_id != workos_organization_id:
        raise ValueError("Seed target differs from existing company")
    for value in values:
        expected = (user_map or {}).get(str(value.email), "demo_" + str(value.id))
        user = db.get(User, value.id)
        if user is None:
            db.add(
                User(
                    id=value.id,
                    organization_id=org.id,
                    workos_user_id=expected,
                    email=str(value.email),
                    display_name=value.display_name,
                    role=value.role,
                )
            )
        elif (
            user.organization_id != org.id
            or user.workos_user_id != expected
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
    parser.add_argument("--user-map", type=Path)
    parser.add_argument("--workos-organization-id")
    args = parser.parse_args()
    identities = json.loads(Path(__file__).with_name("identities.json").read_text())
    mapping = json.loads(args.user_map.read_text()) if args.user_map else None
    with session_factory()() as db:
        print(
            json.dumps(
                seed(
                    db,
                    args.organization_name,
                    identities,
                    mapping,
                    args.workos_organization_id,
                )
            )
        )
