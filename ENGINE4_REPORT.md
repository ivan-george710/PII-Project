# Engine 4 implementation report

## A. Files created or modified

| File | Responsibility |
| --- | --- |
| `app/engines/redaction/__init__.py` (modified) | Public engine, result, record, issue and exception exports. |
| `app/engines/redaction/engine.py` (modified) | Input validation, legacy decision compatibility, document orchestration and page-local replacement. |
| `app/engines/redaction/models.py` (created) | Dataclass output, sensitive audit records, status properties and allowlisted text payload. |
| `app/engines/redaction/resolver.py` (created) | Span-based overlap resolution and structured superseded/unresolved findings. |
| `app/engines/redaction/tagging.py` (created) | Document-scoped deterministic tags keyed by exact entity type and value. |
| `tests/test_redaction.py` (modified) | 44 synthetic unit cases, including validation and fail-closed decisions. |
| `tests/test_redaction_integration.py` (created) | Two integration checks using PDF extraction, real Presidio and the actual Engine 3 detection method. |
| `ENGINE4_REPORT.md` (created) | Usage, verification, limitations and completion status. |

The empty `text.py` and `document.py` placeholders were left untouched. Engines 1, 2, 3 and 5 were not modified. No commits, pushes or external submissions were made.

## B. Architecture and interface

```python
from app.engines.redaction import RedactionEngine

result = RedactionEngine().redact(extraction_result, pii_detection_result)
```

Engine 4 consumes the existing Engine 2 `ExtractionResult` and Engine 3 `PIIDetectionResult`. It runs locally and returns a `RedactionResult` with source identity, ordered pages, joined `full_text`, applied records, tag mapping, rejected records and issues. `applied_redaction_count` counts applied spans, including repeated values.

The compatibility layer stays inside Engine 4. Engine 3's `detections` and `rejected` collections encode its legacy final decisions when metadata is absent. Explicit metadata takes precedence: REVIEW, unresolved AMBIGUOUS, unsupported decisions, contradictory decisions and collection/metadata conflicts block export. An AMBIGUOUS validation can be resolved by an explicit LLM CONFIRM or REJECT. No validation rules or inference settings were changed.

`redaction_complete` means that supplied findings have no blocking redaction issue; it does not establish detection coverage. `safe_for_llm` is always false with this prototype input contract because it supplies no trustworthy complete-document coverage evidence. `to_text_payload()` omits audit records, mappings, source filenames and paths, and includes `requires_coverage_review=True`. It raises for blocking findings. Its text still requires coverage review before downstream submission.

Never serialize the whole result for an external consumer: records, rejected findings, issues and tag mappings intentionally contain sensitive audit data. Blocked results can also contain unredacted text and are internal review artifacts.

## C. Redaction algorithm

1. Validate source path and filename, unique positive page numbers, page-local integer offsets, exact detected text, entity tag format, confidence and supplied source-block references. Invalid spans raise `RedactionValidationError`; no offset correction is attempted.
2. Interpret final decisions conservatively. Preserve rejected records unchanged and unresolved records as blocking issues.
3. Group overlapping confirmed spans. Select a span covering the entire group. Prefer complete coverage over narrower spans; break equal-coverage ties using entity priority, confidence and stable input order. Preserve every superseded finding. If no candidate covers the whole group, record blocking crossing-overlap issues and leave that group for review.
4. Assign tags in extracted page order, then original character order. Each entity type starts at 001. Exact `(entity_type, original_text)` values reuse tags across pages. Values are never normalized.
5. Replace selected spans right to left on each page. Record original offsets separately from computed redacted offsets. Preserve every character outside selected spans and join pages using Engine 2's existing two-newline convention.

Audit detections are copied to avoid aliasing caller-owned mutable objects. Available source-block indices are validated and retained; no bounding boxes or block-to-span associations are invented. Engine 5 can dereference valid indices against the original extraction object.

## D. Synthetic example

Input:

```text
Owner: Ada Example
Employee ID: EMP-00001
Email: ada@example.com
```

Confirmed page-1 detections use end-exclusive original spans:

| Entity | Value | Span |
| --- | --- | --- |
| PERSON | Ada Example | [7, 18) |
| EMPLOYEE_ID | EMP-00001 | [32, 41) |
| EMAIL_ADDRESS | ada@example.com | [49, 64) |

