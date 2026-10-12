# Cadence real-document validation

Validated on 12 October 2026 using the project's existing virtual environment.

**Assessment: Engines 1–4 completed the technical pipeline on all 35 pages, and Engine 4 correctly blocked export. The result is NOT ready for downstream LLM submission.** There are three unresolved PERSON/PHONE overlap groups and independently identified residual names, email-like strings, telephone-like strings and an SSN-shaped value. Candidate conservation and correct replacement do not establish complete PII detection.

## Source and evaluation controls

The PDF was discovered with a root-directory glob, rather than a hardcoded input filename. The sole root PDF was:

`Cadence_Group_Risk_Management_Policy__v6.0.pdf`

- Size: **14,094,994 bytes**.
- SHA-256: `3f4b5db17d2e2694630fe4244754a270d4c0dde68ef009ee0495e43a2bf606f3`.
- File Intelligence: PDF, `application/pdf`, **35 image-only pages**, zero text/mixed/blank pages, `requires_ocr=True`, **strategy `ocr`**.
- Engines used: existing `FileIntelligenceEngine`, `ExtractionEngine`, `PIIDetectionEngine` and `RedactionEngine`.
- All **31 engine Python source files** matched their pre-run SHA-256 fingerprints afterward. No detection rules, recognizers, validation logic, model prompts or engine code were changed during this task.
- Instrumentation only wrapped existing OCR, analyzer, resolver and generation calls to checkpoint results and measure elapsed time. Production decisions and generation arguments were retained.
- Qwen ran locally and offline on CPU, with one model load. Four CPU threads were selected for this diagnostic process through PyTorch/OMP/MKL resource settings; prompts, thinking mode, sampling settings and output-token limit were unchanged.

## Extraction and OCR

| Measurement | Result |
| --- | ---: |
| PDF pages | 35 |
| Extracted pages | 35 |
| Sum of page-text characters | 107,571 |
| `ExtractionResult.full_text` characters | 107,639 |
| OCR blocks | 3,396 |
| Missing extracted pages | 0 |
| Empty extracted pages | 0 |
| Final-pass page/render/OCR errors | 0 |
| Initial operational interruption | 1 console-encoding error |
| OCR block confidence mean | 0.8684 |
| OCR block confidence minimum | 0.5011 |
| Blocks with OCR confidence below 0.8 | 401 |

The 68-character difference between the page sum and full text is the existing two-newline separator across 34 page boundaries. All pages used the implemented RapidOCR path at its default **150 DPI**. OCR confidence is an OCR signal, not a calibrated measure of extraction accuracy or PII coverage.

The initial process successfully OCR'd and checkpointed page 1, then hit `UnicodeEncodeError` while the unchanged extractor printed its checkmark to a non-UTF-8 console. The diagnostic runner was adjusted to use UTF-8 output and reuse completed page checkpoints. The resumed extraction reused page 1 and OCR'd the remaining 34 pages. **Each page underwent OCR once; completed OCR was not repeated.** The first page was rendered again for the resumed extractor, but its cached blocks were reused.

There were no lost pages or empty OCR results in the completed extraction. That does not prove all source text was accurately recognized: name concatenation, line breaks, fused labels, initials and identifiers require additional source-ground-truth checking.

## Engine 3: candidate dispositions

| Measurement | Result |
| --- | ---: |
| Pages analyzed | 35 |
| Raw candidates returned by Presidio | 1,418 |
| Confirmed | 675 |
| Rejected | 743 |
| REVIEW | 0 |
| Sum of final dispositions | 1,418 |
| Candidate accounting consistent | **True** |
| Analyzer processing failures | 0 |
| Local Qwen escalations | 172 |
| Model load attempts | 1 |
| Model/inference exceptions | 0 |

Pages **11 and 16** returned zero raw candidates and were processed successfully. They were not omitted or treated as failed analysis. The observed 1,418 total matches the historical approximate count supplied for this policy, but matching that number is not evidence of detection accuracy or complete recall.

“Raw candidates” means results returned by `AnalyzerEngine.analyze`, after Presidio's own internal processing. It is not a count of all possible source PII or every internal recognizer proposal.

