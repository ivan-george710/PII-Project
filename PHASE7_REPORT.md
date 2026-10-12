# Phase 7 DOCX and PPTX extraction and redaction

Implemented on 12 October 2026. The existing pipeline now processes DOCX/PPTX through extraction, deterministic detection, text redaction, audit, original-structure artifact generation and independent verification. Both supplied Cadence review copies reopen with their libraries. **Neither document is cleared for downstream submission.** The deck retains two confirmed spans that could not be mapped to a single source paragraph.

## Implementation and files

| File | Responsibility |
| --- | --- |
| `app/engines/file_intelligence/detector.py` | Content-based OOXML package identification when Windows libmagic reports ZIP/binary; does not trust filenames. |
| `app/engines/extraction/models.py` | Optional structural map, paragraph segments and text-node offsets; consolidate duplicate placeholder definitions. Existing positional constructors remain valid. |
| `app/engines/extraction/office.py` | Exact text/control-node mapping, source hashing and conservative package limitation inventory. |
| `app/engines/extraction/docx.py` | Body/nested-table/header/footer paragraph extraction. |
| `app/engines/extraction/pptx.py` | Slide/group/table/notes paragraph extraction with original ZIP-node validation. |
| `app/engines/extraction/engine.py` | Route DOCX/PPTX to these extractors through the existing public API. |
| `app/engines/redaction/artifacts.py` | Private original-package edits, mapping issues, reopening, independent re-extraction, structure/tag checks and residual diagnostics. |
| `app/engines/audit/engine.py` | Persist/restore optional mapping data and include it in Office identities/fingerprints; preserve historical PDF fingerprints by omitting absent mapping data. |
| `app/pipeline/pipeline.py`, `models.py` | Two artifact stages, feedback/reload regeneration and distinct progress/verification diagnostics. |
| `tests/test_office_documents.py` | 27 focused synthetic and real-Presidio tests. |
| `tests/test_document_pipeline.py` | Update the former unsupported-format test: standalone image remains unsupported; DOCX/PPTX are now supported. |
| `tools/validate_office_documents.py` | Supplied-document evaluation with aggregate terminal output and private diagnostic evidence. |
| `.gitignore`, `README.md`, `PHASE7_REPORT.md` | Private-output/source exclusions, current API documentation and this report. |

Already installed dependencies: `python-docx==1.2.0`, `python-pptx==1.0.2`; no dependency changes were needed. Engine 3's recognizers and policies, Engine 4's decision/overlap/tag logic and Engine 5's feedback semantics remain unchanged. No cloud services, database, API, authentication, Qwen, commits or pushes were introduced.

## Extraction and exact source mappings

DOCX uses one existing `ExtractedPage` per **logical paragraph segment**, ordered through the body XML and nested tables, then unique header/footer parts. Shared linked headers/footers are not duplicated. `page_number` is a positive logical segment identifier, never a claimed physical page number. Paragraphs join text across runs, including hyperlink runs, tabs and line breaks. Segment metadata identifies body/header/footer and table depth; part name and paragraph XPath identify the exact table cell/paragraph.

PPTX uses one `ExtractedPage` per actual slide. Shapes are visited in source order, including placeholders and recursive groups; table cell paragraphs and accessible body speaker notes follow their own mappings. Newlines separate paragraphs. Each segment retains slide number, shape ID, group chain, paragraph index, table row/column where applicable, package part, XPath, slide-text start/end and individual text-node offsets. Separators have no source text node. Candidates crossing paragraph boundaries are not guessed or merged.

Each optional `StructureMap` retains the source byte SHA-256, location convention, ordered segments and limitation counts. Engine 3 receives the ordinary `ExtractionResult`; its original candidate text, offsets, recognizers, confidences and CONFIRM/REJECT/REVIEW accounting remain intact. Mappings are internal sensitive audit data and never appear in sanitized summaries.

The real deck exposed another library behavior: accessing an empty placeholder text frame can cause python-pptx to create a paragraph in memory that is absent from the original ZIP. Extraction now validates paragraph references against the original XML and ignores those empty virtual paragraphs. It never invents an editable source mapping. A focused regression test covers this case.

## Artifact generation, feedback and verification

```python
from app.pipeline import DocumentPipeline
from app.engines.audit import ReviewerFeedback

pipeline = DocumentPipeline(artifact_output_dir=".private_artifacts")
result = pipeline.process("path/to/document.docx")  # or .pptx
if result.failure is None:
    artifact = result.artifact_result
    summary = result.sanitized_summary()
    # Choose an actual finding in the authorized review interface.
    updated = pipeline.apply_feedback(result, ReviewerFeedback(
        "FALSE_POSITIVE", "reviewer-id", result.audit_result.records[0].detection_id,
    ))
```

