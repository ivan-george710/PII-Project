# apps/api/app/storage

Original and sanitized file storage access, retention, and cleanup. Actual uploads belong outside the tracked source tree.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Storage package marker. |
| `files.py` | Planned | Separate original/sanitized artifact storage and enforce authorized access. |
| `cleanup.py` | Planned | Apply configured file retention and cleanup. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