### Breakdown by entity type

Zeros are shown explicitly, including policy entities for which no candidate was returned.

| Entity | Raw | Confirmed | Rejected | REVIEW | Applied redactions |
| --- | ---: | ---: | ---: | ---: | ---: |
| PERSON | 258 | 215 | 43 | 0 | 212 |
| EMPLOYEE_ID | 168 | 168 | 0 | 0 | 166 |
| EMAIL_ADDRESS | 140 | 140 | 0 | 0 | 140 |
| PHONE_NUMBER | 109 | 109 | 0 | 0 | 106 |
| US_SSN | 2 | 2 | 0 | 0 | 2 |
| US_PASSPORT | 0 | 0 | 0 | 0 | 0 |
| US_DRIVER_LICENSE | 57 | 19 | 38 | 0 | 7 |
| US_ITIN | 1 | 1 | 0 | 0 | 0 |
| US_BANK_NUMBER | 28 | 20 | 8 | 0 | 3 |
| IBAN_CODE | 0 | 0 | 0 | 0 | 0 |
| CREDIT_CARD | 0 | 0 | 0 | 0 | 0 |
| MEDICAL_LICENSE | 1 | 1 | 0 | 0 | 1 |
| DATE_TIME | 235 | 0 | 235 | 0 | 0 |
| URL | 356 | 0 | 356 | 0 | 0 |
| LOCATION | 54 | 0 | 54 | 0 | 0 |
| NRP | 9 | 0 | 9 | 0 | 0 |
| **Total** | **1,418** | **675** | **743** | **0** | **637** |

Applied counts can be lower than confirmed counts because a covering span supersedes a contained candidate, or because a crossing overlap is blocked. The table is a disposition/replacement accounting table, not a labeled precision/recall evaluation.

### Actual Qwen outcomes

| Escalated entity | Calls | CONFIRM | REJECT | REVIEW |
| --- | ---: | ---: | ---: | ---: |
| PERSON | 87 | 58 | 29 | 0 |
| US_BANK_NUMBER | 28 | 20 | 8 | 0 |
| US_DRIVER_LICENSE | 57 | 19 | 38 | 0 |
| **Total** | **172** | **97** | **75** | **0** |

The other 578 confirmations and 668 rejections were determined without Qwen. All observed resolver outcomes were CONFIRM or REJECT; a zero REVIEW count must not be interpreted as absence of uncertainty, false positives or missed PII. No model-generated confidence probabilities were used. Original Presidio scores were retained.

## Measured performance

These are `perf_counter()` elapsed measurements, not estimates.

| Operation | Seconds |
| --- | ---: |
| File Intelligence, final runner attempt | 0.04 |
| Resumed extraction/OCR, including initialization and cached page 1 | 211.97 |
| Presidio engine initialization | 1.66 |
| Total Engine 3 detection | 769.52 |
| Presidio analysis calls within detection | 4.70 |
| Qwen model load | 5.50 |
| Actual Qwen `model.generate` time, all 172 calls | **758.76** |
| Resolver classify time, including load | 764.59 |
| Resolver classify time, excluding load | 759.09 |
| Engine 4 redaction and internal serialization | 0.04 |
| Successful primary runner process, including imports and initial diagnostic checks | **993.71** |
| Initial failed process before console fix | 44.26 |
| Cumulative active primary-process runtime across both attempts | **1,037.97** |

The successful process took approximately **16 minutes 34 seconds**; both primary attempts together took approximately **17 minutes 18 seconds**. The total includes imports and checkpoint I/O. It excludes tool/chat idle time and the later lightweight independent inspection and redaction replay. Nested timing rows must not be added together: generation is included in classification, and classification is included in detection.

Per-call resolver wall time ranged from **3.04 to 18.76 seconds**, including the first call's model loading. The loader reported CPU/disk offloading and meta-device placeholders; all calls nevertheless completed. This was a real installed `Qwen/Qwen3-1.7B` run, not mocked inference.

Runtime packages: Presidio Analyzer 2.2.364, RapidOCR ONNX Runtime 1.2.3, ONNX Runtime 1.30.0, Transformers 5.18.0, PyTorch 2.14.1, spaCy 3.8.16, pypdf 6.19.0 and pdf2image 1.17.0.

