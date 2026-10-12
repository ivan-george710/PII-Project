# Engine 5: audit, traceability and human review

Completed on 12 October 2026. **Engine 5 is COMPLETE for this phase's implementation requirements.** The cached Cadence policy remains blocked for downstream submission, and complete PII coverage is not established.

## A. Files created or modified

| File | Responsibility |
| --- | --- |
| `app/engines/audit/__init__.py` (modified placeholder) | Public engine, models, actions and exception exports. |
| `app/engines/audit/models.py` (modified placeholder) | Internal audit records, immutable feedback/events, queue items, audit results and conservative status properties. |
| `app/engines/audit/engine.py` (modified placeholder) | Input verification, stable identities, redaction traceability, feedback replay/conflicts, effective detections, correction regeneration, save/load verification. |
| `app/engines/audit/reporter.py` (modified placeholder) | Allowlisted sanitized summaries; excludes sensitive strings and identifiers. |
| `app/engines/audit/storage.py` (created) | Restricted local JSON snapshots, atomic writes, revision checks and immutable original-baseline protection. |
| `tests/test_audit.py` (created) | 46 synthetic audit, correction, persistence, consistency and security tests. |
| `tests/test_audit_integration.py` (created) | Real synthetic PDF extraction/Presidio/redaction/reviewer-correction integration. |
| `tools/validate_audit_cache.py` (created) | Lightweight audit of the existing complete Cadence caches, with no OCR, new detection or real-document reviewer overrides. |
| `.gitignore` (modified) | Add `/.private_audit/`. |
| `README.md` (modified) | Update Engine 5 architecture/status and document review/persistence APIs and safety limits. |
| `ENGINE5_REPORT.md` (created) | This report. |

Private JSON snapshots and a sanitized diagnostic summary were also generated under `.private_audit/`. All **26 Engine 1–4 Python source files** matched the prior deterministic diagnostic fingerprints. No recognizers, validation rules, model prompts, earlier engine logic or original document files were changed. Historical reports/caches were retained. No commits or pushes were made.

## B. Audit data model

The public entry point is:

```python
from app.engines.audit import AuditEngine

engine = AuditEngine()
audit = engine.create_audit(extraction_result, detection_result, redaction_result)
```

`AuditResult` contains internal snapshots of:

- The original `ExtractionResult`, original `PIIDetectionResult` and original `RedactionResult`.
- The effective corrected detection result and current regenerated redaction result.
- Audit records, review queue, feedback history, aggregate counts and revision number.
- Internal document identity and baseline fingerprint.

Each `AuditRecord` links a document-local detection ID to the **original detection** and **effective detection**, preserving entity, original text, source offsets, page, original confidence, recognizer/method, validation decision/reason, final decision and available OCR block reference. It also records automated/effective decisions separately, extraction method, redaction status/tag, redacted offsets, a covering detection ID for superseded findings and whether a reviewer correction was applied.

Statuses distinguish `APPLIED`, `REJECTED`, `REVIEW_REQUIRED`, `SUPERSEDED`, `UNRESOLVED_OVERLAP` and `VALIDATION_ISSUE`. Confirmed candidates do not automatically count as separate replacements. A superseded record points to the covering tag and its actual replacement offsets, rather than inventing its own replacement.

`ReviewerFeedback` describes a caller-supplied action, reviewer identifier, optional reason/timestamp, detection ID or original source span, and optional expected decision. Immutable `FeedbackEvent` records add an event ID and previous/new effective decisions. Timestamps default to UTC and supplied timestamps must be timezone-aware ISO 8601; they are normalized to UTC.

Aggregate counts retain original automated raw/CONFIRM/REJECT/REVIEW counts separately from effective findings, human additions, applied redactions, superseded findings, unresolved-overlap findings/groups, blocking issues, queue items and feedback events.

The corrected `PIIDetectionResult` is the existing Engine 4 input container. Its candidate count accounts for all effective input findings, including human additions. The authoritative **original raw Presidio count** remains separately preserved in the original detection snapshot and `counts['raw_detection_count']`; manual additions are never reported as new raw Presidio discoveries.

## C. Detection traceability

- IDs `D000001`, `D000002`, etc. are assigned deterministically by original document page order, span and detection metadata. They are document-local and stable for the same extraction/detection inputs.
- IDs `H000001`, etc. identify validated human additions in feedback order. Existing automated IDs do not change when corrections are applied.
- Duplicate raw candidates remain separate records. Matching the Engine 4 mapping/issues consumes individual occurrences, avoiding accidental attribution of every duplicate to one applied span.
- Engine 4's original candidate order is preserved for tie-breaking, even though audit identities are assigned in document order.
- The internal document fingerprint binds the supplied source identity and complete extraction, including page/block structure. It is not a hash of an individual sensitive value and is not included in public summaries. No random UUID is used for finding identity.
- Baseline fingerprints and regenerated-state checks detect inconsistent original snapshots, mutated derived audit state, feedback history corruption and stored traceability mismatches. These are consistency checks, not signed evidence against a malicious filesystem owner.

