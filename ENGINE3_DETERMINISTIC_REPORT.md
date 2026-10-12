# Engine 3 deterministic architecture report

Completed on 12 October 2026. The active detection workflow now uses Microsoft Presidio, the existing custom employee-ID recognizer and deterministic validation rules. **Qwen is no longer an active product component.**

## Files changed or removed

| File | Change |
| --- | --- |
| `app/engines/pii_detection/engine.py` | Remove resolver imports, initialization, injection argument, inference and response parsing. Map existing AMBIGUOUS validation directly to final REVIEW. Rename the bounded-context helper for validation. |
| `app/engines/pii_detection/models.py` | Mark optional `llm_decision` and `llm_reason` as deprecated in comments and dataclass metadata; retain their defaults/positions for historical cache and consumer compatibility. |
| `app/engines/redaction/models.py` | Document the existing LLM audit field as deprecated; no behavior or constructor change. |
| `tests/test_pii_detection.py` | Replace resolver-based tests with deterministic REVIEW handling, preserve existing regression/offset/accounting tests, and prove default detection works without the generative package stack. |
| `tests/test_redaction_integration.py` | Remove the fake resolver and use the actual deterministic constructor/interface. |
| `tests/test_redaction.py` | Update the module description; retain historical-metadata compatibility tests. |
| `tools/validate_cadence_document.py` | Remove all Qwen timing/inference machinery and configuration. Reuse trusted extraction, run current deterministic detection/redaction, and write new results separately from historical artifacts. |
| `tools/inspect_cadence_evidence.py` | Update its description to describe source/detection evidence inspection; historical audit fields remain readable. |
| `requirements.txt` | Remove nine direct package entries associated with generative inference or inactive Docling model dependencies. |
| `README.md` | Document the current architecture, API, REVIEW/export semantics, environment requirements and cached diagnostic command. |
| `ENGINE3_DETERMINISTIC_REPORT.md` | This report. |
| `app/engines/pii_detection/local_llm.py` | **Removed.** |
| `tools/verify_qwen_local.py` | **Removed.** |
| `tests/test_local_llm.py` | **Removed.** |
| `test_local_llm.py` | **Removed** obsolete root-level model experiment. |
| `test_engine_llm.py` | **Removed** obsolete root-level resolver experiment. |

Two obsolete project-local compiled bytecode files were also removed: the deleted resolver's `.pyc` and its deleted unit-test module's `.pyc`. Cleanup was confined to verified paths inside this project. Historical reports and sensitive historical validation artifacts were preserved. No global model cache or global Python installation was modified, and no packages were uninstalled from the existing virtual environment.

The unchanged `validation.py` and `recognizers.py` retain their established policy, patterns and classification heuristics. The Engine 4 engine, overlap resolver and tagging implementation also remain byte-for-byte unchanged relative to the real-document validation fingerprints. No new speculative rules were introduced to reduce REVIEW counts.

## Simplified architecture and decisions

```text
ExtractionResult pages
    → Microsoft Presidio + custom recognizers
    → deterministic validation
    → CONFIRM / REJECT / REVIEW
    → Engine 4 redaction
    → Engine 5 audit in a future phase
```

The public call remains:

```python
from app.engines.pii_detection import PIIDetectionEngine

result = PIIDetectionEngine().detect(extraction_result)
```

An already-configured analyzer can still be injected with `analyzer=...` for tests and diagnostics. The former resolver injection argument was removed with the resolver architecture.

| Existing validation outcome | Final decision | Result collection |
| --- | --- | --- |
| CONFIRM | CONFIRM | `detections` |
| REJECT | REJECT | `rejected` |
| AMBIGUOUS | REVIEW | `review` |

AMBIGUOUS remains the existing internal validation enum/metadata value for backward compatibility; its final disposition is always REVIEW. It is never automatically rejected or adjudicated by a model. Existing government/bank/license policy support is retained; identifiers whose rules remain ambiguous now require review.

Every returned Presidio candidate still receives exactly one disposition. Original text, confidence, page-local end-exclusive offsets, recognizer/method, reliable OCR block index, validation decision/reason and final decision remain available. Raw candidate counts, page-analysis identifiers and aggregate diagnostics are unchanged. Empty documents/pages, zero-candidate pages and multiple pages retain their existing behavior. Analyzer/input failures still raise explicit processing errors rather than implying zero PII.