Office generation follows the audit stage and uses the current effective detections with the existing Engine 4 result. It verifies that those inputs regenerate the same text redaction, checks source integrity, validates every source mapping, copies the original ZIP package and edits selected text nodes in place. Replacements spanning formatting runs insert the tag into the first intersecting node and remove the sensitive portions from the remaining nodes. Run properties, tables, shape geometry, slide relationships and unrelated content remain intact; tags inherit the first run's formatting. Unchanged package members retain identical bytes.

Each artifact uses a random `review_<uuid>` filename in a separate private directory. Directory checks and Windows ACL/POSIX permission protection reuse Engine 5's storage helper; no second audit database is created. Files are written through temporary files and atomic replacement. Originals are never overwritten.

An unreliable **span** remains unchanged in a partial private review copy. Internal `mapping_issues` preserve its page/slide, original offsets and entity type for lookup against audit records. This is deliberately different from the flattened text preview, which may already contain a tag for that unmappable span. A broken mapping/source-integrity failure blocks artifact generation entirely and returns a sanitized failed-stage result.

Verification reopens the result through python-docx/python-pptx and independently enumerates supported output text. It checks the expected mapped replacements, actual tag offsets, all other supported text, source paragraph locations, ZIP member identity and XML structural signatures with text normalized. This detects unrelated package, formatting or geometry changes. Each unmappable confirmed span contributes one verification failure; correctly applied replacements are checked with adjusted offsets to avoid cascading failures from a retained unmappable span.

Residual diagnostics count occurrences of confirmed replacement values still present anywhere in supported output text, plus separate employee-ID/email/SSN pattern matches. These are potential remnants, not labeled ground truth or a new detection policy. They do not inspect image pixels or prove absence of other PII. Unsupported package content is inventoried separately.

Feedback delegates to Engine 5 and always generates a new copy from the fingerprinted original. The original result, source extraction and automated detections remain unchanged; no File Intelligence, source extraction, OCR or Presidio rerun occurs. Output re-extraction is performed for verification. Audit save/load remains explicit and now retains maps; Office reload regenerates a review artifact from the original source. Artifact paths/verification reports are not added to the audit JSON schema as a second persistent state; the diagnostic tool separately keeps local evaluation evidence.

## Safety and status semantics

`extraction_completed`, `detection_completed` and `text_redaction_completed` mean their operations returned results. They do not establish complete extraction, redaction completeness or coverage. Audit `human_review_complete` means no known automated review items remain, not that every unsupported object was reviewed.

Artifact `redaction_completed` means generation ran, including partial review copies. `verification_completed` means checks ran. `reopened` means the library could open/extract the output. `supported_content_verified` means all required mapped/text/structure checks passed; unsupported structures are separately reported. `artifact_verified` additionally requires no mapping failures, verification failures, residual matches, unsupported structures or known text-redaction review issues.

A successful operation with artifact limitations returns `PROCESSED_REVIEW_REQUIRED`, even if the audit queue itself is empty. Exceptions return `PROCESSING_FAILED` at `artifact_redaction` or `artifact_verification` with fixed sanitized diagnostics. Only allowlisted numeric counts, issue categories, booleans, statuses and timings appear externally. Source/artifact paths, names, detected values, map references and reviewer reasons remain internal.

**`safe_for_llm=False`, `coverage_verified=False`, and `downstream_export_permitted=False` always.** No artifact or review-completion shortcut enables submission.

## Real Cadence findings

Sources were discovered in the repository root: `Cadence_TPRM_Training.docx` and `Cadence_Financial_Group_Organizational_Pack.pptx`. Source byte hashes were checked before/after each evaluation; both originals were unchanged. Generated artifacts and internal evidence are under the ACL-restricted, gitignored `.private_artifacts/` directory. Public report data below contains counts only.

| Metric | Training DOCX | Organizational PPTX |
| --- | ---: | ---: |
| Logical paragraph sections / slides | 2,610 segments | 9 slides |
| Mapped paragraphs | 2,610 | 424 |
| Nonempty segments / slides | 2,345 | 9 |
| Extracted characters, excluding inter-page/slide join separators | 92,898 | 8,366 |
| Raw Presidio candidates | 424 | 59 |
| Confirmed | 29 | 25 |
| Rejected | 85 | 19 |
| REVIEW / audit queue items | 310 | 15 |
| Engine 4 text replacements | 29 | 25 |
| Actual artifact replacements | 29 | 23 |
| Unmappable confirmed spans | 0 | 2 |
| Verification failures | 0 | 2 |
| Supported content verification passed | Yes | No |
| Remaining confirmed-value occurrences in supported output | 33 | 5 |
| Separate EMP/email/SSN pattern matches in supported output | 0 | 34 |
| Output reopened using its library | Yes | Yes |
| Artifact verified / coverage verified / export permitted | No / No / No | No / No / No |
| Measured pipeline runtime | 19.365417 s | 2.862004 s |

