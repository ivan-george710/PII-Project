from fastapi import Depends

from app.auth.sessions import current_identity
from app.db.models import ManagerAssignment, User
from app.schemas.auth import SessionIdentity
from app.schemas.common import ApiError


def require_manager(identity: SessionIdentity = Depends(current_identity)):
    if identity.role != "manager":
        raise ApiError(403, "FORBIDDEN", "Manager access required")
    return identity


def require_employee(identity: SessionIdentity = Depends(current_identity)):
    if identity.role != "employee":
        raise ApiError(403, "FORBIDDEN", "Employee access required")
    return identity


def require_company(identity, organization_id):
    if identity.organization_id != organization_id:
        raise ApiError(404, "NOT_FOUND", "Resource unavailable")


def require_assigned_employee(identity, employee_id, db):
    if identity.role != "manager":
        raise ApiError(403, "FORBIDDEN", "Manager access required")
    employee = db.get(User, employee_id)
    assignment = db.get(ManagerAssignment, employee_id)
    if (
        not employee
        or not employee.active
        or not assignment
        or assignment.manager_id != identity.user_id
        or assignment.organization_id != identity.organization_id
    ):
        raise ApiError(404, "NOT_FOUND", "Resource unavailable")
    return employee
