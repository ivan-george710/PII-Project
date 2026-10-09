from conftest import login_as


def test_rules_get_defaults_and_authorization(env):
    manager = env.users[0]
    employee = env.users[1]
    client = env.client

    # Employee gets 403 Forbidden
    emp_headers = login_as(env, employee)
    res = client.get("/api/v1/rules", headers=emp_headers)
    assert res.status_code == 403

    # Manager gets default policy snapshot with version 1 and 13 rules enabled
    mgr_headers = login_as(env, manager)
    res = client.get("/api/v1/rules", headers=mgr_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == 1
    assert data["organization_id"] == str(manager.organization_id)
    assert len(data["builtins"]) == 13
    assert data["builtins"]["CREDIT_CARD"] is True
    assert data["builtins"]["FACE"] is True
    assert data["custom_rules"] == []


def test_rules_update_builtins_and_optimistic_conflict(env):
    manager = env.users[0]
    client = env.client
    headers = login_as(env, manager)

    # Initial get
    snap = client.get("/api/v1/rules", headers=headers).json()
    assert snap["version"] == 1

    # Stale version update gets 409
    res = client.patch(
        "/api/v1/rules/builtins",
        json={
            "expected_version": 999,
            "updates": [{"rule_id": "CREDIT_CARD", "enabled": False}],
        },
        headers=headers,
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "POLICY_VERSION_CONFLICT"

    # Valid update increments version
    res = client.patch(
        "/api/v1/rules/builtins",
        json={
            "expected_version": 1,
            "updates": [{"rule_id": "CREDIT_CARD", "enabled": False}],
        },
        headers=headers,
    )
    assert res.status_code == 200
    updated = res.json()
    assert updated["version"] == 2
    assert updated["builtins"]["CREDIT_CARD"] is False
    assert updated["builtins"]["FACE"] is True


def test_rules_toggle_all(env):
    manager = env.users[0]
    client = env.client
    headers = login_as(env, manager)

    snap = client.get("/api/v1/rules", headers=headers).json()
    v = snap["version"]

    # Toggle all off
    res = client.post(
        "/api/v1/rules/toggle-all",
        json={"expected_version": v, "enabled": False},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == v + 1
    assert all(val is False for val in data["builtins"].values())

    # Toggle all on
    res = client.post(
        "/api/v1/rules/toggle-all",
        json={"expected_version": v + 1, "enabled": True},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["version"] == v + 2
    assert all(val is True for val in data["builtins"].values())


def test_custom_rule_lifecycle(env):
    manager = env.users[0]
    client = env.client
    headers = login_as(env, manager)

    snap = client.get("/api/v1/rules", headers=headers).json()
    v = snap["version"]

    # Create custom rule
    res = client.post(
        "/api/v1/rules/custom",
        json={
            "expected_version": v,
            "name": "Project Secret",
            "kind": "exact",
            "pattern": "SuperSecretCodename",
            "case_sensitive": False,
            "enabled": True,
        },
        headers=headers,
    )
    assert res.status_code == 201
    created = res.json()
    assert created["policy_version"] == v + 1
    rule_id = created["rule"]["id"]
    assert created["rule"]["name"] == "Project Secret"

    # Duplicate name rejection
    res = client.post(
        "/api/v1/rules/custom",
        json={
            "expected_version": v + 1,
            "name": "project secret",
            "kind": "exact",
            "pattern": "OtherPattern",
            "case_sensitive": False,
            "enabled": True,
        },
        headers=headers,
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "RULE_NAME_EXISTS"

    # Update custom rule
    res = client.patch(
        f"/api/v1/rules/custom/{rule_id}",
        json={
            "expected_version": v + 1,
            "name": "Project Secret Renamed",
            "enabled": False,
        },
        headers=headers,
    )
    assert res.status_code == 200
    updated = res.json()
    assert updated["policy_version"] == v + 2
    assert updated["rule"]["name"] == "Project Secret Renamed"
    assert updated["rule"]["enabled"] is False

    # Delete custom rule
    res = client.delete(
        f"/api/v1/rules/custom/{rule_id}?expected_version={v + 2}",
        headers=headers,
    )
    assert res.status_code == 200
    deleted = res.json()
    assert deleted["deleted_id"] == rule_id
    assert deleted["policy_version"] == v + 3


def test_custom_rule_invalid_regex_and_empty_matching_rejection(env):
    manager = env.users[0]
    client = env.client
    headers = login_as(env, manager)

    snap = client.get("/api/v1/rules", headers=headers).json()
    v = snap["version"]

    # Invalid regex syntax
    res = client.post(
        "/api/v1/rules/custom",
        json={
            "expected_version": v,
            "name": "Broken Regex",
            "kind": "regex",
            "pattern": "[invalid(regex",
            "case_sensitive": True,
            "enabled": True,
        },
        headers=headers,
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "INVALID_REGEX"

    # Empty-matching regex (.*)
    res = client.post(
        "/api/v1/rules/custom",
        json={
            "expected_version": v,
            "name": "Empty Matching",
            "kind": "regex",
            "pattern": ".*",
            "case_sensitive": True,
            "enabled": True,
        },
        headers=headers,
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "EMPTY_MATCHING_REGEX"


def test_rule_preview_endpoint(env):
    manager = env.users[0]
    client = env.client
    headers = login_as(env, manager)

    # Preview exact match
    res = client.post(
        "/api/v1/rules/preview",
        json={
            "kind": "exact",
            "pattern": "secret",
            "case_sensitive": False,
            "sample_text": "This is a SECRET mission with secret documents.",
        },
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 2
    assert len(data["matches"]) == 2
    assert data["matches"][0]["start"] == 10
    assert data["matches"][0]["end"] == 16

    # Preview regex match
    res = client.post(
        "/api/v1/rules/preview",
        json={
            "kind": "regex",
            "pattern": r"\bEMP-\d{4}\b",
            "case_sensitive": True,
            "sample_text": "Contact EMP-1234 or EMP-5678 for access.",
        },
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 2
    assert len(data["matches"]) == 2
