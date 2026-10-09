# packages/engine/tests

Engine tests covering extraction, OCR, text and face detection, company/custom rules, redaction, and the complete engine pipeline.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `conftest.py` | Planned | Shared engine fixtures and helper configuration. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_inspection.py` | Planned | MIME validation and mixed-content classification. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_extraction.py` | Planned | Native and embedded content extraction in every format. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_ocr.py` | Planned | Scan recognition and coordinate mapping. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_detection.py` | Planned | Positive/negative text categories and overlaps. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_faces.py` | Planned | Portrait/group/crop detection, duplicate suppression, and mapping. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_rules.py` | Planned | Built-in toggles, custom patterns, precedence, and all-on/all-off. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_redaction.py` | Planned | Sanitized artifact integrity, leak checks, and region coverage. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_pipeline.py` | Planned | Complete standalone engine processing and failure behavior. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |

## Subdirectories

- [fixtures/](fixtures/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](../../../docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/ivan-george710/PII-Project/issues/1)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
