# Engine 3 completion report

Implementation verified on 12 October 2026. This report supersedes the Engine 3 failure observations in the historical `ENGINE4_REPORT.md`; it does not assert complete PII coverage.

## A. Root cause analysis

- **Candidate and page loss:** the disposition/appending block was outside both the page loop and the Presidio candidate loop. Only the last candidate in the document received a disposition. Earlier candidates and pages disappeared from the result. The repaired block now runs once for each candidate on each page.
- **Empty candidate crash:** `decision` and `detection` were referenced when no candidate had assigned them. Reproduced `UnboundLocalError` with a nonempty zero-candidate page. A later empty page could also leave stale candidate/page context. Empty pages are now skipped explicitly; nonempty pages with zero candidates are recorded as successfully analyzed.
- **REVIEW conflated with rejection:** every LLM response other than CONFIRM was appended to `rejected`. REVIEW now has its own collection and final disposition.
- **Missing decision provenance:** validation ran twice per candidate but neither its decision nor its reason was saved. Validation now runs once and populates both fields; LLM decisions/reasons and final decisions are recorded separately from original Presidio confidence.
- **Unsafe LLM parsing:** substring search could accept `NOT CONFIRM`, prose containing several decisions, or other malformed output. Exact whole-word parsing now converts unexpected responses to REVIEW.
- **Conflicting prompt instructions:** the original system requested JSON while the user prompt requested one word. The prompt now consistently requests CONFIRM, REJECT or REVIEW. It adjudicates the stated entity type, rather than assuming all ambiguous candidates are names.
- **Eager loading and logging:** constructing the engine loaded Qwen even when no candidate needed it. Raw model output was printed. Loading is now lazy, cached per resolver instance, local-files-only, and failed loads are not retried for every candidate. Prompt/context/response logging was removed.
- **Validation defects:** two word-like tokens automatically counted as a name, and the original alphabet regex supported a limited character range. General business-word segmentation now catches role/process labels, including concatenated OCR labels. Name validation uses Unicode character properties and preserves unusual names as ambiguous. A joined initial such as `T.Achebe` is spaced only inside validation, with no changes to source text or offsets.
- **Identifier rejection without context:** driver-license/bank candidates were definitively rejected when context keywords were absent. They now remain ambiguous and receive contextual adjudication; missing keywords alone are not sufficient to discard possible identifiers.
- **Employee recognizer default flags:** Presidio's default pattern flags were case-insensitive. Explicit flags now enforce the documented uppercase `EMP-` format without broadening the pattern. Duplicate recognizer construction was removed.
- **Missing failure and block traceability:** analyzer errors and malformed offsets were not represented with a deliberate fail-closed contract, and source blocks were not mapped. Analysis/input failures now raise `DetectionProcessingError`; reliable OCR block references are assigned only when the exact block join reconstructs the page.

Before editing, the existing regression was reproduced with an offline Qwen stand-in: **1 failed**, with only the final phone number returned and expected employee IDs missing. The separate zero-candidate reproduction also failed before editing. Engines 1 and 2 were inspected and left unchanged, including the duplicate extraction model definitions; Engine 3 uses their actual final exported definitions.

## B. Files changed

