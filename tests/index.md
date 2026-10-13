# tests

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `test_audit.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `test_audit_integration.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `test_detector_evaluation.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `test_document_pipeline.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `test_extraction.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `test_file_intelligence.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `test_office_documents.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `test_pdf_artifacts.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `test_pii_detection.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `test_pipeline.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `test_pptx_boundaries.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `test_redaction.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `test_redaction_integration.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `test_review_api.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `test_visual_api.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `test_visual_privacy.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |

Subdirectories contain their own manifests when touched. Engine implementation and phase evidence remain authoritative.

| `test_manager_service.py` | Implemented; verified (7 passed) | Affected-only payload, immutable revision, stale decision, readiness, denial-only downloads, safe transport and manager rule validation tests. |

| `test_mixed_privacy.py` | Implemented | Real OCR and independent returned-artifact OCR checks for mixed PDF, embedded Office images, PNG/JPEG and original short-alias/ID/mail/password regressions. |