`create_audit` verifies raw candidate accounting and validates supplied redaction against the existing Engine 4 output. It rejects mismatched or inconsistent inputs rather than creating an audit that could imply clearance. Invalid source spans cannot be repaired by guesswork. Unknown decision metadata that Engine 4 exposes as a blocking issue remains a validation issue in the queue.

## D. Reviewer feedback workflow

```python
from app.engines.audit import ReviewerFeedback

corrected = engine.apply_feedback(audit, ReviewerFeedback(
    action="FALSE_POSITIVE",
    reviewer_id="caller-supplied-reviewer-id",
    detection_id=selected_record.detection_id,
    reason="Reviewer explanation",
))
```

Supported actions:

| Action | Effect |
| --- | --- |
| `CONFIRM_PII` | Set the finding's effective decision to CONFIRM; retain its original automated decision and provenance. |
| `FALSE_POSITIVE` | Set its effective decision to REJECT; retain its original detection/redaction history. |
| `MISSED_PII` | Validate page, integer end-exclusive offsets and entity-label format; slice exact text from the original extraction; add a human-provenance CONFIRM finding. |

MISSED_PII does not accept arbitrary original/replacement text. Its `detection_method` and recognizer identify human review. Confidence is `0.0` as an **uncalibrated sentinel**, not a Presidio or model confidence estimate. A source-block index is added only when complete newline-joined OCR blocks exactly reconstruct the page and the human span is wholly inside one block. No bounding box or source mapping is invented.

Example request:

```python
corrected = engine.apply_feedback(audit, ReviewerFeedback(
    action="MISSED_PII",
    reviewer_id="caller-supplied-reviewer-id",
    page_number=1,
    original_start=validated_start,
    original_end=validated_end,
    entity_type="EMAIL_ADDRESS",
))
```

### Conflict policy

1. The first explicit reviewer decision can override an automated decision.
2. Repeating the same action, target/span, reviewer, reason and expected-decision parameters is idempotent. Retry timestamps do not create duplicate events. Unrelated intervening corrections do not defeat idempotency when the latest decision for that finding is unchanged.
3. A different reviewer decision on an already-corrected finding requires `expected_decision` matching its current effective state. An absent or stale expectation raises `FeedbackConflictError`; it does not silently overwrite history.
4. Another confirmation with a different reason/reviewer can be recorded as a distinct event when it does not contradict the effective decision.
5. An exact missed span/type already represented by an automated finding must be addressed through that finding's ID. Repeated human additions to the same span/type are idempotent; subsequent changes use its `H...` ID.

Feedback and original source/detection objects are copied, not mutated. The caller supplies the reviewer identifier. Engine 5 does not authenticate that identity or decide whether the caller is authorized; that remains the application's responsibility.

The internal review queue is retrieved with `engine.get_review_queue(audit)`. There is one queue item per REVIEW/validation finding, and one grouped item per connected unresolved crossing-overlap issue. An overlap group references all involved detection IDs without creating separate duplicate tasks for the same underlying conflict. Queue identifiers and explanations are stable and contain no original text; authorized callers can dereference IDs into sensitive internal records.

## E. Redaction regeneration

Every correction builds a fresh effective detection result and invokes the existing:

`RedactionEngine().redact(original_extraction, effective_detections)`

Engine 5 does not reverse tags, edit previously redacted strings or copy Engine 4's span replacement logic. FALSE_POSITIVE restores source characters by regeneration; CONFIRM_PII and MISSED_PII receive tags through Engine 4. Reused values, tag numbering, page boundaries, offset validation and overlap decisions remain Engine 4's responsibilities.

Original automated metadata remains in the original record. Corrected effective copies have consistent CONFIRM/REJECT validation/final metadata and explicit reviewer provenance; obsolete model decision fields are cleared only on those copies. No inference mechanism is introduced.

An overlap that remains unresolved after a reviewer confirmation continues to block the document. Completing known review tasks cannot establish discovery of all PII.

The read-only properties `coverage_verified`, `downstream_export_permitted` and `safe_for_llm` remain **False**. There is no approve-document action or setter that enables them. `human_review_complete` means no known unresolved queue items remain; it is not a statement that every page or every detected finding has received human approval.