Candidate accounting is consistent: DOCX 29 + 85 + 310 = 424; PPTX 25 + 19 + 15 = 59. Neither has a superseded/crossing Engine 4 overlap. The PPTX mapping failures are confirmed spans crossing paragraph boundaries, not failed overlap resolution. Their exact source offsets are retained privately.

DOCX residual-value count 33 and PPTX count 5 count repeated strings matching confirmed values elsewhere in supported output; their classification may differ at those other locations. They are not 33/5 independently verified missed PII findings. The separate 34 PPTX pattern matches also require human interpretation and may overlap known REVIEW findings. The tests/report make no detection-recall claim.

| Unsupported/unverified category | DOCX count | PPTX count |
| --- | ---: | ---: |
| Alternative-text-bearing objects | 58 | 9 |
| Annotation/footnote/endnote package parts | 2 | 0 |
| Content controls | 8 | 0 |
| Document-property parts | 3 | 3 |
| Dynamic fields | 44 | 11 |
| External relationships | 2 | 0 |
| Media parts without OCR | 41 | 1 |
| Text boxes | 4 | 0 |
| Unmapped OOXML text nodes | 80 | 16 |

Counts are inventory units, can overlap and are not counts of confirmed PII. Unmapped text may occur in unsupported controls, annotations, layout/master content or other parts. Images were not OCR-processed. Unsupported content remains unchanged in private review copies and prevents artifact clearance.

Measured stages, seconds:

| Stage | DOCX | PPTX |
| --- | ---: | ---: |
| File Intelligence | 0.051685 | 0.006377 |
| Extraction | 0.843545 | 0.388671 |
| Detection, including lazy initialization | 15.831223 | 1.777249 |
| Text redaction | 0.010530 | 0.001186 |
| Audit | 0.389273 | 0.229201 |
| Artifact generation | 0.575543 | 0.252313 |
| Artifact verification | 1.663510 | 0.206931 |

The PPTX measurement is a targeted final rerun after correcting virtual-placeholder mappings and partial-copy verification. DOCX metrics are retained from its successful full pipeline evaluation. The diagnostic tool supports `--format` to avoid repeating unchanged format evaluations. Earlier failed deck attempts exposed the mapping issues; no rules or model prompts were changed.

## Tests and exact commands

```powershell
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/python.exe -u tools/validate_office_documents.py
.venv/Scripts/python.exe -u tools/validate_office_documents.py --format pptx
```

Final full-suite result: **217 passed in 61.23s (0:01:01)**. Includes all previous detection/redaction/audit/PDF regression coverage, the updated format-support tests and 27 Office cases. Focused Office tests cover paragraph/run joining, nested tables, headers/footers, placeholders, groups, notes, multiple slides, exact source mappings, all three feedback actions, fresh-source regeneration, non-sensitive text and formatting, reopened outputs, tampered-output residual verification, image/chart/text-box limitations, source integrity, missing/broken mappings, private-directory guards, persistence/reload and real Presidio on both formats. Content-based classification tests also cover misleading extensions and ordinary ZIP files disguised as DOCX.

A separate read-only reload of the existing historical Cadence PDF audit succeeded: 35 pages, 1,418 raw candidates, no Office artifact stage and `safe_for_llm=False`. Original PDF audit fingerprints remain compatible. The 35-page PDF was not OCR-processed again.

Python compilation checks passed for the changed modules. `.private_artifacts` ACL inspection confirmed non-inherited FullControl entries only for the current Windows user and SYSTEM. Root/local gitignore rules exclude the original supplied documents and generated review artifacts/evidence.

## Limitations and completion assessment

Both real artifacts are **library-readable private review copies**, with tables/slides and unrelated package structures preserved. They were not opened in Microsoft Word/PowerPoint or visually rendered. LibreOffice and the skill's packaged DOCX renderer were unavailable on this Windows host; therefore no visual-layout guarantee is made. Longer replacement tags can change wrapping or overflow fixed slide boxes. The implementation preserves formatting where practical but does not resize/reflow layouts automatically.

No OCR of Office images, text-box extractor for DOCX, content-control/tracked-change resolution, dynamic-field refresh, chart/embedded-document sanitization, metadata stripping, signature handling or whole-package PII coverage verification is implemented. Strict/transitional OOXML variants, unusual namespace aliases and unsupported library constructs may fail closed. The source must remain available and byte-identical for regeneration. Private files contain unverified content, including retained confirmed spans in partial copies; they are not encrypted and must remain inside the authorized review boundary.

**Implementation complete for supported structures, with explicit real-document blockers.** DOCX/PPTX processing and mapped structure-preserving redaction work through the existing pipeline and reviewer workflow. The supplied DOCX passes mapped-content verification; the supplied PPTX is usable for review but fails verification on two unmappable spans. Technical integration does not establish detection accuracy, complete extraction, verified PII coverage or downstream readiness.
