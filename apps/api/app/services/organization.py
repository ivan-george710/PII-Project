from app.db.models import ManagerAssignment, User
from app.schemas.common import ApiError


def assign(db, identity, employee_id, manager_id):
    employee, manager = db.get(User, employee_id), db.get(User, manager_id)
    if any(
        u is None or u.organization_id != identity.organization_id or not u.active
        for u in (employee, manager)
    ):
        raise ApiError(404, "NOT_FOUND", "User unavailable")
    if employee.role != "employee" or manager.role != "manager":
        raise ApiError(422, "INVALID_ASSIGNMENT", "Choose an employee and a manager")
    assignment = db.get(ManagerAssignment, employee_id)
    if assignment is None:
        assignment = ManagerAssignment(
            employee_id=employee_id, organization_id=identity.organization_id
        )
        db.add(assignment)
    assignment.manager_id = manager_id
    db.commit()
    db.refresh(assignment)
    return assignment