## Engine 4 and unresolved spans

- Applied spans: **637**, using **240 unique deterministic tags**.
- All **637 redacted-position checks passed**: each recorded redacted span contains its assigned tag.
- **621** applied records have reliable OCR source-block indices; **16** do not. No missing block mapping was invented.
- Superseded overlap records: **32**. These comprise 2 EMPLOYEE_ID, 17 US_BANK_NUMBER, 12 US_DRIVER_LICENSE and 1 US_ITIN candidate.
- Blocking unresolved overlap records: **6**, forming **three crossing-overlap groups**.
- Explicit review-decision records: **0**.
- `redaction_complete`: **False**.
- `safe_for_llm`: **False**.
- Calling `to_text_payload()` raises the expected blocking `RedactionValidationError`.

Candidate accounting for confirmed findings is exact:

`675 confirmed = 637 applied + 32 superseded + 6 unresolved`

The three blocking groups involve a PERSON span that absorbs a line break and the start of a telephone number, overlapping a PHONE_NUMBER span that extends beyond it. Neither span covers the entire group, so Engine 4 leaves the group for internal review rather than independently replacing crossing spans.

| Page | PERSON original span, end-exclusive | PHONE_NUMBER original span | Sanitized conflict |
| --- | --- | --- | --- |
| 12 | [2215, 2233) | [2231, 2248) | Name + newline + `+<digit>` crosses the full phone span |
| 31 | [651, 669) | [666, 681) | Name + newline + country prefix crosses the full phone span |
| 32 | [1283, 1302) | [1300, 1317) | Name + newline + `+<digit>` crosses the full phone span |

A replay using only cached extraction/detection objects produced exactly the same redacted full text and the same 637 applied records. It required no OCR, Presidio analysis or Qwen inference. The blocked redacted text is an **internal review artifact**, not an LLM-safe export.

## Representative sanitized inspections

No original names, employee values, mailbox addresses, telephone numbers or government identifiers are included here. `X`/`x` denote uppercase/lowercase letters and `0` denotes a digit; punctuation and token structure are preserved for diagnosis. Offsets refer to the original extracted page text.

| Category / example | Observed behavior |
| --- | --- |
| PERSON, page 2 [1209, 1224), shape `Xxxxxx X.Xxxxxx` | CONFIRM by deterministic name structure, Presidio confidence 0.85, source block 74; redacted. |
| PERSON, page 1 owner field [104, 118), shape `XxxxxxX.Xxxxxx` | OCR concatenation; no covering PERSON candidate. Overlapping URL/NRP findings were rejected. The name remains. |
| PERSON, page 1 author field [160, 175), shape `XxxxxxXxxxxxxxx` | OCR concatenation; no overlapping final detection record. The name remains. |
| PERSON, page 23 name variant [3312, 3328) | The containing PERSON candidate [3312, 3343) absorbs a name plus the next line. Validation escalates it; Qwen REJECTs the whole span. The known name variant remains. |
| EMPLOYEE_ID, page 1 [142, 151), shape `XXX-00000` | CONFIRM by documented format, confidence 0.95, source block 5. All 168 exact source occurrences were covered, including two superseded by larger applied spans. |
| EMAIL_ADDRESS, page 1 [217, 242), shape `x.xxxxxxxxx@xxxxxxxxx.xxx` | CONFIRM, confidence 1.0, source block 6; redacted. |
| Email-like residual, page 18 [1912, 1940), shape `x.xxxxxxxxxxxx@xxxxxxxxx.xxx` | Independent pattern found it; only a rejected URL record overlaps. No applied span covers it. |
| PHONE_NUMBER, page 1 [463, 480), shape `+0 (000) 000-0000` | CONFIRM, confidence 0.4, source block 9; redacted. |
| Phone-like residual, page 7 [615, 632), shape `+0 (000)` + newline + `000-0000` | Independent pattern found a line-broken number with no overlapping disposition. It remains. |
| US_BANK_NUMBER, page 3 [3470, 3480), ten digits | Raw confidence 0.05; deterministic validation records missing supporting context, then Qwen CONFIRMs. Inspect as a possible category false positive; other overlapping entity evidence may explain the number. |
| US_DRIVER_LICENSE, page 2 [2101, 2103), shape `x0` | Two-character candidate, raw confidence 0.3, no supporting license context found, Qwen CONFIRM. Suspicious possible false positive; not treated as verified personal identification. |
| MEDICAL_LICENSE, page 22 [3425, 3434), shape `XX0000000` | CONFIRM, confidence 1.0; source context contains SSN/passport cues. Category accuracy needs source review rather than assuming the recognizer label is correct. |
| SSN-shaped residual, page 22 [3375, 3386), shape `000-00-0000` | No covering detection or applied span. Context contains SSN/passport cues; the installed SSN invalidation check does not invalidate the value. It immediately follows a letter, consistent with an OCR word-boundary discovery gap. |

