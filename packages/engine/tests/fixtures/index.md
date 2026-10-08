# packages/engine/tests/fixtures

Synthetic documents and images with known PII, scans, embedded faces, and expected outputs. Avoid real employee data.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `message.txt` | Planned | Synthetic text with known PII. |
| `text.pdf` | Planned | Native-text PDF. |
| `mixed.pdf` | Planned | PDF with native text and scanned/face content on the same page. |
| `scanned.pdf` | Planned | Image-only scanned document. |
| `embedded.docx` | Planned | Word document with native text, scans, and faces. |
| `embedded.pptx` | Planned | Slides containing native text, scans, and faces. |
| `scan.png` | Planned | Synthetic scanned paper image. |
| `faces.jpg` | Planned | Face-detection example with documented redistribution rights. |
| `expected.json` | Planned | Expected categories, source locations, actions, and coverage assertions. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
