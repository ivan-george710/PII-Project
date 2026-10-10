# apps/api/app/db/models

Organization, user, manager assignment, conversation, message, attachment, company rule, and PII event models.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Export/register all models. Owner: [issue 3](../../../../../docs/issues/03-auth-company-setup.md). |
| `auth_session.py` | Existing | Hashed opaque session tokens, user ownership, and expiry; logout/reset revokes sessions. Owner: [issue 3](../../../../../docs/issues/03-auth-company-setup.md). |
| `organization.py` | Existing | Company identity and administrative settings. Owner: [issue 3](../../../../../docs/issues/03-auth-company-setup.md). |
| `user.py` | Existing | Unique email text, password hash, company membership, and role. Owner: [issue 3](../../../../../docs/issues/03-auth-company-setup.md). |
| `manager_assignment.py` | Existing | Employee-to-manager relationship within a company. Owner: [issue 3](../../../../../docs/issues/03-auth-company-setup.md). |
| `conversation.py` | Existing | Employee-owned conversations. Owner: [issue 2](../../../../../docs/issues/02-employee-chat.md). |
| `message.py` | Existing | Conversation turns and safe provider history. Owner: [issue 2](../../../../../docs/issues/02-employee-chat.md). |
| `attachment.py` | Existing | File ownership, storage references, and processing state. Owner: [issue 2](../../../../../docs/issues/02-employee-chat.md). |
| `rule.py` | Existing | Company built-in overrides, custom rules, and policy versions. Owner: [issue 4](../../../../../docs/issues/04-manager-settings-reports.md). |
| `pii_event.py` | Existing | Submission findings/actions and idempotency identifiers. Owner: [issue 4](../../../../../docs/issues/04-manager-settings-reports.md). |
| `submission.py` | Existing | Persist submission state, idempotency, request hash, and stream result. Owner: [issue 2](../../../../../docs/issues/02-employee-chat.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)
- [Issue 3: Deliver local authentication, company setup, and employee-manager assignments](../../../../../docs/issues/03-auth-company-setup.md) — [GitHub #3](https://github.com/ivan-george710/PII-Project/issues/3)
- [Issue 4: Deliver manager rule settings, custom rules, and employee PII reporting](../../../../../docs/issues/04-manager-settings-reports.md) — [GitHub #4](https://github.com/ivan-george710/PII-Project/issues/4)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.

All implemented models are exported by `__init__.py` so Alembic metadata includes chat tables without importing HTTP routes. Chat metadata types, indexes and constraints match migration `0004_employee_chat`.

## PR 18 integration

`file_blob.py`: `private_file_blobs`, private original/sanitized bytes keyed to an owned attachment and removed by cascade when the attachment is deleted.
