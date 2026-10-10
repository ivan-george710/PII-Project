# packages/engine/src/pii_guard/redaction

Text replacement, image-region and face redaction, and supported PDF/DOCX/PPTX rewriting. Image/PDF renderers accept future enabled face sources; Office face-source binding and face detection remain pending.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Export text, image, PDF and Office redaction helpers and internal rendering results. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `text.py` | Existing | Validate original source identity and enabled targets; deterministically merge overlapping/adjacent spans and replace with [REDACTED], retaining block provenance without changing public findings. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `image.py` | Existing | Validate image-local OCR/future FACE sources, replace pixels, clear fully transparent RGB, bake orientation and encode/validate metadata-free PNG/JPEG rasters with safe warnings. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `pdf.py` | Existing | Strict structure and catalog/font-name validation, original glyph/region mapping, permanent raster/content redaction, Info/XMP removal, fresh garbage-collected saving, reopening and atomic publication with cleanup rollback. Unsupported structures fail closed; no page rasterization or face detection. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `docx.py` | Existing | Strip validated package metadata, permanently rewrite supported paragraph/table runs and inline pictures, preserve original extraction references and publish exclusively; reject unsafe ancillary parts. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `pptx.py` | Existing | Strip validated package metadata, rewrite ordinary slide/notes runs and placed PNG/JPEG pictures with inverse scale mapping, shared-media union, source validation and exclusive publication; reject unsupported transforms/ancillary parts. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `office.py` | Existing | Private OOXML package/relationship checks, stock ancillary allowlist, codepoint-to-run rewriting, permanent shared media replacement and atomic file publication reused by Word/PowerPoint. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `metadata.py` | Existing | Private four-way ancillary classification and fixed warnings; validated Office properties/preview/printer/shape-metadata removal, bounded PDF Info/XMP validation and removal, fresh raster metadata checks. Unsupported content fails closed through existing writers. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](../../../../../docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/ivan-george710/PII-Project/issues/1)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.

## PR 18 integration

Office renderers now accept validated `region_sources` for faces in embedded PNG/JPEG pictures. Multiple faces in a single source image have separate geometry-bound identities. Faces are opaque pixel replacement, not blur.
