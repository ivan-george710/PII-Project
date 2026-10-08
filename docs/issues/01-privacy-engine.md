**Before starting: refer to the [root index.md](../../index.md) and the `index.md` in every directory you touch. Follow their exact filenames, responsibilities, and shared interfaces; update the indexes when files change.**

# Build the complete document and image privacy engine

Status: Draft — awaiting individual approval before GitHub creation.
Suggested ownership: Engine

Build the privacy engine as one complete package, covering inspection, extraction, detection, rule evaluation, redaction, and structured reporting output.

## Scope
- Package reusable prototype code under packages/engine; migrate it without retaining competing production implementations.
- Process message text, PDF, DOCX, PPTX, PNG, and JPEG.
- Extract native text, scanned pages, and embedded images, including native text and image text on the same page/slide.
- Run OCR and preserve source locations and coordinate transforms.
- Implement Presidio-based text detection, employee IDs, confidence/context validation, and overlap handling.
- Adapt Spark’s whole-image/crop face detection strategy, duplicate suppression, coordinates, and padding to a backend-compatible detector. Redact every detected face when enabled; omit the subject/bystander classifier.
- Evaluate supplied company policies, built-in toggles, and custom exact-phrase/regex rules. Bound regex execution and report invalid policies clearly.
- Produce sanitized text and rewritten documents/images with originals removed, rather than removable visual overlays.
- Address metadata, notes, comments, hidden content, and embedded payloads by sanitizing, stripping, or blocking unsupported content.
- Return findings/actions with rule IDs, policy version, category, confidence, source locations, and redacted/allowed status. Disabled-rule matches remain reportable.
- Provide a stable package entry point, sample policy, synthetic fixtures, usage guide, and model acquisition/license documentation.

## Acceptance criteria
- The package runs independently with supplied input and policy; no API or database is needed.
- Tests cover every input format, mixed pages, embedded scans, embedded faces, positive/negative PII examples, overlaps, and custom rules.
- Exported artifacts open successfully; enabled-rule fixture values do not remain in extractable text or relevant package content.
- Visual checks confirm correct text-region and face coverage in output images/documents.
- Disabled rules allow matching content and record the action; all-on/all-off behavior is covered.
- Processing errors and unsupported inputs are explicit and distinguishable from clean content.
- Detection coverage, document fidelity, supported languages/formats, and known limitations are documented.

## Exact file ownership

Implement the following file plan. Shared directories assign individual files to their workstream; the directory indexes contain responsibilities and current/planned status. Existing prototype files remain reference material, not a second production implementation.

