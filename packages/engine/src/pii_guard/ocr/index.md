# packages/engine/src/pii_guard/ocr

OCR on scanned content and embedded images; coordinate mapping back to document pages, slides, and image regions.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Package marker and relevant public exports. |
| `engine.py` | Planned | Recognize text in scans and image content with confidence and boxes. |
| `coordinates.py` | Planned | Map OCR pixel regions to page/slide/image coordinates. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
