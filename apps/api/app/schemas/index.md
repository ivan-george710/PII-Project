# apps/api/app/schemas

API request and response models, including validation and serialization.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Schema package marker (issue 4). |
| `common.py` | Existing | Pydantic v2 strict HealthResponse model; future shared API errors/pagination belong here. |
| `auth.py` | Planned | Session identity and roles (issue 3). |
| `chat.py` | Planned | Conversation, message, submission, and stream events (issue 2). |
| `uploads.py` | Planned | File metadata, processing state, and authorized output responses (issue 2). |
| `reports.py` | Planned | Report filters, event summaries, and details (issue 3). |
| `rules.py` | Planned | Company policy, custom rule, and preview request/response types (issue 3). |
| `organization.py` | Planned | Company/user/assignment request/response types (issue 3). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
