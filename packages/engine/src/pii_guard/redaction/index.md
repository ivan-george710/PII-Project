# packages/engine/src/pii_guard/redaction

Text replacement, image-region and face redaction, and PDF/DOCX/PPTX rewriting to produce sanitized artifacts. Every detected face is redacted when the face rule is enabled.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Package marker and relevant public exports. |
| `text.py` | Planned | Merge spans and replace exact source text without rewriting unrelated content. |
| `image.py` | Planned | Permanently obscure text regions and every enabled-rule detected face. |
| `pdf.py` | Planned | Rewrite sanitized PDF content/images without recoverable overlays. |
| `docx.py` | Planned | Rewrite Word text and replace embedded images; sanitize ancillary content. |
| `pptx.py` | Planned | Rewrite slide text and embedded images; sanitize ancillary content. |
| `metadata.py` | Planned | Inspect/strip unsafe metadata, notes, comments, and unsupported payloads. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
