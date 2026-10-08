import base64
import json
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.auth.permissions import require_manager
from app.auth.sessions import current_identity
from app.db.models import ManagerAssignment, Organization, User
from app.db.session import get_db
from app.schemas.common import ApiError
from app.schemas.organization import (
    AssignmentInput,
    AssignmentResponse,
    AssignmentsPage,
    OrganizationResponse,
    OrganizationUpdate,
    UsersPage,
)
from app.services.organization import assign

router = APIRouter(prefix="/api/v1/organization", tags=["Company setup"])


def page(db, model, identity, limit, cursor, extra=None):
    # Cursor is company-bound and carries the descending timestamp/id pair.
    stamp_column = model.updated_at if model is ManagerAssignment else model.created_at
    id_column = model.employee_id if model is ManagerAssignment else model.id
    query = select(model).where(model.organization_id == identity.organization_id)
    if extra is not None:
        query = query.where(extra)
    if cursor:
        try:
            value = json.loads(base64.urlsafe_b64decode(cursor.encode()))
            if (
                value["company"] != str(identity.organization_id)
                or value["type"] != model.__tablename__
            ):
                raise ValueError()
            stamp, ident = datetime.fromisoformat(value["time"]), UUID(value["id"])
        except Exception:
            raise ApiError(422, "INVALID_CURSOR", "Invalid page cursor") from None
        query = query.where(
            or_(stamp_column < stamp, and_(stamp_column == stamp, id_column < ident))
        )
    items = list(
        db.scalars(
            query.order_by(stamp_column.desc(), id_column.desc()).limit(limit + 1)
        )
    )
    next_cursor = None
    if len(items) > limit:
        last = items[limit - 1]
        next_cursor = base64.urlsafe_b64encode(
            json.dumps(
                {
                    "company": str(identity.organization_id),
                    "type": model.__tablename__,
                    "time": getattr(last, stamp_column.key).isoformat(),
                    "id": str(getattr(last, id_column.key)),
                }
            ).encode()
        ).decode()
    return {"items": items[:limit], "next_cursor": next_cursor}


@router.get("", response_model=OrganizationResponse)
def get_organization(identity=Depends(current_identity), db: Session = Depends(get_db)):
    return db.get(Organization, identity.organization_id)


@router.patch("", response_model=OrganizationResponse)
def update(
    body: OrganizationUpdate,
    identity=Depends(require_manager),
    db: Session = Depends(get_db),
):
    org = db.get(Organization, identity.organization_id)
    org.name = body.name
    db.commit()
    db.refresh(org)
    return org


@router.get("/users", response_model=UsersPage)
def users(
    limit: int = Query(25, ge=1, le=100),
    cursor: str | None = Query(None, max_length=512),
    role: Literal["employee", "manager"] | None = None,
    identity=Depends(require_manager),
    db: Session = Depends(get_db),
):
    extra = User.active.is_(True)
    if role:
        extra = and_(extra, User.role == role)
    return page(db, User, identity, limit, cursor, extra)


@router.get("/assignments", response_model=AssignmentsPage)
def assignments(
    limit: int = Query(25, ge=1, le=100),
    cursor: str | None = Query(None, max_length=512),
    identity=Depends(require_manager),
    db: Session = Depends(get_db),
):
    return page(db, ManagerAssignment, identity, limit, cursor)


@router.put("/assignments/{employee_id}", response_model=AssignmentResponse)
def put_assignment(
    employee_id: UUID,
    body: AssignmentInput,
    identity=Depends(require_manager),
    db: Session = Depends(get_db),
):
    return assign(db, identity, employee_id, body.manager_id)


@router.delete("/assignments/{employee_id}", status_code=204)
def delete_assignment(
    employee_id: UUID, identity=Depends(require_manager), db: Session = Depends(get_db)
):
    item = db.get(ManagerAssignment, employee_id)
    if not item or item.organization_id != identity.organization_id:
        raise ApiError(404, "NOT_FOUND", "Assignment unavailable")
    db.delete(item)
    db.commit()
    return Response(status_code=204)
