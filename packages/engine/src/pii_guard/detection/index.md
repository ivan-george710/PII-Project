# packages/engine/src/pii_guard/detection

Text PII detection, face detection, and candidate validation. Face detection should cover standalone and embedded images, including overlapping crop passes.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Package marker and relevant public exports. |
| `text.py` | Planned | Run Presidio and custom recognizers on extracted text. |
| `faces.py` | Planned | Backend-compatible whole-image/crop face detection and duplicate suppression. |
| `validation.py` | Planned | Entity-specific confidence/context validation and overlap handling. |

## Subdirectories

- [recognizers/](recognizers/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