The deterministic engine never populates the deprecated LLM audit fields. They remain optional solely so the existing Engine 4 records and historical JSON caches continue to work. Retaining those fields does not retain any model dependency or inference path.

## Dependency removal and verification

Removed direct requirements:

- `accelerate`
- `torch`
- `transformers`
- `torchvision`
- `tokenizers`
- `safetensors`
- `docling`
- `docling-ibm-models`
- `docling-slim`

The last three were inactive exploratory Docling entries, not dependencies of the active extraction engine. Keeping `docling-ibm-models` would have pulled Torch, Transformers, Torchvision and Safetensors back into a new install. Its inactive parent Docling entries were removed for the same reason. The `scratch_docling.py` experiment therefore no longer has its model-based prerequisites in the primary requirements; no production engine uses it. The existing installed environment was left intact.

Other shared packages were retained rather than performing unrelated dependency cleanup. In particular, Hugging Face Hub/HF-XET remain shared requirements of the retained PaddleX OCR experimentation packages; they are not imported or used by active deterministic detection. Active OCR continues to use RapidOCR/ONNX. Presidio still needs its spaCy English NLP model; removing the generative adjudicator does not remove Presidio's own NLP detection.

A metadata dependency-closure check over all **156 remaining direct requirements**, using applicable non-extra dependencies in this environment, found **none** of Torch, Transformers, Accelerate, Torchvision, Tokenizers or Safetensors reachable. This verifies that merely removing their explicit pins did not leave a mandatory transitive path that reinstalls them. It is not a fresh package-install test on every platform; versions and optional extras selected in other environments can differ.

A fresh-process regression makes Torch, Transformers, Accelerate, Tokenizers and Safetensors unavailable through an import hook before importing the engine. It initializes the default real Presidio analyzer, detects synthetic email/employee identifiers, verifies candidate accounting, and asserts that none of those modules loaded. The test passes. Source scanning also found no Qwen/resolver import or invocation in active app code or diagnostic tools. Package-name strings used by that absence test are not runtime dependencies.

## Engine 4 compatibility

No redaction logic change was necessary. Engine 4 already consumes the explicit review collection and blocks export for unresolved findings.

It continues to:

- Replace confirmed spans using deterministic tags and original offsets.
- Preserve rejected records internally.
- Create blocking issues for REVIEW findings, including review findings that overlap a confirmed redaction.
- Resolve covered/nested overlaps and block unsafe crossing overlaps.
- Preserve internal mappings and decision provenance.
- Keep `safe_for_llm=False` without trustworthy coverage clearance.

Legacy audit-metadata tests remain because historical objects can still contain old LLM decision fields. They exercise compatibility only and perform no inference. Engine 4 was not rewritten.

## Tests

Executed from the project root using the existing virtual environment:

```powershell
.venv/Scripts/python.exe -m pytest tests -q
```

**Final result: 117 passed in 14.01 seconds; zero failures.**

The final suite contains 66 detection tests, 44 redaction tests, two real PDF/Presidio/redaction integration tests and five existing extraction/file-intelligence tests. Obsolete Qwen parsing/protocol and resolver-behavior tests were removed or replaced; the earlier 141-test total represented the old architecture.

Coverage includes confirmed PERSON/employee/email/phone findings, rejected business terminology, ambiguous names and bank/license identifiers becoming REVIEW, empty/zero-candidate pages, multiple pages, exact offsets, candidate conservation, preserved metadata, deterministic repetition, analyzer failure handling, Engine 4 compatibility, blocked REVIEW export, and absence of generative model dependencies.

The first development test run had **116 passes and one failure** caused by one leftover `FakeResolver` reference in the analyzer-initialization test. That obsolete reference was removed; the final complete command above passes. No production rules were changed to make the tests pass.

## Cached real-document diagnostic

Executed:

```powershell
.venv/Scripts/python.exe -u tools/validate_cadence_document.py --cached-extraction
```

**Exit code 0.** The runner discovered the root PDF, verified its SHA-256 against the trusted historical cache, checked that the extraction/file-intelligence implementation fingerprints still match, restored `ExtractionResult`, and ran fresh deterministic Presidio/validation/redaction. It did not reuse historical Qwen-derived detection decisions.

