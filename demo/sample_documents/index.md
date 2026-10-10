# demo/sample_documents

Synthetic PDF, PPTX, DOCX, and image examples containing text PII, scanned content, and embedded faces.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `message.txt` | Implemented | Synthetic text with known PII. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `text.pdf` | Implemented | Native-text PDF. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `mixed.pdf` | Implemented | Synthetic native-text PDF with explicitly documented scan/face placeholders. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `scanned.pdf` | Implemented | Searchable-text placeholder for an unavailable OCR-only scanned PDF. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `embedded.docx` | Implemented | Synthetic Word text document; embedded scan/face fixtures are placeholders. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `embedded.pptx` | Implemented | Synthetic presentation package; embedded scan/face fixtures are placeholders. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `scan.png` | Implemented | Generated grayscale page-like image with a simple geometric illustration, not a face photo. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `faces.jpg` | Deferred | Not distributed: no face image with documented redistribution rights was available. |
| `manifest.json` | Implemented | Demo scenario descriptions, synthetic provenance, and asset permissions. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |
| `messages.json` | Implemented | Fictional text examples for contact details, employee IDs, government/financial IDs, and custom rules in the app sample menu. Owner: [issue 2](../../docs/issues/02-employee-chat.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 2: Deliver employee chat with guarded uploads and LLM responses](../../docs/issues/02-employee-chat.md) — [GitHub #2](https://github.com/ivan-george710/PII-Project/issues/2)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
