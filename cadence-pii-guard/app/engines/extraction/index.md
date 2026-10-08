# cadence-pii-guard/app/engines/extraction

Existing PDF extraction and RapidOCR implementation; DOCX and PPTX files are placeholders.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Prototype package exports/marker. |
| `docx.py` | Existing | Empty Word extraction placeholder. |
| `engine.py` | Existing | Prototype engine implementation or empty placeholder; see current source. |
| `models.py` | Existing | Prototype data contracts; audit models are currently empty. |
| `ocr.py` | Existing | RapidOCR image recognition and PDF rendering/OCR. |
| `pdf.py` | Existing | Native and hybrid PDF extraction. |
| `pptx.py` | Existing | Empty PowerPoint extraction placeholder. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

Reference prototype for [issue 1](../../../../docs/issues/01-privacy-engine.md). Production engine implementation belongs in packages/engine; preserve this code as reference.
