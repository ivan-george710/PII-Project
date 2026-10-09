**Before starting: refer to the [root index.md](../../index.md) and the `index.md` in every directory you touch. Follow their exact filenames, responsibilities, and shared interfaces; update the indexes when files change.**

# Build the complete document and image privacy engine

Status: Approved for implementation and GitHub publication.
Suggested ownership: Engine

Build the privacy engine as one complete package, covering inspection, extraction, detection, rule evaluation, redaction, and structured reporting output.

## Current implementation to preserve (updated 2026-10-09)

- Start from current upstream `ivan-george710/PII-Project:main`, fetch it again before submitting, and merge current main into existing feature branches. Old branch code must not replace newer working features. Review the final diff against current main.
- Authentication is local email/password. WorkOS was removed intentionally: do not restore its SDK, redirects, settings, cookies, mocks, secrets or CI jobs. Preserve Argon2 hashing, database sessions, company/user/assignment models, permissions, logout/revocation, CSRF and account lockout.
- Preserve `POST /api/v1/auth/signup` (201 new isolated company + manager), `POST /api/v1/auth/login` (200), `GET /api/v1/auth/me` (200 session DTO or 401), and `POST /api/v1/auth/logout` (204). Session DTO: `{user:{id,email,display_name,role,organization_id},organization:{id,name},csrf_token}`. Cookie name is `pii-session`; the API resolves roles/company from its database. Signup cannot join an existing company or promote an existing user.
- Email/password inputs are strings with **no email-format/verification or password-strength/length checks**. Email is lowercased. Duplicate email is 409 ACCOUNT_EXISTS. Public email fields use Pydantic `str` / Zod `z.string()`, not EmailStr or email-format validators. Ordinary feature-specific text/file limits still apply.
- Preserve `/login`, `/signup` and `/company/setup`. Product screens use black/white and neutral grayscale only, no icons; simple text labels and controls. Keep the existing auth design. Employee chat remains a plain LLM interface, with attachments and built-in test samples in the composer addon menu.
- Existing migration chain is `0001_company_identity -> 0002_local_auth -> 0003_signup`. Keep those files, revision IDs, models and deployed data. Add a uniquely named feature migration after the current head; reconcile new parallel revisions on integration so there is one head. Never delete/rewrite an applied migration or recreate company/user/session tables.
- CI currently passes build/tests, migration parity, Vercel deployment and live checks. Preserve these checks; do not delete tests, skip jobs or weaken assertions to get green. Main pushes deploy production, other pushes previews; PRs run tests. Reuse VERCEL_TOKEN / VERCEL_ORG_ID / VERCEL_PROJECT_ID and same-origin `/api` routing. No external-auth credentials are needed.
- Only auth/company setup is implemented in the product. Chat, reports/policies and `packages/engine` are still feature work; the prototype is reference code. Never label placeholders, empty namespaces or `NotImplementedError` stubs as delivered integration. Missing production processing must block submissions; fake adapters require explicit development/test opt-in. A present feature with a broken import must fail checks/startup, not silently disappear.
- Before delivery run the existing backend and frontend checks, migration upgrade/parity and the feature's own checks. Verify the actual PR head and resolve conflicts. Update touched indexes and this issue's status to distinguish implemented work from pending work. This is a shared baseline, not a prerequisite issue dependency.

## Scope

Current scheduling: image/face redaction work is paused at the user’s request; preserve the eventual requirements below, but do not resume that work without a new instruction.
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

## Mandatory validation and shared conventions

Use **Pydantic v2** for Python request/response models, engine contracts, stored JSON policies/events, and provider-bound requests. Use **Zod** for frontend forms, REST responses, and streaming event payloads; TypeScript types alone are not runtime validation. Add `apps/web/src/lib/schemas.ts` for Zod schemas. Use FastAPI’s generated OpenAPI and check matching frontend payloads within this feature’s tests.