No candidates were returned for US_PASSPORT, IBAN_CODE or CREDIT_CARD. Their absence is not proof that the source contains none; there is no labeled source inventory with which to verify those categories.

## Separate residual-PII checks

After the unchanged production evaluation, a separate diagnostic screened the cached source and redacted text. It used independent identifier regexes and two policy-owner/author name-field anchors, allowing whitespace/initial-dot variants only for diagnostic matching. Exact source spans were retained. These probes did not add production candidates, change dispositions or fix redactions.

| Diagnostic | Original matches | Not fully covered by applied spans | Matches remaining in redacted text |
| --- | ---: | ---: | ---: |
| Exact documented EMPLOYEE_ID | 168 | 0 | 0 |
| EMPLOYEE_ID whitespace/case diagnostic variants | 168 | 0 | 0 |
| Email-like pattern | 150 | 11 | **10** |
| Broader telephone-shaped pattern | 72 | 10 | **8** |
| SSN-shaped pattern | 2 | 1 | **1** |
| IBAN-shaped pattern | 0 | 0 | 0 |

The employee variant probe found the same occurrences as the exact probe; do not sum those rows. The email probe's 11 incomplete original matches include one otherwise-redacted address with only a leading punctuation character left, so that case is not an intact leaked email. Partial phone-prefix residuals similarly explain why incomplete-source-span counts can exceed complete residual-pattern counts. Patterns are heuristic and have finite format coverage; an email-like match is not proof of mailbox validity, and these counts must not be presented as recall.

The name-field diagnostic found **two explicit labeled name fields**, both uncovered on page 1. Matching those two anchors with bounded diagnostic spacing/initial variants found **43 source occurrences, of which 8 were not fully covered**. Those uncovered occurrences are on pages **1, 7, 12, 23, 31, 32 and 35**, with two occurrences on page 1. Some are omitted candidates, some are inside blocked overlap groups, and one is inside an overlong rejected PERSON span. This provides concrete qualitative evidence of missed or unresolved names without estimating overall document recall.

An additional exact-value screen found **60 surviving occurrences of values that were confirmed as PERSON elsewhere**. That screen can include business terms, duplicate hypotheses and overlaps with the name-anchor findings; the 60 are **not** asserted to be 60 verified personal identities or unique leaks.

### False positives and over-redaction screening

- **Three confirmed PERSON spans** contain ordinary business/role words and cross-line text. They may mix a real name with a committee/group label. These are possible overlong-span/over-redaction cases, not a demonstrated count of three entirely false identities.
- **40 confirmed government/banking candidates** lacked entity-specific supporting context in a 200-character radius: 19 US_DRIVER_LICENSE, 19 US_BANK_NUMBER, 1 US_ITIN and 1 US_SSN. Some overlap genuinely sensitive telephone/other identifier spans, so missing context alone does not establish a false positive.
- The two-character putative license candidate above is particularly weak evidence. Qwen confirmation should not be mistaken for a calibrated probability or a source-ground-truth label.
- **38 PERSON candidates** showed diagnostic indicators of OCR contamination such as concatenation, line breaks, labels or mixed characters. That count is an inspection flag, not a count of known errors.

