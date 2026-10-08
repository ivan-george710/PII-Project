# apps/api/app/auth

WorkOS integration, session validation, and company/role access checks.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Auth package marker. |
| `workos.py` | Planned | WorkOS login/callback/logout integration and identity mapping. |
| `sessions.py` | Planned | Validate sessions and resolve company/user identity. |
| `permissions.py` | Planned | Enforce company, role, manager-assignment, and policy-edit permissions. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
