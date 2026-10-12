# Phase 6 pipeline report

Completed 12 October 2026. One synchronous call processes supported PDFs through Engines 1–5. Corrections regenerate redaction and audit history without repeating extraction or detection. Downstream submission remains blocked.

## A. Architecture and Files Changed

| File | Change |
| --- | --- |
| `app/pipeline/pipeline.py` | Thin orchestrator, lazy reusable engines, stage timing/failure boundaries, feedback and explicit persistence. |
| `app/pipeline/models.py` | Typed internal result, processing statuses, structured failures and sanitized summary. |
| `app/pipeline/__init__.py` | Public exports. |
| `tests/test_document_pipeline.py` | 28 pipeline tests including real native-PDF integration. |
| `README.md` | Usage, state retention, persistence and conservative safety semantics. |
| `PIPELINE_REPORT.md` | This report. |

Flow: input → File Intelligence → Extraction/OCR → deterministic Detection → Redaction → Audit → internal preview/queue/history and sanitized summary. Existing Engines 1–5, recognizers and validators were not edited. No new dependencies, frontend, network service, generative model, commits or pushes.

## B. Public Pipeline API

```python
from app.pipeline import DocumentPipeline
from app.engines.audit import ReviewerFeedback

pipeline = DocumentPipeline()
result = pipeline.process("path/to/document.pdf")
summary = result.sanitized_summary()
if result.failure is None:
    corrected = pipeline.apply_feedback(result, ReviewerFeedback(
        "CONFIRM_PII", "reviewer-id", result.audit_result.records[0].detection_id,
    ))
    saved = pipeline.save_audit(corrected)
    reloaded = pipeline.load_audit(corrected.document_id)
```

Check each returned `failure` before continuing. `save_audit(result, expected_revision=...)` uses Engine 5's existing conflict checks and restricted atomic JSON store. Engine injection is available through keyword arguments `file_intelligence`, `extraction`, `detection`, `redaction`, `audit`; injected engines use the existing engine interfaces. Production defaults contain no cached document counts.

The internal result exposes `source_path`, `document_id`, each `*_result`, `review_queue`, `effective_detection_result`, `internal_preview`, `processing_status`, `coverage_status`, `stage_timings`, `total_runtime`, `failure` and `persisted_path`. Original automated detections remain in `detection_result`; corrections are in the effective audit view.

## C. Processing Stages and Error Handling

| Stage | Contract |
| --- | --- |
| `file_intelligence` | Existing `analyze(path)` returns `FileMetadata`. |
| `extraction` | Existing `extract(metadata.path)` returns `ExtractionResult`. For the default extractor, a small classification adapter supplies the actual preceding metadata through its existing `file_intelligence.analyze()` contract, avoiding another file analysis. |
| `detection` | Existing `detect(extraction_result)` receives extracted pages, never PDF bytes. |
| `redaction` | Existing `redact(extraction_result, detection_result)` validates exact source spans and applies tags. |
| `audit` | Existing `create_audit(extraction_result, detection_result, redaction_result)` verifies and records the supplied results. |

Missing files, unsupported inputs and corrupt PDFs stop at classification. Recognized formats without implemented extraction stop at `extraction` with `UNSUPPORTED_EXTRACTION`. OCR/rendering, detector, invalid-offset, redactor and audit failures stop at their failing stage; later stages do not run. Unexpected engine result types also fail. Missing files use `SOURCE_NOT_FOUND`; other failures use `STAGE_FAILED`. Each failure carries a fixed sanitized message, stage and code. No vendor exception string is copied or printed by the orchestrator. Partial internal results may remain accessible, but the result is marked failed and never safe. Processing failures are not converted into zero detections.

Timings use `perf_counter()` and include default engine initialization. Native extraction does not invoke OCR inference; the current ExtractionEngine constructor still initializes its OCR component. Engines are reused across calls. Engine 5 revalidates/regenerates redaction internally as part of its integrity contract; this time belongs to the audit/feedback stage, not to another detector run.

Feedback and save add their elapsed time to the preceding result's total runtime. Stage timings retain original stages and the latest duration for each subsequent operation; repeated operations overwrite that stage's duration. Total runtime includes all operations on the result branch, not user waiting time. Reload measures only load time.

## D. Review and Feedback Integration

`apply_feedback()` delegates `CONFIRM_PII`, `FALSE_POSITIVE` and `MISSED_PII` to Engine 5. It returns a new pipeline result and refreshes redaction, review queue, effective findings, summary and feedback history. Original extraction and original automated detections remain unchanged. No File Intelligence, OCR or Presidio rerun occurs. Engine 5's idempotency, source-span validation and expected-decision conflict policy remain authoritative.

`process()` and feedback retain state in memory only. Explicit save stores Engine 5's extraction, original detections/redaction, effective redaction, records, queue and feedback snapshot. Reload delegates validation/replay to Engine 5. Original File Intelligence metadata and pipeline timing history are not stored by that audit schema; reloaded results leave metadata absent and report load timing. There is no second store and no automatic persistence.

## E. Status and Safety Semantics

| Field/value | Meaning |
| --- | --- |
| `PROCESSING_FAILED` | A stage or explicit feedback/persistence operation failed. |
| `PROCESSED_REVIEW_REQUIRED` | Successful processing/reload with known unresolved review items. |
| `PROCESSED_NO_KNOWN_REVIEW` | Successful processing/reload with no known queue items. |
| `COVERAGE_UNVERIFIED` | Separate coverage state, always present. |
| `coverage_verified`, `safe_for_llm`, `downstream_export_permitted` | Always false; no enabling API. |

