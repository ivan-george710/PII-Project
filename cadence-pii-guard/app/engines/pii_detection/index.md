# cadence-pii-guard/app/engines/pii_detection

Existing Presidio integration, employee ID recognizer, data models, and category allowlist validation.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Prototype package exports/marker. |
| `engine.py` | Existing | Prototype engine implementation or empty placeholder; see current source. |
| `models.py` | Existing | Prototype data contracts; audit models are currently empty. |
| `presidio.py` | Existing | Empty wrapper placeholder; Presidio is called by engine.py. |
| `recognizers.py` | Existing | Cadence EMP-five-digit employee ID recognizer. |
| `validation.py` | Existing | PII category allowlist only; no application confidence/context validation. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

Reference prototype for [issue 1](../../../../docs/issues/01-privacy-engine.md). Production engine implementation belongs in packages/engine; preserve this code as reference.
