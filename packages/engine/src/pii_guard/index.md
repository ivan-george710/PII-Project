# packages/engine/src/pii_guard

Inspection, extraction, OCR, detection, rules, redaction, and audit events. models.py defines engine contracts; pipeline.py provides the main sanitization entry point.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Public engine exports. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |
| `models.py` | Planned | Input/output, source locations, findings/actions, policy, and artifact contracts. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |
| `pipeline.py` | Planned | Complete inspection-to-sanitization workflow accepting supplied company policy. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |
| `errors.py` | Planned | Explicit processing, unsupported-content, and policy errors. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |

## Subdirectories

- [audit/](audit/index.md): see its exact file manifest.
- [detection/](detection/index.md): see its exact file manifest.
- [extraction/](extraction/index.md): see its exact file manifest.
- [inspection/](inspection/index.md): see its exact file manifest.
- [ocr/](ocr/index.md): see its exact file manifest.
- [redaction/](redaction/index.md): see its exact file manifest.
- [rules/](rules/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Runtime validation

Use Pydantic v2 BaseModel contracts with forbidden extra fields, strict booleans/integers, constrained values, and explicit boundary validation. Follow the exact models/API shapes in docs/issues. Python types and dataclasses alone do not validate external inputs.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](../../../../docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/ivan-george710/PII-Project/issues/1)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
