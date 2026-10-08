# cadence-pii-guard

Existing Python prototype retained unchanged as migration reference. Implements file inspection, PDF extraction/OCR, and initial Presidio PII detection; several modules are placeholders. Future production code belongs under apps/ and packages/engine/.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `.env` | Existing | Empty prototype environment file. |
| `.gitignore` | Existing | Empty prototype ignore file. |
| `README.md` | Existing | Empty prototype README; project description is in the root README. |
| `createfile.py` | Existing | Generate the hybrid PDF fixture. |
| `requirements.txt` | Existing | Existing broad dependency snapshot, including platform-specific packages. |
| `run.py` | Existing | Empty prototype runner placeholder. |
| `scratch_docling.py` | Existing | Docling conversion experiment. |
| `scratch_extraction.py` | Existing | Experimental full policy-PDF extraction with Windows path. |
| `scratch_hybrid.py` | Existing | Experimental hybrid fixture extraction with Windows path. |
| `scratch_ocr_pdf.py` | Existing | Experimental full-PDF OCR with Windows path. |
| `scratch_paddle.py` | Existing | PaddleOCR experiment. |
| `scratch_page.png` | Existing | Existing experimental rendered image. |

## Subdirectories

- [app/](app/index.md): see its exact file manifest.
- [tests/](tests/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
