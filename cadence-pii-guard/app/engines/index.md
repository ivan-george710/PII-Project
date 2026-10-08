# cadence-pii-guard/app/engines

Existing modular engine code and placeholders retained for reference.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `DESC.txt` | Existing | Existing engine-folder description. |
| `__init__.py` | Existing | Prototype package exports/marker. |

## Subdirectories

- [audit/](audit/index.md): see its exact file manifest.
- [extraction/](extraction/index.md): see its exact file manifest.
- [file_intelligence/](file_intelligence/index.md): see its exact file manifest.
- [pii_detection/](pii_detection/index.md): see its exact file manifest.
- [redaction/](redaction/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

Reference prototype for [issue 1](../../../docs/issues/01-privacy-engine.md). Production engine implementation belongs in packages/engine; preserve this code as reference.
