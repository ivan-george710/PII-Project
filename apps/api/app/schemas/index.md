# apps/api/app/schemas

API request and response models, including validation and serialization.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Schema package marker. Owner: [issue 5](../../../../docs/issues/05-platform-deployment.md). |
| `common.py` | Existing | Existing HealthResponse plus shared API error/pagination models. Owner: [issue 5](../../../../docs/issues/05-platform-deployment.md). |
| `auth.py` | Existing | Session identity and roles. Owner: [issue 3](../../../../docs/issues/03-auth-company-setup.md). |
| `chat.py` | Planned | Conversation, message, submission, and stream events. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `uploads.py` | Planned | File metadata, processing state, and authorized output responses. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `reports.py` | Planned | Report filters, event summaries, and details. Owner: [issue 4](../../../../docs/issues/04-manager-settings-reports.md). |
| `rules.py` | Planned | Company policy, custom rule, and preview request/response types. Owner: [issue 4](../../../../docs/issues/04-manager-settings-reports.md). |
| `organization.py` | Existing | Company/user/assignment request/response types. Owner: [issue 3](../../../../docs/issues/03-auth-company-setup.md). |
| `demo.py` | Planned | Pydantic sample union and attachment-selection request models. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Runtime validation

Use Pydantic v2 BaseModel contracts with forbidden extra fields, strict booleans/integers, constrained values, and explicit boundary validation. Follow the exact models/API shapes in docs/issues. Python types and dataclasses alone do not validate external inputs.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)
- [Issue 3: Deliver local authentication, company setup, and employee-manager assignments](../../../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)
- [Issue 5: Connect the app and document basic setup](../../../../docs/issues/05-platform-deployment.md) — [GitHub #5](https://github.com/ivan-george710/PII-Project/issues/5)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
