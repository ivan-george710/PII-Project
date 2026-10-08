# packages/engine/src/pii_guard

Inspection, extraction, OCR, detection, rules, redaction, and audit events. models.py defines engine contracts; pipeline.py provides the main sanitization entry point.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Public engine exports. |
| `models.py` | Planned | Input/output, source locations, findings/actions, policy, and artifact contracts. |
| `pipeline.py` | Planned | Complete inspection-to-sanitization workflow accepting supplied company policy. |
| `errors.py` | Planned | Explicit processing, unsupported-content, and policy errors. |

## Subdirectories

- [audit/](audit/index.md): see its exact file manifest.
- [detection/](detection/index.md): see its exact file manifest.
- [extraction/](extraction/index.md): see its exact file manifest.
- [inspection/](inspection/index.md): see its exact file manifest.
- [ocr/](ocr/index.md): see its exact file manifest.
- [redaction/](redaction/index.md): see its exact file manifest.
- [rules/](rules/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
