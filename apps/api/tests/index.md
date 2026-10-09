# apps/api/tests

Backend tests for auth, access control, rules, reporting, and orchestration.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `conftest.py` | Existing | Shared isolated database/session fixtures. Owner: [issue 3](../../../docs/issues/03-auth-company-setup.md). |
| `test_migrations.py` | Existing | Upgrade the historical schema with existing company/users/assignments; check data preservation and model parity. Owner: [issue 3](../../../docs/issues/03-auth-company-setup.md). |
| `test_auth.py` | Existing | Local password/session behavior, expiry, revocation, CSRF, lockout, and role enforcement. Owner: [issue 3](../../../docs/issues/03-auth-company-setup.md). |
| `test_organization.py` | Existing | Membership and manager-assignment boundaries. Owner: [issue 3](../../../docs/issues/03-auth-company-setup.md). |
| `test_rules.py` | Planned | Policy versioning, isolation, preview, and invalid-pattern behavior. Owner: [issue 4](../../../docs/issues/04-manager-settings-reports.md). |
| `test_reports.py` | Planned | Report authorization and idempotent event ingestion. Owner: [issue 4](../../../docs/issues/04-manager-settings-reports.md). |
| `test_chat.py` | Planned | Safe history, guarded provider calls, streaming, and retry behavior. Owner: [issue 2](../../../docs/issues/02-employee-chat.md). |
| `test_uploads.py` | Planned | Upload authorization, supported inputs, and output access. Owner: [issue 2](../../../docs/issues/02-employee-chat.md). |
| `test_guard.py` | Planned | Sanitized-only payloads, disabled rules, and blocked failures. Owner: [issue 2](../../../docs/issues/02-employee-chat.md). |
| `test_health.py` | Existing | Preserve the existing health smoke test. Owner: [issue 5](../../../docs/issues/05-platform-deployment.md). |
| `test_demo.py` | Planned | Catalog scoping, feature toggle, selection idempotency, and file limits. Owner: [issue 2](../../../docs/issues/02-employee-chat.md). |
| `test_seed.py` | Existing | Trusted fictional seeding, explicit opt-in, and idempotency checks. Owner: [issue 3](../../../docs/issues/03-auth-company-setup.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)
- [Issue 3: Deliver local authentication, company setup, and employee-manager assignments](../../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)
- [Issue 5: Connect the app and document basic setup](../../../docs/issues/05-platform-deployment.md) — [GitHub #5](https://github.com/ivan-george710/PII-Project/issues/5)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
