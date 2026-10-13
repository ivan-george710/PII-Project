# app/engines/file_intelligence

| File | Responsibility |
|---|---|
| `__init__.py` | Public classification exports. |
| `detector.py` | Content-based MIME and Office package validation. |
| `engine.py` | Validate/classify actual input and select extraction strategy. |
| `models.py` | File classification metadata. |
| `pdf_analyzer.py` | Classify native/scanned/mixed PDF pages; any mixed page requires OCR. |
