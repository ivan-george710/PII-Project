# apps/api/tests

Backend tests for auth, access control, rules, reporting, and orchestration.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `conftest.py` | Planned | Shared isolated database/session fixtures (issue 4). |
| `test_auth.py` | Planned | WorkOS/session behavior and role enforcement (issue 3). |
| `test_organization.py` | Planned | Membership and manager-assignment boundaries (issue 3). |
| `test_rules.py` | Planned | Policy versioning, isolation, preview, and invalid-pattern behavior (issue 3). |
| `test_reports.py` | Planned | Report authorization and idempotent event ingestion (issue 3). |
| `test_chat.py` | Planned | Safe history, guarded provider calls, streaming, and retry behavior (issue 2). |
| `test_uploads.py` | Planned | Upload authorization, supported inputs, and output access (issue 2). |
| `test_guard.py` | Planned | Sanitized-only payloads, disabled rules, and blocked failures (issue 2). |
| `test_health.py` | Planned | Readiness and production configuration checks (issue 4). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
