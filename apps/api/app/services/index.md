# apps/api/app/services

Application workflows for sanitization before LLM submission, chat, reporting, company rules, and organization setup.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Services package marker. Owner: [issue 5](../../../../docs/issues/05-platform-deployment.md). |
| `guard.py` | Planned | Apply company policy, sanitize, block failures, and publish events. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `chat.py` | Planned | Persist conversation flow, build safe history, and stream LLM results. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `reporting.py` | Existing | Idempotent event ingestion and manager report queries. Owner: [issue 4](../../../../docs/issues/04-manager-settings-reports.md). |
| `rules.py` | Existing | Policy snapshots/versioning and bounded custom-rule preview. Owner: [issue 4](../../../../docs/issues/04-manager-settings-reports.md). |
| `organization.py` | Existing | Company membership and manager-assignment workflows. Owner: [issue 3](../../../../docs/issues/03-auth-company-setup.md). |
| `demo.py` | Planned | Load safe sample assets and create employee-owned attachments. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)
- [Issue 3: Deliver local authentication, company setup, and employee-manager assignments](../../../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)
- [Issue 5: Connect the app and document basic setup](../../../../docs/issues/05-platform-deployment.md) — [GitHub #5](https://github.com/ivan-george710/PII-Project/issues/5)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
