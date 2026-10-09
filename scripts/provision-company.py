"""Trusted operator setup for local company accounts; passwords are never printed."""

import argparse
import getpass
from uuid import UUID

from pydantic import Field
from sqlalchemy import delete, select

from app.auth.passwords import hash_password
from app.db.models import AuthSession, Organization, User
from app.db.session import session_factory
from app.schemas.common import Schema


class ProvisionUser(Schema):
    email: str
    display_name: str = Field(min_length=1, max_length=120)
    role: str = Field(pattern=r"^(employee|manager)$")


def provision(db, organization_id, name, identity, password, reset_password=False):
    value = ProvisionUser.model_validate(identity)
    email = str(value.email).lower()
    user = db.scalar(select(User).where(User.email == email))
    if user and (user.organization_id != organization_id or user.role != value.role):
        raise ValueError("Existing company/role mapping conflict")
    org = db.get(Organization, organization_id)
    if org is None:
        org = Organization(id=organization_id, name=name)
        db.add(org)
        db.flush()
    if user is None:
        user = User(
            organization_id=org.id,
            email=email,
            display_name=value.display_name,
            role=value.role,
        )
        db.add(user)
    if not user.password_hash or reset_password:
        user.password_hash = hash_password(password)
        user.failed_login_attempts = 0
        user.locked_until = None
        if user.id:
            db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    db.commit()
    return {
        "organization_id": str(org.id),
        "user_id": str(user.id),
        "email": email,
        "role": user.role,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--organization-id", required=True, type=UUID)
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--role", choices=["employee", "manager"], default="employee")
    parser.add_argument("--reset-password", action="store_true")
    args = parser.parse_args()
    if not 1 <= len(args.name.strip()) <= 120:
        raise ValueError("Company name must be 1–120 characters")
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise ValueError("Passwords do not match")
    with session_factory()() as db:
        print(
            provision(
                db,
                args.organization_id,
                args.name.strip(),
                {
                    "email": args.email,
                    "display_name": args.display_name,
                    "role": args.role,
                },
                password,
                args.reset_password,
            )
        )