No known review items does not establish PII coverage. Even zero candidates and a technically complete redaction remain blocked for downstream submission. Internal preview is not an LLM-safe payload.

`sanitized_summary()` includes fixed status/failure identifiers, timings and Engine 5's allowlisted counts/status aggregates. It excludes paths, filenames, document/finding identifiers, tags, raw or preview text, entity values, reviewer identities and reasons. Full result access requires application-layer authorization.

## F. File Format Support Matrix

| Format | File Intelligence | End-to-end extraction |
| --- | --- | --- |
| Native-text PDF | Recognized, `text` | Supported; no OCR inference. |
| Scanned PDF | Recognized, `ocr` | Existing RapidOCR/Poppler path supported; lightweight orchestration test mocks OCR. |
| Hybrid PDF | Recognized, `hybrid` | Existing hybrid routing supported; no new real hybrid/OCR accuracy evaluation in this phase. |
| PNG/JPEG | Recognized | Explicit unsupported-extraction failure. |
| DOCX | Recognized | Explicit unsupported-extraction failure. |
| PPTX | Recognized | Explicit unsupported-extraction failure. |
| Other/corrupt input | Rejected or analysis fails | Structured classification failure. |

## G. Test Results

Exact final command:

```powershell
.venv/Scripts/python.exe -m pytest tests -q
```

**192 passed in 22.98s.** This includes 28 new pipeline tests and all 164 pre-existing tests. Coverage includes execution order and actual object routing, native PDF, mocked OCR, missing/unsupported/corrupt input, all five stage failures and invalid result types, downstream stops, invalid offsets, counts, review queues, crossing overlap queue, timings, sanitized summaries, all three feedback actions, preserved originals, no upstream reruns, persistence/reload/failures, status semantics and zero candidates. An initial focused run had one test assertion failure because it counted Engine 5 baseline validation as an upstream rerun; the assertion was corrected to specifically prohibit classification/extraction/detection reruns.

Real integration uses a small generated selectable PDF containing synthetic employee ID `EMP-00001`, person `John Smith`, email `audit@example.com`, and business phrase `Risk Management`. Real Engines 1–5 classify/extract/detect/tag/audit it. Employee, email and person types are confirmed; the business phrase is not confirmed. A false-positive correction restores the fixture name, records one event and preserves original state. OCR inference is explicitly asserted absent. Safety remains false.

Optional cached Cadence diagnostic was executed with this exact command, using the existing audit and trusted source fingerprint:

```powershell
@'
import hashlib, json
from pathlib import Path
from app.pipeline import DocumentPipeline
root = Path.cwd()
metrics_files = list((root / '.private_validation').glob('*-deterministic/deterministic_metrics.json'))
assert len(metrics_files) == 1
metrics = json.loads(metrics_files[0].read_text(encoding='utf-8'))
source = list(root.glob('*.pdf'))
assert len(source) == 1 and hashlib.sha256(source[0].read_bytes()).hexdigest() == metrics['source_sha256']
files = list((root / '.private_audit').glob('audit_*.json'))
assert len(files) == 1
snapshot = json.loads(files[0].read_text(encoding='utf-8'))
assert Path(snapshot['extraction']['source_path']).resolve() == source[0].resolve()
result = DocumentPipeline().load_audit(snapshot['document_id'])
assert result.failure is None
summary = result.sanitized_summary()
assert summary['audit']['counts']['extracted_pages'] == 35
assert summary['audit']['counts']['raw_detection_count'] == 1418
assert summary['audit']['counts']['review'] == 172
assert summary['audit']['counts']['applied_redactions'] == 577
assert not result.safe_for_llm
print(json.dumps(summary, sort_keys=True))
'@ | .venv/Scripts/python.exe -
```

Measured pipeline load: **1.048532 seconds**, total API runtime **1.048550 seconds** (excludes interpreter/import startup and diagnostic source hashing). Result: 35 pages, 1,418 raw candidates, 578 confirmed, 668 rejected, 172 REVIEW/queue items, 577 applied redactions, one superseded overlap, zero unresolved crossing overlap groups. Candidate accounting: 578 + 668 + 172 = 1,418. Processing status review-required; redaction incomplete; coverage unverified; safe/export false. This checks persisted cached state representation and integrity, not a fresh five-stage document run. No OCR, detection, feedback, audit overwrite or new sensitive terminal inventory occurred.

## H. Known Limitations

There is no labeled ground truth or independent coverage verification. The real document's earlier detection limitations remain; this orchestration phase does not measure or improve detection accuracy. Real OCR was not repeated. Existing hybrid routing and OCR dependencies retain their existing limitations. Constructors may load local OCR/NLP resources even when inference is unnecessary.

Processing is synchronous; one pipeline instance is intended for sequential use. There is no concurrency coordination, authentication, upload boundary or production multi-user persistence. Audit snapshots retain plaintext PII under existing restricted local permissions; they are not encrypted. Failure messages intentionally omit vendor details. Authorized callers must inspect internal state locally if further diagnosis is needed. Reload cannot restore metadata that the audit schema never persisted.

## I. Completion Status

**Phase 6 complete.** Technical integration, feedback regeneration, structured failures, explicit persistence and test coverage are implemented. Detection accuracy and verified PII coverage remain separate from integration success. No result is cleared for downstream LLM submission.
