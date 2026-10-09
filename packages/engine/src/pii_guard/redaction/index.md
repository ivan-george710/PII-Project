# packages/engine/src/pii_guard/redaction

Text replacement, image-region and face redaction, and PDF/DOCX/PPTX rewriting to produce sanitized artifacts. Every detected face is redacted when the face rule is enabled.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Package marker and relevant public exports. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `text.py` | Planned | Merge spans and replace exact source text without rewriting unrelated content. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `image.py` | Planned | Permanently obscure text regions and every enabled-rule detected face. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `pdf.py` | Planned | Rewrite sanitized PDF content/images without recoverable overlays. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `docx.py` | Planned | Rewrite Word text and replace embedded images; sanitize ancillary content. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `pptx.py` | Planned | Rewrite slide text and embedded images; sanitize ancillary content. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `metadata.py` | Planned | Inspect/strip unsafe metadata, notes, comments, and unsupported payloads. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](../../../../../docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/anubhav20ch/PII-Project/issues/1)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