## F. Persistence and security limitations

```python
path = engine.save_audit(audit)
updated_path = engine.save_audit(corrected, expected_revision=audit.revision)
reloaded = engine.load_audit(audit.document_id)
public_summary = corrected.sanitized_summary()
```

The default directory is `.private_audit/`; a dedicated local path can be supplied to `AuditEngine(storage_dir=...)`. Creation is in-memory; persistence is explicit. No database, ORM, network API or cloud storage is used.

Snapshots include original extraction/detections, original/current redaction data, records, queue, counters and full feedback history. A same-directory temporary file is flushed/fsynced and atomically replaced. Write failures leave the preceding JSON snapshot intact. Saving a changed snapshot requires the expected saved revision; exact unchanged writes are idempotent. A different automated baseline cannot overwrite an existing document's audit history, even with an expected revision: a new detector run requires a separate store/run context.

Loading reconstructs the original inputs, replays every feedback event, regenerates through Engine 4 and checks stored decisions, tags, counters, queue, revision and baseline against that result. Corrupt JSON, stale schema/state, inconsistent events or incompatible stored traceability raise explicit errors. A change in redaction semantics may therefore require a deliberate migration rather than silently rewriting historical traceability.

Security controls:

- Windows storage gets a protected DACL granting FullControl only to the current OS user and SYSTEM. The implementation changes the access-control section only, avoiding a security-audit privilege requirement.
- POSIX storage uses directory mode 0700 and new snapshot mode 0600. POSIX behavior is implemented but was not exercised on this Windows host.
- The default directory is gitignored, and each configured store gets its own `.gitignore` ignoring contents.
- Project/home/filesystem roots, common public/served directory names, symbolic-link/junction traversal and Windows network shares are rejected. Path normalization prevents `..` aliases from bypassing root protections.
- Snapshot IDs are validated and cannot be used for path traversal. Failure messages avoid dumping sensitive input or vendor exception text.
- `sanitized_summary()` exposes only fixed count/status/category fields and conservative flags. It excludes original/redacted document text, document hashes, filenames/paths, tags, finding IDs, reviewer identifiers and free-form reasons. Invalid count types are rejected; unexpected status labels are not echoed.

This is **ACL/permission-restricted plaintext**, not encrypted storage, a signed immutable ledger or a multi-user production database. Sequential revision checks are not a cross-process transaction or locking system. A malicious filesystem owner can alter/delete files or recompute hashes; authentication, authorization, retention, backups and secure deployment remain application/operations concerns. Configurable paths must be genuinely private and not served by an application, even if their directory name is not on the common-name denylist. Git ignore rules cannot prevent deliberate force-adds.

The first persistence test attempts exposed a child-process Windows `SeSecurityPrivilege` error in the initial ACL implementation. Writes failed closed before storing audit payloads. Restricting the ACL operation to DACL access rights fixed the issue; real persistence, atomic-failure recovery and reload tests now pass.

## G. Test results

Executed using the existing virtual environment:

```powershell
.venv/Scripts/python.exe -m pytest tests -q
```

**Final result: 164 passed in 20.46 seconds; zero failures.**

This consists of the 117 existing tests and 47 new Engine 5 cases: 46 unit cases and one real synthetic PDF/Presidio integration case. No Qwen or expensive OCR is loaded in the audit tests. Existing tests verify the deterministic architecture without generative package dependencies.

New cases cover all requested audit/count/traceability, stable-ID, multi-page, CONFIRM/REJECT/REVIEW, superseded/crossing overlap, three feedback actions, invalid page/span/action/reviewer/timestamp, duplicate/conflicting feedback, regeneration, input immutability, multiple corrections, persistence/reload, sanitized summaries, blocked export, empty document and coverage-separation behaviors. Additional checks cover exact duplicate candidate attribution, preserved original overlap winner, corrupted history/traceability, atomic-write failure, stale storage revisions, immutable automated baselines, root/path protections, working-directory-independent identity and inability to manually enable safety.

The initial focused run had **33 passes and four persistence failures** from the ACL privilege issue; the integration-inclusive retry also encountered the same persistence failure. After fixing access-right setup, all **38 then-existing audit/integration cases passed in 13.59 seconds**. Subsequent consistency/security cases were added before the final full-suite command above. Tests were not weakened to bypass real persistence.

### Integration scenarios

A small ReportLab-generated selectable PDF goes through real PDF extraction, real Presidio/deterministic detection, Engine 4 redaction, Engine 5 audit, three reviewer events, regeneration, persistence and reload:

