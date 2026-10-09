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


def create_employee(db, identity, body):
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError
    from app.auth.passwords import hash_password

    manager_id = body.manager_id or identity.user_id
    manager = db.get(User, manager_id)
    if (not manager or not manager.active or manager.role != "manager"
            or manager.organization_id != identity.organization_id):
        raise ApiError(404, "NOT_FOUND", "Manager unavailable")
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        # Do not reveal which company owns an existing account.
        raise ApiError(409, "ACCOUNT_EXISTS", "An account with this email already exists")
    employee = User(
        organization_id=identity.organization_id,
        email=email,
        display_name=body.display_name,
        role="employee",
        password_hash=hash_password(body.password.get_secret_value()),
    )
    try:
        db.add(employee)
        db.flush()
        assignment = ManagerAssignment(
            employee_id=employee.id,
            manager_id=manager_id,
            organization_id=identity.organization_id,
        )
        db.add(assignment)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "ACCOUNT_EXISTS", "Account could not be created; refresh and try again") from None
    db.refresh(employee)
    db.refresh(assignment)
    return {"user": employee, "assignment": assignment}
