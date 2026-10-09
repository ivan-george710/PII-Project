# demo/sample_documents

Synthetic PDF, PPTX, DOCX, and image examples containing text PII, scanned content, and embedded faces.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `message.txt` | Planned | Synthetic text with known PII. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `text.pdf` | Planned | Native-text PDF. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `mixed.pdf` | Planned | PDF with native text and scanned/face content on the same page. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `scanned.pdf` | Planned | Image-only scanned document. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `embedded.docx` | Planned | Word document with native text, scans, and faces. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `embedded.pptx` | Planned | Slides containing native text, scans, and faces. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `scan.png` | Planned | Synthetic scanned paper image. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `faces.jpg` | Planned | Face-detection example with documented redistribution rights. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `manifest.json` | Planned | Demo scenario descriptions, synthetic provenance, and asset permissions. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `messages.json` | Planned | Fictional text examples for contact details, employee IDs, government/financial IDs, and custom rules in the app sample menu. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/anubhav20ch/PII-Project/issues/2)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