1. **Employee ID:** `EMP-00001` is correctly recognized and confirmed by the reviewer; its tag remains in regenerated text.
2. **Unnecessary PERSON redaction:** the synthetic system label `John Smith` is initially redacted as PERSON. FALSE_POSITIVE restores that label from original extracted text while retaining the original automated decision and feedback history.
3. **Missed email:** `audit@example.invalid` is not recognized as EMAIL_ADDRESS by the existing recognizer in this fixture. MISSED_PII supplies its exact original span; it becomes `[EMAIL_ADDRESS_001]` in regenerated text with human provenance.

All three outcomes and their previous/new decisions are retained; persistence reload reproduces the complete result. The synthetic values above are test fixtures, not values copied from the Cadence document. The integration test never declares complete-document safety.

## H. Cached Cadence document diagnostic

Executed:

```powershell
.venv/Scripts/python.exe tools/validate_audit_cache.py
```

The tool verifies the root PDF against the cached source fingerprint, restores the existing trusted extraction and deterministic detection/redaction objects, creates the complete audit, persists it and reloads it. It does not rerun OCR, Presidio or model inference, and it does not modify real-document detection decisions. It refuses to overwrite a snapshot containing reviewer corrections.

**Exit code 0.** The final recorded diagnostic took **12.041 seconds**, including imports, snapshot validation, local persistence and reload. Earlier diagnostic runs during implementation were repeated only to validate persistence/schema fixes; none reran OCR/detection or applied real-document feedback.

| Measurement | Observed |
| --- | ---: |
| Extracted pages | 35 |
| Original raw candidates | 1,418 |
| Audit records | **1,418** |
| Original/effective confirmed | 578 |
| Original/effective rejected | 668 |
| Original/effective REVIEW | 172 |
| Applied redactions / APPLIED records | **577** |
| Superseded overlap records | 1 |
| Unresolved overlap findings/groups | 0 / 0 |
| Blocking issues | **172** |
| Review queue items | **172** |
| Human additions / feedback events | 0 / 0 |
| All automated candidates accounted for | **True** |
| Persistence reload matches | **True** |
| Original detection result unchanged | **True** |
| `human_review_complete` | **False** |
| `redaction_complete` | **False** |
| `coverage_verified` | **False** |
| `downstream_export_permitted` | **False** |
| `safe_for_llm` | **False** |

These match the previous deterministic comparison values. The counters were measured from the supplied results, not hardcoded assertions. Internal record statuses account for every finding:

`1,418 = 577 APPLIED + 668 REJECTED + 172 REVIEW_REQUIRED + 1 SUPERSEDED`

The original caches remain under `.private_validation/`; the audit snapshot and sanitized diagnostic summary are under `.private_audit/`. Windows ACL inspection confirmed the private directory grants access only to the current OS user and SYSTEM. No original Cadence values or sensitive candidate inventories were printed in diagnostic logs or included in this report.

## I. Known limitations

- The previous policy validation found missed names, email-like strings, telephone-like strings and an SSN-shaped value. Engine 5 does not automatically discover or certify those residuals. It provides validated MISSED_PII corrections when a reviewer supplies source spans.
- Resolving all known REVIEW/overlap issues does not establish full PII recall. No labeled ground truth or comprehensive source review is introduced here.
- Reviewer identity and reasons are caller assertions; there is no authentication, role enforcement, digital signature or independent timestamp attestation.
- IDs are document-local and deterministic for the same inputs, not a cross-version entity-resolution system. New automated baselines need separate store/run contexts to preserve history.
- File-based revision checking supports sequential use, not concurrent multi-user transactions. Atomic replacement protects against torn files but does not make the store a database or append-only ledger.
- New human findings use exact extracted character spans and an uncalibrated confidence sentinel. They cannot correct inaccurate OCR bytes or modify original PDF/DOCX/PPTX content.
- Tags may be renumbered after correction because Engine 4 regenerates deterministically from the effective spans. Original tag information and feedback remain available in the original snapshot/history.
- Known original-to-OCR-block relationships are preserved; cross-block/unreliable mappings remain absent. No spatial visual redaction or frontend review interface was implemented.

## J. Completion status

**Engine 5: COMPLETE for audit creation, traceability, human corrections, Engine 4 regeneration, local persistence/reload and the requested tests.** All 164 relevant tests pass, and all 1,418 cached findings are audited without dropped records or modified real-document decisions.

**The Cadence document is not cleared for downstream LLM submission.** Human-review completion and PII coverage remain separate, conservative statuses. The work adds no model-based detection, automatic rule learning, database, network service, authentication system, frontend or downstream submission mechanism.
