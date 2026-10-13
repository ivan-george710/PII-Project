# app/engines/extraction

| File | Responsibility |
|---|---|
| `__init__.py` | Public extraction engine exports. |
| `docx.py` | Exact native Word paragraph/run mapping. |
| `engine.py` | Routes PDF, DOCX, PPTX and PNG/JPEG through real extraction; invokes media OCR. |
| `media.py` | Fingerprint and OCR embedded Office raster images as distinct logical segments. |
| `models.py` | Extraction, OCR boxes and source/Office/PDF/media mapping dataclasses. |
| `residual.py` | Scan serialized PDF pixels for known PII; map affected regions to original OCR/crop evidence for bounded repairs. |
| `ocr.py` | Cached RapidOCR text boxes from original embedded pixels; preserves native lines and maps to canonical output geometry. |
| `office.py` | Package hashes, XML mappings and unsupported-content inventory. |
| `pdf.py` | Selects native text versus canonical raster OCR per page, including mixed pages. |
| `pptx.py` | Exact slide/group/table/speaker-note text mapping. |
