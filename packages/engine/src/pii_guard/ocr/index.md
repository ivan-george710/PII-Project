# packages/engine/src/pii_guard/ocr

OCR on scanned content and embedded images; coordinate mapping back to document pages, slides, and image regions.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Package marker and relevant public exports. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `engine.py` | Planned | Recognize text in scans and image content with confidence and boxes. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `coordinates.py` | Planned | Map OCR pixel regions to page/slide/image coordinates. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](../../../../../docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/anubhav20ch/PII-Project/issues/1)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
