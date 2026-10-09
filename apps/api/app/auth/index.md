# apps/api/app/auth

Password verification, database session validation, and company/role access checks.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Auth package marker. Owner: [issue 3](../../../../docs/issues/03-auth-company-setup.md). |
| `passwords.py` | Existing | Password hashing and verification. Owner: [issue 3](../../../../docs/issues/03-auth-company-setup.md). |
| `sessions.py` | Existing | Validate sessions and resolve company/user identity. Owner: [issue 3](../../../../docs/issues/03-auth-company-setup.md). |
| `permissions.py` | Existing | Enforce company, role, manager-assignment, and policy-edit permissions. Owner: [issue 3](../../../../docs/issues/03-auth-company-setup.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 3: Deliver local authentication, company setup, and employee-manager assignments](../../../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
