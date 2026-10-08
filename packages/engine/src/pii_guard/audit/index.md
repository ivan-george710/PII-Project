# packages/engine/src/pii_guard/audit

Structured findings and action events with source locations and applied rules, including detections allowed by disabled rules. The backend associates events with employees and managers.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Package marker and relevant public exports. |
| `events.py` | Planned | Produce source-linked detection/action events without user/database coupling. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
