# apps/api/app/routes

HTTP routes for auth, chat, uploads, reports, rules, organization setup, and health.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Routes package marker (issue 4). |
| `auth.py` | Planned | Login/callback/logout and current-session endpoints (issue 3). |
| `chat.py` | Planned | Conversation, submission, and streaming endpoints (issue 2). |
| `uploads.py` | Planned | Authorized upload and sanitized-file access endpoints (issue 2). |
| `reports.py` | Planned | Assigned-employee report and event detail endpoints (issue 3). |
| `rules.py` | Planned | Company rule CRUD/toggles and sample preview endpoints (issue 3). |
| `organization.py` | Planned | Company setup, user, and manager-assignment endpoints (issue 3). |
| `health.py` | Existing | Service readiness/liveness endpoints (issue 4). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
