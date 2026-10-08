# packages/engine/src/pii_guard/extraction

PDF, DOCX, PPTX, and standalone image extraction, including embedded images and scanned pages inside documents. Preserve source locations for redaction.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Package marker and relevant public exports. |
| `pdf.py` | Planned | Extract PDF native text and image/rendered content with page references. |
| `docx.py` | Planned | Extract Word text, embedded images, and source relationships. |
| `pptx.py` | Planned | Extract slide text and embedded images with slide/shape references. |
| `image.py` | Planned | Normalize standalone images and expose image content. |
| `embedded_images.py` | Planned | Shared embedded-image enumeration and source relationships. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