| File | Purpose |
| --- | --- |
| `app/engines/pii_detection/engine.py` | Correct page/candidate control flow, deterministic ordering, injected test dependencies, bounded context, exact offsets, block traceability, failure handling and accounting. |
| `app/engines/pii_detection/models.py` | Backward-compatible `final_decision`, explicit `review`, raw counts, analyzed-page identifiers, aggregate diagnostics and public processing exception. |
| `app/engines/pii_detection/validation.py` | Explicit 12-category entity policy; general business/OCR-label and Unicode name validation; conservative identifier decisions. |
| `app/engines/pii_detection/recognizers.py` | Preserve employee-ID pattern while enforcing its documented case-sensitive format. |
| `app/engines/pii_detection/local_llm.py` | Lazy offline Qwen loading, deterministic non-thinking inference, category-aware prompt, strict parser and no sensitive default logging. |
| `app/engines/pii_detection/__init__.py` | Export `DetectionProcessingError` alongside the existing engine/models. |
| `app/engines/redaction/engine.py` | Minimal compatibility change: read the explicit review collection and fail closed on final-disposition/collection conflicts. |
| `tests/test_pii_detection.py` | Expand regression and synthetic tests; use a fake resolver rather than loading Qwen in ordinary tests. |
| `tests/test_local_llm.py` | Fake tokenizer/model protocol tests, parsing tests, local-only load assertions, failure caching and inference-setting checks. |
| `tests/test_redaction_integration.py` | Use the supported injected analyzer/resolver interface and assert zero omitted raw candidates. |
| `tools/verify_qwen_local.py` | Explicit offline live smoke diagnostic with three synthetic candidates. |
| `ENGINE3_REPORT.md` | This report. |

No dependencies, Git configuration, databases, frontends or Engine 5 implementation were added. No commits or pushes were made.

## C. Final architecture

```python
from app.engines.pii_detection import PIIDetectionEngine
from app.engines.redaction import RedactionEngine

detection_result = PIIDetectionEngine().detect(extraction_result)
redaction_result = RedactionEngine().redact(extraction_result, detection_result)
```

The default Presidio analyzer is initialized once and registers one employee-ID recognizer. Each nonempty page is analyzed once. Returned candidates are validated for integer, page-local, end-exclusive offsets, valid confidence and recognizer metadata, then ordered by original spans and entity type. Raw candidates, including overlaps and duplicates, are retained; Engine 4 owns overlap resolution.

Each candidate receives exactly one disposition:

1. Deterministic CONFIRM → `detections`.
2. Deterministic REJECT → `rejected`.
3. AMBIGUOUS → local Qwen, whose CONFIRM/REJECT/REVIEW selects `detections`/`rejected`/`review`.
4. Malformed resolver output or any resolver exception → `review`, with a reason and no sensitive exception message.

Every record retains original text, offsets, page, recognizer, detection method and original Presidio confidence. A candidate never receives an LLM-generated probability. The engine checks `disposition_count == raw_candidate_count` before returning. `diagnostics` contains aggregate counts only. Analyzer, candidate or validation failures raise an actionable processing error rather than returning a partially analyzed document.

LLM context contains at most 200 original characters on either side plus the candidate itself. Only ambiguous candidates reach the resolver. Qwen loads the installed `Qwen/Qwen3-1.7B` with `local_files_only=True`, disables thinking in the chat template, uses `do_sample=False` and limits output to 12 tokens. No candidate or context is sent to an external inference service.

OCR mapping is available when joining the supplied block texts with one newline exactly equals the page text. A detection completely contained in one reconstructed block gets that block's index; cross-block or unreconstructable mappings remain `None`. No bounding boxes or normalized-source offsets are invented.

## D. Synthetic examples

| Candidate / context | Validation | Resolver | Final disposition |
| --- | --- | --- | --- |
| `Miriam T. Achebe` in an owner field | CONFIRM | Not called | CONFIRM |
| `EMP-38104` | CONFIRM | Not called | CONFIRM |
| `Policyowner`, `RCSA`, `Risk Management` | REJECT | Not called | REJECT |
| `HeadofEnterpriseRiskFramework` | REJECT | Not called | REJECT |
| `Brightwell` with a review-only test resolver | AMBIGUOUS | REVIEW | REVIEW |
| `Raghavan` with a confirming test resolver | AMBIGUOUS | CONFIRM | CONFIRM |
| A business false positive with a rejecting test resolver | AMBIGUOUS | REJECT | REJECT |
| Any ambiguous candidate with malformed output/unavailable resolver | AMBIGUOUS | REVIEW | REVIEW |

The automated synthetic pipeline fixture contains one confirmed name, one rejected field label and one unresolved surname. Its redacted text is:

