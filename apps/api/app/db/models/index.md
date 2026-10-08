# apps/api/app/db/models

Organization, user, manager assignment, conversation, message, attachment, company rule, and PII event models.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Export/register all models (issue 4). |
| `organization.py` | Planned | Company identity and administrative settings (issue 3). |
| `user.py` | Planned | WorkOS identity, company membership, and role (issue 3). |
| `manager_assignment.py` | Planned | Employee-to-manager relationship within a company (issue 3). |
| `conversation.py` | Planned | Employee-owned conversations (issue 2). |
| `message.py` | Planned | Conversation turns and safe provider history (issue 2). |
| `attachment.py` | Planned | File ownership, storage references, and processing state (issue 2). |
| `rule.py` | Planned | Company built-in overrides, custom rules, and policy versions (issue 3). |
| `pii_event.py` | Planned | Submission findings/actions and idempotency identifiers (issue 3). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
