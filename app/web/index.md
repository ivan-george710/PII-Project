# app/web

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `__init__.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `models.py` | Implemented; integration in progress | Pydantic local API boundaries, text submission and original/redacted chat response fields. |
| `server.py` | Implemented; integration in progress | Trusted-local real-engine document/text processing, samples/original previews, report sync and verified approval-gated artifacts. |

Subdirectories contain their own manifests when touched. Engine implementation and phase evidence remain authoritative.

| `manager_client.py` | Implemented; integration in progress | HTTPS/loopback manager transport; sends affected-only reports and checks fresh revision/hash-bound approval. |
