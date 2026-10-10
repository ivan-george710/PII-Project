# packages/engine/src/pii_guard/extraction

PDF, DOCX, PPTX, and standalone image extraction, including embedded images and scanned pages inside documents. Preserve source locations for redaction.

PDF OCR uses full-page PDFium rendering (including fallback content) with rotated
crop-box coordinates. DOCX traverses reachable text/image parts; PPTX includes
nested text and ancillary parts. Shared image helpers manage temporary resources,
part/relationship references and cropped/rotated picture coordinates. Unsupported
image placements fail explicitly. See ../../../README.md for current limits.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Package marker and relevant public exports. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `pdf.py` | Existing | Extract PDF native text and image/rendered content with page references. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `docx.py` | Existing | Extract Word text, embedded images, and source relationships. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `pptx.py` | Existing | Extract slide text and embedded images with slide/shape references. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `image.py` | Existing | Normalize standalone images and expose image content. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `embedded_images.py` | Existing | Shared embedded-image enumeration and source relationships. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](../../../../../docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/ivan-george710/PII-Project/issues/1)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