False-positive rate, precision, recall and complete PII coverage cannot be measured without an independent labeled source inventory. This run found meaningful failure modes, but did not perform a full visual/manual labeling of every source page or verify the original PDF against ground truth.

## Local artifacts, security and commands

Sensitive artifacts are retained under:

`.private_validation/3f4b5db17d2e2694/`

The parent directory's inherited permissions were removed before writing evidence. Its Windows ACL grants FullControl only to the current Windows user and SYSTEM; child files inherit those restricted permissions. The extraction file's ACL was checked after completion. Storage is **local ACL-restricted plaintext**, not an encrypted vault. The directory and the source PDF have explicit entries in `.gitignore`. No Git configuration was changed.

Internal artifacts include:

- `manifest.json`: source and engine-code fingerprints.
- `extraction.json` and 35 `ocr_blocks_*.json` files: full text, original pages and OCR blocks/bounding boxes.
- `raw_page_*.json`, `detections.json` and `llm_evidence.jsonl`: raw candidate spans, final dispositions and local adjudication evidence/timing.
- `redaction_internal.json` and `redacted_internal_review.txt`: sensitive audit mapping and blocked review text.
- `metrics.json`: measured aggregate results, timings and sanitized diagnostics.
- `independent_sensitive_inspection.json`, `residual_sensitive_evidence.json` and `representative_sensitive_evidence.json`: exact evidence for local review only.
- `independent_sanitized_inspection.json`, `ssn_sanitized_check.json` and `independent_export_check.json`: sanitized follow-up evidence and export-block verification.

Do not send the internal artifacts to downstream LLMs or serialize the audit objects into an external payload. The redacted review text still contains identified residual PII.

Executed from the project root:

```powershell
Get-ChildItem -LiteralPath . -File -Filter *.pdf | Select-Object Name,Length
.venv/Scripts/python.exe -u tools/validate_cadence_document.py
.venv/Scripts/python.exe tools/inspect_cadence_evidence.py
```

The primary runner command was executed twice: the first ended with the console-encoding error, and the second succeeded using the first page's saved OCR checkpoint. The independent inspection command performed no OCR or Qwen inference. A separate cache-only `RedactionEngine().redact(...)` replay checked output identity and attempted `to_text_payload()`, confirming it was blocked. All source values and surrounding evidence stayed in the restricted directory; terminal output contained aggregates and selected sanitized structures only.

For future diagnostic-only reuse, the runner supports:

```powershell
.venv/Scripts/python.exe -u tools/validate_cadence_document.py --diagnostics-only
```

That mode was **not needed for this evaluation**. It requires existing extraction/detection caches and never invokes OCR or Qwen, although it repeats inexpensive File Intelligence/redaction/diagnostic work and refreshes corresponding metrics. Preserve the original metrics if comparing timings across runs.

Changes made in this task were limited to `.gitignore`, the two diagnostic scripts (`tools/validate_cadence_document.py`, `tools/inspect_cadence_evidence.py`), this report, and local private artifacts. No engine or model changes, Engine 5 implementation, commits or pushes were made.

## Final assessment

| Dimension | Assessment |
| --- | --- |
| Technical integration | **Successful**: Engines 1–4 processed all 35 pages; candidate accounting and recorded replacement positions passed; blocking/export behavior worked. |
| Detection accuracy | **Insufficient for clearance**: concrete OCR-concatenated names were omitted, a contaminated name was rejected, and independent email/phone/SSN-shaped residuals were found. Potential category false positives and oversized spans also require review. |
| Verified PII coverage | **Not established**: no labeled ground truth or full source-image review; independent probes are limited and cannot demonstrate 100% recall. |
| Downstream LLM readiness | **NOT READY**: `redaction_complete=False`, `safe_for_llm=False`, export blocked, and residual PII remains in the internal review text. |

The pipeline's fail-closed mechanism works for the unresolved spans it knows about. It does not catch every undetected value on its own. The next evaluation work should label the known residuals and conflict groups, investigate OCR-boundary candidate discovery and contaminated-span adjudication, and validate fixes against this trusted cache and a broader labeled dataset. **No such detection or prompt fixes were applied during this initial validation.**
