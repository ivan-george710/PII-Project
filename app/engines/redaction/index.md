# app/engines/redaction

| File | Responsibility |
|---|---|
| `__init__.py` | Public redaction exports. |
| `artifacts.py` | Office XML edits, embedded OCR/face media composition and independent verification. |
| `document.py` | Legacy document redaction adapter. |
| `document_artifacts.py` | Format dispatcher for PDF, Office and image artifact engines. |
| `engine.py` | Replace confirmed and uncertain PII; preserve explicit review warnings and source offsets. |
| `image_artifacts.py` | Standalone PNG/JPEG OCR/face redaction; emits stripped PNG with independent pixel verification. |
| `media_artifacts.py` | Mask mapped embedded OCR blocks and verify serialized image payloads. |
| `models.py` | Redaction records, issues, results and validation errors. |
| `pdf_artifacts.py` | Native or raster PDF artifact creation; destructive removal, labels and saved-content checks. |
| `resolver.py` | Resolve contained overlaps; detection supplies unions for crossing sensitive spans. |
| `tagging.py` | Document-scoped replacement tags. |
| `text.py` | Legacy text redaction adapter. |
| `visual_artifacts.py` | Face transformations/crops and independent serialized-media verification. |
