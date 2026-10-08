# packages/engine/tests

Engine tests covering extraction, OCR, text and face detection, company/custom rules, redaction, and the complete engine pipeline.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `conftest.py` | Planned | Shared engine fixtures and helper configuration. |
| `test_inspection.py` | Planned | MIME validation and mixed-content classification. |
| `test_extraction.py` | Planned | Native and embedded content extraction in every format. |
| `test_ocr.py` | Planned | Scan recognition and coordinate mapping. |
| `test_detection.py` | Planned | Positive/negative text categories and overlaps. |
| `test_faces.py` | Planned | Portrait/group/crop detection, duplicate suppression, and mapping. |
| `test_rules.py` | Planned | Built-in toggles, custom patterns, precedence, and all-on/all-off. |
| `test_redaction.py` | Planned | Sanitized artifact integrity, leak checks, and region coverage. |
| `test_pipeline.py` | Planned | Complete standalone engine processing and failure behavior. |

## Subdirectories

- [fixtures/](fixtures/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