```text
Owner: [PERSON_001]
Policyowner
Chair: Brightwell
```

All three raw candidates are accounted for. The confirmed span's original detection remains in the internal tag mapping. The unresolved surname blocks `to_text_payload()`; this is an internal review artifact.

## E. Test results

Commands were run from the project root using the existing virtual environment.

Pre-fix regression reproduction, with a test-process-only offline resolver:

```powershell
.venv/Scripts/python.exe -c "import pytest; import app.engines.pii_detection.engine as module; module.LocalContextResolver = type('OfflineReviewResolver', (), {'classify': lambda self, **kwargs: 'REVIEW'}); raise SystemExit(pytest.main(['tests/test_pii_detection.py', '-q']))"
```

**1 failed, 1 warning in 1.94s** before implementation. The warning concerned pytest assertion rewriting after imports.

Focused Engine 3 check during development:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_pii_detection.py -q
```

**69 passed in 10.43s**, before adding the final real SSN recognizer check.

Final complete Engines 1–4 test suite:

```powershell
.venv/Scripts/python.exe -m pytest tests -q
```

**141 passed in 16.33s; zero failures.** These comprise 70 detection tests, 20 local resolver protocol/parsing tests, 44 redaction tests, two PDF/Presidio/redaction integration tests, and five existing extraction/file-intelligence tests. The pipeline test file remains an empty pre-existing placeholder.

Ordinary pytest runs use fake Qwen resolvers or fake tokenizer/model objects and never load Qwen weights. The original Cadence synthetic regression still uses real Presidio. Additional recognizer tests use the real employee-ID and SSN recognizers. The new tests cover all requested decision branches, candidate conservation, multiple pages, duplicates/overlaps, exact offsets, OCR mapping, bounded context, empty input, analyzer/model failures, deterministic repeated results and Engine 4 export blocking.

Real PDF/Presidio integration command:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_redaction_integration.py -q -s
```

**2 passed in 11.19s.** The full-candidate synthetic diagnostic records **3 raw candidates, 0 omitted, 2 applied redactions, redaction_complete=True, safe_for_llm=False**. Successful replacement of supplied spans is distinguished from full-document coverage. The automated decision-branch pipeline test additionally checks CONFIRM, REJECT and REVIEW together and verifies that unresolved findings prevent export.

## F. Actual Qwen verification

```powershell
.venv/Scripts/python.exe tools/verify_qwen_local.py
```

**Exit code 0; real local inference succeeded.** No mock model was used in this command. Offline environment flags and local-files-only loading were enabled. The existing model loaded in **4.88 seconds** on CPU; installed versions were **PyTorch 2.14.1+cpu** and **Transformers 5.18.0**, with CUDA unavailable. The smoke script bounded CPU parallelism to four threads for this diagnostic only.

| Synthetic candidate | Context | Actual parsed decision | Inference time |
| --- | --- | --- | --- |
| Brightwell | `The committee is chaired by Brightwell.` | CONFIRM | 1.76 s |
| Raghavan | `Prepared by Raghavan, employee EMP-00001.` | CONFIRM | 1.40 s |
| Sorokina | `Sorokina` | CONFIRM | 1.31 s |

The loader reported some parameters offloaded to disk/CPU with meta-device placeholders; generation nevertheless completed successfully. No new model was downloaded. The three calls reused one loaded resolver and deterministic, non-thinking generation.

**Accuracy limitation observed:** Sorokina was confirmed despite having no informative context. This is evidence that the small model can overconfirm uncertain names, not evidence that the decision is correct. The checks establish working local inference only. They do not calibrate confidence, establish accuracy, or prove all CONFIRM/REJECT/REVIEW behaviors on representative real documents. Automated fake-model tests verify parsing and fail-closed behavior independently of model accuracy.

## G. Cadence document diagnostic