| File | Responsibility |
|---|---|
| `packages/engine/pyproject.toml` | Installable engine dependencies, supported Python version, and test configuration. |
| `packages/engine/README.md` | Standalone usage, supported inputs, policy examples, and limitations. |
| `packages/engine/model_assets/manifest.json` | Model identifiers, versions, licenses, checksums, and download locations. |
| `packages/engine/model_assets/README.md` | Acquisition/cache instructions; model weights remain outside Git. |
| `packages/engine/src/pii_guard/__init__.py` | Public engine exports. |
| `packages/engine/src/pii_guard/models.py` | Input/output, source locations, findings/actions, policy, and artifact contracts. |
| `packages/engine/src/pii_guard/pipeline.py` | Complete inspection-to-sanitization workflow accepting supplied company policy. |
| `packages/engine/src/pii_guard/errors.py` | Explicit processing, unsupported-content, and policy errors. |
| `packages/engine/src/pii_guard/audit/__init__.py` | Package marker and relevant public exports. |
| `packages/engine/src/pii_guard/audit/events.py` | Produce source-linked detection/action events without user/database coupling. |
| `packages/engine/src/pii_guard/detection/__init__.py` | Package marker and relevant public exports. |
| `packages/engine/src/pii_guard/detection/text.py` | Run Presidio and custom recognizers on extracted text. |
| `packages/engine/src/pii_guard/detection/faces.py` | Backend-compatible whole-image/crop face detection and duplicate suppression. |
| `packages/engine/src/pii_guard/detection/validation.py` | Entity-specific confidence/context validation and overlap handling. |
| `packages/engine/src/pii_guard/detection/recognizers/__init__.py` | Package marker and relevant public exports. |
| `packages/engine/src/pii_guard/detection/recognizers/employee_id.py` | Recognize Cadence employee identifier patterns. |
| `packages/engine/src/pii_guard/extraction/__init__.py` | Package marker and relevant public exports. |
| `packages/engine/src/pii_guard/extraction/pdf.py` | Extract PDF native text and image/rendered content with page references. |
| `packages/engine/src/pii_guard/extraction/docx.py` | Extract Word text, embedded images, and source relationships. |
| `packages/engine/src/pii_guard/extraction/pptx.py` | Extract slide text and embedded images with slide/shape references. |
| `packages/engine/src/pii_guard/extraction/image.py` | Normalize standalone images and expose image content. |
| `packages/engine/src/pii_guard/extraction/embedded_images.py` | Shared embedded-image enumeration and source relationships. |
| `packages/engine/src/pii_guard/inspection/__init__.py` | Package marker and relevant public exports. |
| `packages/engine/src/pii_guard/inspection/file_type.py` | Detect real file format and reject unsupported inputs. |
| `packages/engine/src/pii_guard/inspection/pdf_analysis.py` | Classify native text, scans, mixed content, and blank PDF pages. |
| `packages/engine/src/pii_guard/ocr/__init__.py` | Package marker and relevant public exports. |
| `packages/engine/src/pii_guard/ocr/engine.py` | Recognize text in scans and image content with confidence and boxes. |
| `packages/engine/src/pii_guard/ocr/coordinates.py` | Map OCR pixel regions to page/slide/image coordinates. |
| `packages/engine/src/pii_guard/redaction/__init__.py` | Package marker and relevant public exports. |
| `packages/engine/src/pii_guard/redaction/text.py` | Merge spans and replace exact source text without rewriting unrelated content. |
| `packages/engine/src/pii_guard/redaction/image.py` | Permanently obscure text regions and every enabled-rule detected face. |
| `packages/engine/src/pii_guard/redaction/pdf.py` | Rewrite sanitized PDF content/images without recoverable overlays. |
| `packages/engine/src/pii_guard/redaction/docx.py` | Rewrite Word text and replace embedded images; sanitize ancillary content. |
| `packages/engine/src/pii_guard/redaction/pptx.py` | Rewrite slide text and embedded images; sanitize ancillary content. |
| `packages/engine/src/pii_guard/redaction/metadata.py` | Inspect/strip unsafe metadata, notes, comments, and unsupported payloads. |
| `packages/engine/src/pii_guard/rules/__init__.py` | Package marker and relevant public exports. |
| `packages/engine/src/pii_guard/rules/builtins.py` | Define built-in categories and rule IDs, including faces. |
| `packages/engine/src/pii_guard/rules/custom.py` | Validate and evaluate bounded phrase/regex rules. |
| `packages/engine/src/pii_guard/rules/policy.py` | Resolve supplied enabled states, precedence, and versioned actions. |
| `packages/engine/tests/conftest.py` | Shared engine fixtures and helper configuration. |
| `packages/engine/tests/test_inspection.py` | MIME validation and mixed-content classification. |
| `packages/engine/tests/test_extraction.py` | Native and embedded content extraction in every format. |
| `packages/engine/tests/test_ocr.py` | Scan recognition and coordinate mapping. |
| `packages/engine/tests/test_detection.py` | Positive/negative text categories and overlaps. |
| `packages/engine/tests/test_faces.py` | Portrait/group/crop detection, duplicate suppression, and mapping. |
| `packages/engine/tests/test_rules.py` | Built-in toggles, custom patterns, precedence, and all-on/all-off. |
| `packages/engine/tests/test_redaction.py` | Sanitized artifact integrity, leak checks, and region coverage. |
| `packages/engine/tests/test_pipeline.py` | Complete standalone engine processing and failure behavior. |
| `packages/engine/tests/fixtures/message.txt` | Synthetic text with known PII. |
| `packages/engine/tests/fixtures/text.pdf` | Native-text PDF. |
| `packages/engine/tests/fixtures/mixed.pdf` | PDF with native text and scanned/face content on the same page. |
| `packages/engine/tests/fixtures/scanned.pdf` | Image-only scanned document. |
| `packages/engine/tests/fixtures/embedded.docx` | Word document with native text, scans, and faces. |
| `packages/engine/tests/fixtures/embedded.pptx` | Slides containing native text, scans, and faces. |
| `packages/engine/tests/fixtures/scan.png` | Synthetic scanned paper image. |
| `packages/engine/tests/fixtures/faces.jpg` | Face-detection example with documented redistribution rights. |
| `packages/engine/tests/fixtures/expected.json` | Expected categories, source locations, actions, and coverage assertions. |

## Working independently

Use the shared contract snapshots and development adapters for integration points. Do not wait for another issue to close. Test this workstream against those interfaces, then connect real implementations without changing the contract. Production must never substitute simulated privacy processing.

- Keep all touched directory indexes accurate and distinguish planned files from implemented files.
