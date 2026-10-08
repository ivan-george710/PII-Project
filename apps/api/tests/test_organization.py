import pytest
from conftest import login_as
from sqlalchemy.exc import IntegrityError

from app.auth.permissions import require_assigned_employee
from app.db.models import ManagerAssignment
from app.schemas.auth import SessionIdentity
from app.schemas.common import ApiError


def test_company_update_validation_and_employee_role(env):
    h = login_as(env, env.users[0])
    c = env.client
    assert (
        c.patch(
            "/api/v1/organization", json={"name": "  New name  "}, headers=h
        ).json()["name"]
        == "New name"
    )
    response = c.patch(
        "/api/v1/organization", json={"name": "secret", "role": "manager"}, headers=h
    )
    assert response.status_code == 422 and "secret" not in response.text
    assert (
        c.patch("/api/v1/organization", json={"name": "   "}, headers=h).status_code
        == 422
    )
    h = login_as(env, env.users[1])
    assert (
        c.patch("/api/v1/organization", json={"name": "No"}, headers=h).status_code
        == 403
    )
    assert c.get("/api/v1/organization/users").status_code == 403


def test_assignment_scope_roles_reassignment_and_delete(env):
    manager, employee, other, foreign = env.users
    h = login_as(env, manager)
    c = env.client
    path = "/api/v1/organization/assignments/" + str(employee.id)
    assert (
        c.put(path, json={"manager_id": str(manager.id)}, headers=h).status_code == 200
    )
    assert (
        c.put(path, json={"manager_id": str(employee.id)}, headers=h).status_code == 422
    )
    assert (
        c.put(
            "/api/v1/organization/assignments/" + str(foreign.id),
            json={"manager_id": str(manager.id)},
            headers=h,
        ).status_code
        == 404
    )
    identity = SessionIdentity(
        user_id=manager.id,
        organization_id=manager.organization_id,
        role=manager.role,
        email=manager.email,
        display_name=manager.display_name,
    )
    assert require_assigned_employee(identity, employee.id, env.db).id == employee.id
    assert c.put(path, json={"manager_id": str(other.id)}, headers=h).status_code == 200
    with pytest.raises(ApiError):
        require_assigned_employee(identity, employee.id, env.db)
    assert c.delete(path, headers=h).status_code == 204
    assert c.delete(path, headers=h).status_code == 404


def test_pagination_and_company_bound_cursor(env):
    c = env.client
    login_as(env, env.users[0])
    r = c.get("/api/v1/organization/users?limit=1").json()
    assert len(r["items"]) == 1 and r["next_cursor"]
    second = c.get(
        "/api/v1/organization/users", params={"limit": 1, "cursor": r["next_cursor"]}
    ).json()
    assert r["items"][0]["id"] != second["items"][0]["id"]
    login_as(env, env.users[3])
    env.users[3].role = "manager"
    env.db.commit()
    assert (
        c.get(
            "/api/v1/organization/users", params={"cursor": r["next_cursor"]}
        ).status_code
        == 422
    )
    assert c.get("/api/v1/organization/users?limit=0").status_code == 422


def test_database_rejects_cross_company_assignment(env):
    env.db.add(
        ManagerAssignment(
            employee_id=env.users[3].id,
            manager_id=env.users[0].id,
            organization_id=env.companies[0].id,
        )
    )
    with pytest.raises(IntegrityError):
        env.db.commit()
    env.db.rollback()
