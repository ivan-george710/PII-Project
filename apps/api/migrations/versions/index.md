# apps/api/migrations/versions

Contains the modules and files listed below.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `0001_company_identity_policy_events.py` | Planned | Company, users, assignments, rule versions, and event tables (issue 3). |
| `0002_conversations_messages_attachments.py` | Planned | Chat and attachment tables (issue 2); independent of company migration using scalar identity references until integrated metadata validation. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
