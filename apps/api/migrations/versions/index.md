# apps/api/migrations/versions

Contains the modules and files listed below.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `0001_company_identity.py` | Existing | Historical initial company/provider schema and manager assignments; followed by the local auth migration. Owner: [issue 3](../../../../docs/issues/03-auth-company-setup.md). |
| `0002_local_auth.py` | Existing | Preserve company/user IDs and assignments, remove provider identity columns, add unique emails/password hashes and session storage. Followed by 0003_signup; future feature migrations follow the current head. Owner: [issue 3](../../../../docs/issues/03-auth-company-setup.md). |
| `0003_signup.py` | Existing | Change email storage to unrestricted text for simple signup. Owner: [issue 3](../../../../docs/issues/03-auth-company-setup.md). |
| `0004_employee_chat.py` | Existing | Chat and attachment tables; enforce ownership relationships and extend the deployed 0003_signup head with model-parity checks. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `0005_company_policy_events.py` | Existing | Versioned company policies and PII event tables; company/employee foreign keys and idempotency constraints. Owner: [issue 4](../../../../docs/issues/04-manager-settings-reports.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)
- [Issue 3: Deliver local authentication, company setup, and employee-manager assignments](../../../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.

## PR 18 integration

`0006_private_file_blobs.py`: additive durable file-byte table after `0005_company_policy_events`; apply before deploying this PR.
