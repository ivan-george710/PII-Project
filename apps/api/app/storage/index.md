# apps/api/app/storage

Original and sanitized file storage access, retention, and cleanup. Actual uploads belong outside the tracked source tree.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Storage package marker. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `files.py` | Planned | Separate original/sanitized artifact storage and enforce authorized access. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |
| `cleanup.py` | Planned | Apply configured file retention and cleanup. Owner: [issue 2](../../../../docs/issues/02-employee-chat.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
