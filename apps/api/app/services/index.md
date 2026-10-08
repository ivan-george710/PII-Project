# apps/api/app/services

Application workflows for sanitization before LLM submission, chat, reporting, company rules, and organization setup.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Services package marker (issue 4). |
| `guard.py` | Planned | Apply company policy, sanitize, block failures, and publish events (issue 2). |
| `chat.py` | Planned | Persist conversation flow, build safe history, and stream LLM results (issue 2). |
| `reporting.py` | Planned | Idempotent event ingestion and manager report queries (issue 3). |
| `rules.py` | Planned | Policy snapshots/versioning and bounded custom-rule preview (issue 3). |
| `organization.py` | Planned | Company membership and manager-assignment workflows (issue 3). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
