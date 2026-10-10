# packages/engine/tests/fixtures

Synthetic documents and images with known PII, scans, embedded faces, and expected outputs. Avoid real employee data.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `message.txt` | Planned | Synthetic text with known PII. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |
| `text.pdf` | Planned | Native-text PDF. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |
| `mixed.pdf` | Planned | PDF with native text and scanned/face content on the same page. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |
| `scanned.pdf` | Planned | Image-only scanned document. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |
| `embedded.docx` | Planned | Word document with native text, scans, and faces. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |
| `embedded.pptx` | Planned | Slides containing native text, scans, and faces. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |
| `scan.png` | Existing | Synthetic HELLO image for opt-in real OCR verification; generated locally, no personal data. |
| `generate_scan.py` | Existing | Reproduce scan.png using Pillow and local Arial; normal tests use the checked-in image. |
| `faces.jpg` | Planned | Face-detection example with documented redistribution rights. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |
| `expected.json` | Planned | Expected categories, source locations, actions, and coverage assertions. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](../../../../docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/ivan-george710/PII-Project/issues/1)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
