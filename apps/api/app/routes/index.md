# apps/api/app/routes

HTTP routes for auth, chat, uploads, reports, rules, organization setup, and health.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Routes package marker. Owner: [issue 5](../../../../docs/issues/05-platform-deployment.md). |
| `auth.py` | Existing | Login/callback/logout and current-session endpoints. Owner: [issue 3](../../../../docs/issues/03-auth-company-setup.md). |
| `chat.py` | Planned | Conversation, submission, and streaming endpoints. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `uploads.py` | Planned | Authorized upload and sanitized-file access endpoints. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `reports.py` | Planned | Assigned-employee report and event detail endpoints. Owner: [issue 4](../../../../docs/issues/04-manager-settings-reports.md). |
| `rules.py` | Planned | Company rule CRUD/toggles and sample preview endpoints. Owner: [issue 4](../../../../docs/issues/04-manager-settings-reports.md). |
| `organization.py` | Existing | Company setup/user/manager-assignment endpoints using shared real dependencies. Owner: [issue 3](../../../../docs/issues/03-auth-company-setup.md). |
| `health.py` | Existing | Preserve the existing health response and commit field. Owner: [issue 5](../../../../docs/issues/05-platform-deployment.md). |
| `demo.py` | Implemented | Authenticated built-in sample catalog and attachment selection endpoints. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)
- [Issue 3: Deliver local authentication, company setup, and employee-manager assignments](../../../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)
- [Issue 5: Connect the app and document basic setup](../../../../docs/issues/05-platform-deployment.md) — [GitHub #5](https://github.com/ivan-george710/PII-Project/issues/5)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.

## Delivered interface update

`organization.py` now also implements manager-only `POST /api/v1/organization/employees`, creating a same-company employee plus an immediate-manager assignment atomically.