- Base Python schema: `BaseModel` with `ConfigDict(extra="forbid", validate_assignment=True)`. Use `StrictBool`, `StrictInt`, constrained strings/lists, enums, UUID, and timezone-aware datetime fields. Do not coerce strings such as `"false"` into booleans. Parse legitimate UUID/date strings deliberately at the transport boundary. Do not use `model_construct()` for external data. Use `model_validate`/`model_validate_json` on integrations and `model_dump(mode="json")` for serialization.
- Frontend: strict Zod objects, matching bounds/enums, `.safeParse()` with field feedback for forms, `.parse()`/`.safeParse()` for every API/SSE response. Malformed responses are errors, not a successful operation. Python validation remains authoritative.
- REST prefix `/api/v1`; health stays `/api/health`. Field names use snake_case. IDs are UUID strings; timestamps are RFC3339 UTC (`Z`). Organization and acting-user IDs always come from the validated session, never a client claim.
- JSON error shape: `{"error":{"code":"VALIDATION_ERROR","message":"Invalid request","fields":[{"path":"text","message":"Too long"}],"request_id":"<uuid>"}}`. Never include original PII, secrets, tracebacks, or rejected raw field values. Use 401 unauthenticated, 403 wrong role, 404 unavailable/foreign resource, 409 conflict, 413 limit exceeded, 415 unsupported file, 422 invalid payload, 502 provider error, 503 required component unavailable.
- Pagination: `limit` integer 1..100 (default 25), optional opaque `cursor` max 512 characters; response `{"items":[...],"next_cursor":null}`. Stable descending `created_at,id` ordering; no cross-company cursor reuse.
- Cookie-auth mutations require CSRF validation and an allowed Origin. Frontend sends credentials; do not put bearer/session credentials in localStorage. Validate authorization again on every endpoint and every file access.
- Each issue includes its own migrations, UI/backend/package work, integration adapters, fixtures, and checks. Do not wait for another issue to close. Implement against the contracts below; simulated adapters are explicit development-only substitutes, prohibited in production.
- Official validation reference: [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/), [strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/), [Zod basics](https://zod.dev/basics).

## Engine input/output contract and processing instructions

No public engine HTTP endpoint. Implement `sanitize(request: SanitizeRequest) -> SanitizeResult` in `pipeline.py`. A request is processed completely; do not return clean output if any required step failed.

### Pydantic models in `models.py`

| Model | Exact fields and constraints |
|---|---|
| `CustomRule` | `id: UUID`, `name: str` 1..80 trimmed, `kind: Literal["exact","regex"]`, `pattern: str` 1..512, `case_sensitive: StrictBool`, `enabled: StrictBool` |
| `PolicySnapshot` | `organization_id: UUID`, `version: StrictInt >=1`, `builtins: dict[RuleId,StrictBool]` containing every built-in ID exactly once, `custom_rules: list[CustomRule]` max100; IDs unique |
| `ArtifactInput` | `id: UUID`, `filename: str` 1..255 basename only, `source_path: Path` supplied by trusted storage adapter, `declared_mime: str or null`; actual bytes decide format |
| `SanitizeRequest` | `submission_id: UUID`, `text: str` max100000 Unicode characters, `artifacts: list[ArtifactInput]` max5, `policy: PolicySnapshot`, `output_dir: Path` server-owned; require text.strip() or at least one artifact |
| `SourceLocation` | `artifact_id: UUID or null` (null means message), `kind: Literal["message","native_text","ocr","face"]`, `page_number: positive int or null`, `slide_number: positive int or null`, `source_ref: str or null`, `start/end: nonnegative ints or null`, `bbox: tuple[float,float,float,float] or null`; box is normalized top-left `[x,y,width,height]`, values0..1, within bounds; start/end are page/block-local Unicode codepoint offsets, end exclusive; face requires bbox, text requires span |
| `Finding` | `id: UUID`, `rule_id: str`, `category: str`, `confidence: float`0..1, `recognizer: str`, `location: SourceLocation`, `action: Literal["redacted","allowed_disabled"]`; matched raw text may exist in private processing memory only, not public event serialization |
| `SanitizedArtifact` | `artifact_id: UUID`, `filename: str`, `mime_type: str`, `output_path: Path` under output_dir, `size_bytes: positive int`, `sha256: lowercase hex64`, `format_changed: StrictBool` |
| `SanitizeResult` | `submission_id: UUID`, `policy_version: positive int`, `sanitized_text: str`, `artifacts: list[SanitizedArtifact]`, `findings: list[Finding]`, `warnings: list[str]`; successful result contains every requested artifact once |
| `ProcessingError` | exception carrying `code` enum (`UNSUPPORTED_FILE`, `ENCRYPTED_FILE`, `EXTRACTION_FAILED`, `OCR_FAILED`, `FACE_DETECTION_FAILED`, `REDACTION_FAILED`, `INVALID_POLICY`, `PROCESSING_TIMEOUT`), safe message, submission/artifact ID; no success artifact on failure |

Built-in rule IDs: `PERSON`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `EMPLOYEE_ID`, `US_SSN`, `US_PASSPORT`, `US_DRIVER_LICENSE`, `US_ITIN`, `US_BANK_NUMBER`, `IBAN_CODE`, `CREDIT_CARD`, `MEDICAL_LICENSE`, `FACE`. All enabled for a new company. Custom rule IDs are `custom:<uuid>`. Every supported detector runs even when its rule is disabled so allowed detections can be reported; a disabled detector failure still fails inspection rather than inventing a clean result.

1. Validate models and limits; snapshot policy once. Verify source files exist, are regular files, and come from the storage adapter. Reject encrypted, malformed, unsupported, and >25MiB artifacts; max100 pages/slides each. Limits are configurable with these demo defaults.
2. Inspect content, enumerate native and image content including images on mixed pages, and record stable source references. Render content when needed so faces/text that are not ordinary embedded images are inspected.
3. OCR image content. Map all boxes to original page/image coordinates and retain transforms. Never assume text PDFs contain no image PII.
4. Detect text and faces. Base thresholds: employee ID0.90, email0.70, phone0.70, person0.75, government/financial0.80, face0.50; expose config and document detector-score comparability. Combine context and format validation; record rejected candidates privately for tests. Do not claim thresholds guarantee coverage.
5. Evaluate custom phrases literally (escape regex characters for exact matching). Regex uses a bounded evaluator with a100ms timeout per rule/content unit; timeout is an error. Limit matches to10000 per submission. Case-insensitive comparison must preserve original span positions. Reject empty-string-matching regexes at rule save/preview and engine validation.
6. Preserve one event per accepted rule match, including overlaps. Merge redaction spans/regions for rendering; an enabled redaction takes priority over a disabled overlapping match. Disabled event retains `allowed_disabled`, but may overlap pixels/text removed by another enabled rule.
7. Redact exact text with `[REDACTED]`; permanently remove face/text image regions (opaque coverage preferred; any blur mode must be explicitly tested). Rewrite artifacts and sanitize ancillary content. Unsupported objects are stripped or cause failure; record safe warnings. Do not silently rasterize an entire file without `format_changed`/warnings.
8. Re-open outputs, check known fixture leaks and geometry, publish artifacts only after the whole submission succeeds. Remove partial outputs on failure. Original paths/bytes never reach the LLM interface or manager events.

### Required standalone examples and tests

Provide runnable examples for text-only, each file format, mixed scans/faces, all rules disabled, and a custom rule. Assert exact offsets for Unicode and multiline text, bbox transforms for rotated/scaled content, artifact cardinality, custom timeout, blank pages, invalid policy, and fail-closed behavior. Source dictionaries with unknown keys, boolean strings, invalid enum IDs, missing built-ins, and boxes outside image bounds must fail Pydantic validation.

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
| `demo/adapters/engine.py` | Clearly labeled simulated engine outputs; prohibited for real submissions. |
| `docs/engine-contract.md` | Define content, policy, artifacts, locations, findings, and failures. |
| `docs/spark-reuse.md` | Map Apple/Swift face logic to the backend implementation and test cases. |

## Working independently

Use the documented interfaces and feature-owned development adapters for integration points. Do not wait for another issue to close. Test this workstream against those interfaces, then connect real implementations without changing the contract. Production must never substitute simulated privacy processing.

- Keep all touched directory indexes accurate and distinguish planned files from implemented files.