Result for those supplied confirmations:

```text
Owner: [PERSON_001]
Employee ID: [EMPLOYEE_ID_001]
Email: [EMAIL_ADDRESS_001]
```

The original values and detection provenance remain in internal audit records only. This example assumes all three detections were delivered; it is not a claim that the current Engine 3 detects all three.

## E. Test commands and outcomes

Run from the project root in PowerShell:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_redaction.py -q
```

**44 passed in 41.46s** on the initial run.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_redaction.py tests/test_extraction.py tests/test_file_intelligence.py tests/test_pipeline.py -q
```

**49 passed in 9.59s**. `test_pipeline.py` is an existing empty placeholder and contributes no tests.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_redaction.py tests/test_redaction_integration.py tests/test_extraction.py tests/test_file_intelligence.py tests/test_pipeline.py -q -s
```

**51 passed in 10.89s** on the final run (12.78s on the preceding run). Integration uses real PDF extraction and the installed Presidio/spaCy analyzer. One test limits analyzer output to EMAIL_ADDRESS to verify a successful single-candidate path through the actual Engine 3 method and Engine 4. The other uses full analyzer output: **3 Presidio candidates, 2 omitted by Engine 3, 0 applied redactions, safe_for_llm=False**. A review-only test stand-in replaces Qwen construction; no Qwen model download or inference is performed. These checks validate interoperability and expose detection loss, not complete PII coverage.

Existing Engine 3 regression check, with Qwen replaced only in the test process:

```powershell
.venv/Scripts/python.exe -c "import pytest; import app.engines.pii_detection.engine as module; module.LocalContextResolver = type('OfflineReviewResolver', (), {'classify': lambda self, **kwargs: 'REVIEW'}); raise SystemExit(pytest.main(['tests/test_pii_detection.py', '-q']))"
```

**1 failed, 1 warning in 1.94s**. The expected EMP-38104 detection is missing; only the final phone candidate is returned. That existing test never imports Engine 4. The warning concerns pytest assertion rewriting after imports. The failure arises in the unchanged Engine 3 detection path; its decision/appending block runs outside the candidate loop. An unrestricted Qwen-backed run was not performed.

The initial integration fixture used an `.invalid` email that this recognizer did not detect, causing Engine 3's empty-candidate `UnboundLocalError`. The fixture was corrected to synthetic `example.com`; no production recognizers were changed.

## F. Known limitations

- Engine 3 can omit candidates and fail on pages with no candidates. Its accuracy and multi-page integration defects remain outside this task.
- Detection results lack an extraction fingerprint and coverage attestation. Engine 4 checks source identity and every supplied span, but cannot establish that no PII was missed or that undetected portions of the extraction are unchanged.
- Consequently, downstream LLM submission remains blocked by `safe_for_llm=False`, including documents with zero confirmed detections. Coverage review and a trustworthy upstream clearance contract are future work.
- Unresolved decisions and crossing overlaps require internal review. Other confirmed spans can still be redacted for that review artifact; blocking text is not exportable through `to_text_payload()`.
- OCR source-block indices are preserved only when supplied and valid. Bounding-box traceability requires the original extraction; automatic spatial mapping and original-file visual redaction are not implemented.
- `sample_documents` contains no sample files, so no Cadence sample-policy integration run was possible. No expensive full-document OCR was run.
- Full result serialization includes original PII by design. External consumers must never receive that audit object. Even the allowlisted text payload requires coverage review.

## G. Engine status

**IMPLEMENTED AND VERIFIED FOR SUPPLIED DETECTIONS; NOT MARKED COMPLETE under the requested completion gate.** All 46 new unit/integration cases and five existing extraction/file tests pass. The existing relevant Engine 3 regression test fails, so the requirement that all relevant tests pass is not satisfied. Engine 3 remains unchanged as requested. The overall Cadence PII Guard system is not complete.

## H. Next step for Engine 5

Engine 5 can consume the source identity, applied span records (original and redacted offsets), copied tag-to-detection mappings, confidence and recognizer/method/decision provenance, extraction methods, valid source-block references, rejected records, superseded conflicts and blocking review issues. It should retain these internally and distinguish successful replacement of supplied findings from complete-document privacy clearance. Engine 5 was not implemented here.