No real Cadence policy PDF or trusted saved extraction was found in the accessible project sample/output directories or the corresponding historical project sample/output locations. Those directories contained no usable sample/extraction files. The 35-page real-policy diagnostic therefore **was not run**. No full-document OCR or repeated real-document Qwen run was attempted.

The historical approximate 1,418-candidate figure is not treated as an expected count. For the available small synthetic real-Presidio diagnostic, all returned candidates are accounted for. Successful runs have no analyzer processing failures; analyzer failure tests raise explicitly and return no partial result. A future real-policy diagnostic can compare `raw_candidate_count`, the three disposition counts and processing exceptions using a trusted extraction without repeating OCR.

## H. Known limitations

- Implementation completeness does not establish 100% recall. Presidio can miss names, identifiers, unusual formats and OCR-contaminated spans. No representative labeled evaluation dataset or recall/precision measurement was available.
- The limited business vocabulary/acronym policy can still create false positives or false negatives. Unicode names, uncommon capitalization, concatenation and contamination may require review. Generalizable heuristics reduce known defects but are not a comprehensive identity classifier.
- The employee format intentionally remains uppercase `EMP-` followed by exactly five digits. Whitespace inserted inside that identifier or other undocumented variants are not repaired or broadened.
- Initial-spacing normalization helps adjudicate a returned OCR candidate; it does not discover names that Presidio never returned. Original text/offsets remain unchanged.
- A valid decision word from Qwen can still be wrong. In particular, live inference confirmed a name with no useful context. REVIEW is preserved whenever returned, but a broader labeled evaluation is needed before relying on local model judgments for clearance.
- Context is bounded, so relevant evidence outside the window can be missed. Original Presidio confidence is not an LLM confidence score.
- Source-block mapping is deliberately unavailable for cross-block spans or nonmatching reconstruction. Bounding boxes remain in the original extraction object.
- Qwen initialization and inference can be expensive on CPU. Smoke timings used four threads and three short inputs; they are not throughput guarantees for large OCR documents. Default production thread settings were not changed.
- Engine objects are intended for sequential document processing; concurrent calls sharing a lazy resolver are not a tested service concurrency contract.
- Candidate accounting covers candidates returned by `AnalyzerEngine.analyze`, not all possible PII or every internal recognizer proposal before Presidio filtering.
- Results contain sensitive internal audit information. There is no new external export or LLM submission mechanism.
- Detection/extraction coverage attestation and an extraction fingerprint remain absent. `safe_for_llm` remains false in detection and redaction results, including when zero candidates are returned. Independent coverage review/clearance remains necessary.

## I. Engine 4 compatibility

The original positional `DetectedPII` and four-argument `PIIDetectionResult` constructors remain valid because new fields have defaults. `detections` and `rejected` retain their prior meanings. REVIEW is represented explicitly in `review` rather than duplicated into rejected findings, so every raw candidate counts exactly once.

The only production Engine 4 change is to iterate this optional collection and check an available `final_decision` against collection membership. Legacy metadata/collections still work. Every explicit review finding creates a blocking issue, and conflicting metadata fails closed. All 44 existing redaction tests pass; real PDF integration and the new three-disposition synthetic pipeline also pass. Engine 4's tagging, span replacement, overlap resolver, audit mapping and coverage status were not redesigned.

The failing Engine 3 regression discussed in `ENGINE4_REPORT.md` is now repaired and passes. That earlier report remains a historical account of the preceding task.

## J. Completion status

**Engine 3: COMPLETE for the requested implementation criteria.** Candidate-loop and empty-result defects are fixed; every raw candidate receives one disposition; deterministic validation and lazy local adjudication work; REVIEW is preserved; page-local offsets and reliable block mapping remain accurate; Engine 4 integration works; all 141 relevant tests pass; actual local Qwen inference was performed and its limitations are explicitly recorded.

**Detection coverage and downstream document clearance are not complete or proven.** The real Cadence policy evaluation remains unperformed because its input was unavailable, and no labeled coverage evaluation was supplied. The overall Cadence PII Guard system and Engine 5 are not claimed complete.
