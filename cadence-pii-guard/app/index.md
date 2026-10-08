# cadence-pii-guard/app

Existing prototype application modules; main.py is currently an empty entry-point placeholder.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Prototype package exports/marker. |
| `main.py` | Existing | Empty prototype application entry point. |

## Subdirectories

- [config/](config/index.md): see its exact file manifest.
- [engines/](engines/index.md): see its exact file manifest.
- [pipeline/](pipeline/index.md): see its exact file manifest.
- [utils/](utils/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

Reference prototype for [issue 1](../../docs/issues/01-privacy-engine.md). Production engine implementation belongs in packages/engine; preserve this code as reference.