| Measurement | Result |
| --- | ---: |
| Cached pages | 35 |
| Page-text characters | 107,571 |
| OCR blocks | 3,396 |
| OCR rerun | **No** |
| Raw Presidio candidates | **1,418** |
| Confirmed | **578** |
| Rejected | **668** |
| REVIEW | **172** |
| Disposition count | **1,418** |
| Candidate accounting consistent | **True** |
| Deprecated adjudication fields unset | **True** |
| Applied redactions | **577** |
| REVIEW blocking issues | **172** |
| Superseded confirmed overlaps | 1 |
| Unresolved overlaps among confirmed spans | 0 |
| `redaction_complete` | **False** |
| `safe_for_llm` | **False** |
| Text export blocked | **True** |

### Review breakdown

| Entity | Confirmed | Rejected | REVIEW |
| --- | ---: | ---: | ---: |
| PERSON | 157 | 14 | 87 |
| US_BANK_NUMBER | 0 | 0 | 28 |
| US_DRIVER_LICENSE | 0 | 0 | 57 |
| EMAIL_ADDRESS | 140 | 0 | 0 |
| EMPLOYEE_ID | 168 | 0 | 0 |
| PHONE_NUMBER | 109 | 0 | 0 |
| US_SSN | 2 | 0 | 0 |
| US_ITIN | 1 | 0 | 0 |
| MEDICAL_LICENSE | 1 | 0 | 0 |
| DATE_TIME | 0 | 235 | 0 |
| URL | 0 | 356 | 0 |
| LOCATION | 0 | 54 | 0 |
| NRP | 0 | 9 | 0 |
| **Total** | **578** | **668** | **172** |

No candidates were returned for US_PASSPORT, IBAN_CODE or CREDIT_CARD in this diagnostic. Those categories remain in the policy.

The 172 REVIEW findings are exactly the candidates that previously required model adjudication: 87 PERSON, 28 bank and 57 license candidates. The previous experiment split them into 97 model confirmations and 75 model rejections. They now all remain visible for review. This is the intended policy change, not candidate loss.

Measured initialization took **1.06 seconds**, current detection took **4.18 seconds**, redaction took **0.015 seconds**, and the runner took **14.26 seconds** including imports, cache loading and other setup. Generative model loading/inference time is **zero**. These measurements reused OCR; they are not full OCR-plus-detection timing or a controlled performance benchmark against the earlier run.

The cached diagnostic was repeated once after correcting Windows path-separator normalization in the upstream fingerprint check. The final run verifies the historical extraction/file-intelligence fingerprints before reuse. Both runs returned identical dispositions and redaction counts; neither ran OCR or generative inference. The timings above are from the final run.

Historical artifacts under `.private_validation/3f4b5db17d2e2694/` were not overwritten. New detections, redaction review text, manifests and aggregate metrics are stored in the separately inherited access-restricted directory:

`.private_validation/3f4b5db17d2e2694-deterministic/`

The new detection file's ACL was verified to grant inherited FullControl only to the current Windows user and SYSTEM. All sensitive text and mappings stay local and gitignored; terminal diagnostic output contains counts/timings only.

## Known limitations and status

- Removing model adjudication does not repair Presidio discovery misses, OCR-concatenated names, fused identifier boundaries or oversized source spans. The known residual-PII observations in `CADENCE_REAL_DOCUMENT_VALIDATION.md` remain relevant; no new rules were applied here to fix them.
- More findings now explicitly require review. The implemented deterministic validators intentionally do not guess about ambiguous names or numeric identifier categories.
- There is no feedback learning, reviewer approval implementation, rule generator, database or Engine 5 implementation in this change.
- Successful accounting and replacement do not prove full-document recall. No representative labeled ground truth or complete PII-coverage evaluation was supplied.
- The cached diagnostic is a workload-specific review-count measurement. No full-document OCR was rerun and no downstream submission was made.
- Historical result objects still contain sensitive values and possibly legacy model metadata. Deprecated fields must not be interpreted as evidence that the current engine performs model inference.

**The deterministic Engine 3 simplification is implemented and verified. Qwen is removed from the active architecture; Engine 4 compatibility passes. The Cadence document is not cleared for downstream LLM submission.** No global cache deletion, global environment changes, commits or pushes were performed.
