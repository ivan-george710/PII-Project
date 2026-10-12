# Phase 8 usable redacted artifacts

Implemented 12 October 2026. All three supplied formats now produce real private review files that reopen and pass supported-content verification. The PDF has 577 selected replacements, DOCX 29, and PPTX 25; both previously unmappable deck spans are resolved. **Every output remains blocked for downstream submission.**

## A. Files Changed

| File | Change |
| --- | --- |
| `app/engines/redaction/pdf_artifacts.py` | Destructive native PDF redaction, edited-raster OCR pages, hybrid routing and text/render/image-payload verification. |
| `app/engines/redaction/document_artifacts.py` | Small dispatcher between PDF and the existing Office backend. |
| `app/engines/redaction/artifacts.py` | Add common result aliases/format/evidence fields and deterministic PPTX boundary plans; preserve Office package editing. |
| `app/engines/extraction/models.py` | Optional typed PDF source fingerprint/DPI metadata. Existing constructors retain positional compatibility. |
| `app/engines/extraction/pdf.py`, `ocr.py` | Populate source fingerprints and explicit OCR resolution metadata; hybrid OCR uses 150 dpi explicitly. |
| `app/engines/audit/engine.py` | Persist/restore optional PDF metadata, include present metadata in source identity, and omit absent fields to preserve older audit fingerprints. |
| `app/pipeline/pipeline.py` | Dispatch PDF/DOCX/PPTX generation and verification through existing artifact stages, including feedback/reload. |
| `tests/test_pdf_artifacts.py` | 11 focused native/scanned/hybrid, mapping, destructive removal, regeneration and tamper tests. |
| `tests/test_pptx_boundaries.py` | Five structural-boundary regression tests. |
| `tests/test_document_pipeline.py` | Mock the new artifact stage for deliberately non-PDF synthetic stage-contract fixtures. |
| `tools/validate_phase8_documents.py` | Three-document diagnostic and targeted reruns with trusted PDF cache reuse. |
| `requirements.txt`, `README.md`, `PHASE8_REPORT.md` | Pin PyMuPDF, document current behavior and report measured evidence. |

PyMuPDF **1.28.2** was added to the project virtual environment. The ordinary download timed out; the official PyPI wheel was fetched in byte ranges and its SHA-256 checked against official PyPI metadata before local installation. Existing Office libraries remain unchanged. No detector policies, Qwen, database, network API, frontend, authentication, cloud services, original documents, commits or pushes were introduced.

## B. PPTX Mapping Fix

Both real deck findings include confirmed text followed by the extractor's generated newline. One is a text-box paragraph on slide 3; the other is a table-cell paragraph on slide 8. They do not require merging unrelated source text. The mapper now identifies confirmed characters in the paragraph, applies the existing tag to those characters and retains the structural paragraph separator. This resolves both patterns without exact-value exceptions.

The same mapping planner supports actual multi-paragraph spans when consecutive mapped paragraphs share the same package part, shape/group chain, source text frame or table cell, and the extracted gap is exactly the generated newline. It inserts one tag in the first segment and removes only the confirmed portions in subsequent segments. Prefix/suffix text, paragraph properties and run formatting remain intact. Different shapes, slides and table cells are not combined. Gaps that cannot be proven remain mapping issues.

Verification compares independently re-extracted paragraph text to each paragraph's planned edits, rather than requiring deletion of structural separators from the file. Therefore an Office artifact can preserve paragraph newlines while its flattened Engine 4 preview has replaced those characters. Tests exercise trailing separators and genuine adjacent-paragraph spans in both text frames and table cells, plus an ambiguous cross-shape span that stays blocked.

## C. PDF Artifact Redaction

Native pages align the extraction's non-whitespace character sequence to PyMuPDF's source glyph sequence and retain exact character bounding boxes. If the sequences differ, rotation is unsupported or the selected rectangles would intersect unrelated glyphs, the finding is unmappable. No fuzzy text search or coordinate guess is used.

Mapped glyph rectangles receive redaction annotations, which are **applied** before labels are inserted. The new document is saved with cleanup, compression and `garbage=4`; this removes underlying redacted text instead of covering it with a drawing. This follows the [PyMuPDF destructive redaction contract](https://pymupdf.readthedocs.io/en/latest/page.html#Page.apply_redactions). Labels are confined to the removed region and omitted when they cannot fit a practical font size. Other pages/content are copied through the existing PDF structure where practical.

Scanned pages require source-byte identity, a known OCR render DPI and valid bounded OCR quadrilaterals. Exact block-joined text must match the extraction. Confirmed portions can span proven OCR block separators; each participating block must validate. Source images are rendered at the trusted resolution, mapped block rectangles are replaced with white pixels, and new pages embed **only the edited raster**, never the original image payload or original source-page content streams.

OCR boxes locate whole text blocks, not individual glyphs. Consequently a patched block is reconstructed from its retained non-sensitive OCR transcription plus the current tags. This preserves extracted context but changes typography inside the patch and inherits any OCR transcription errors. Unrelated raster pixels outside the patch remain intact. In very small boxes a visible tag is omitted; retained non-sensitive transcription is still redrawn, including small original punctuation. On the real PDF, **65 patched block labels were omitted** because they did not fit the minimum tag size. Destructive pixel replacement still occurred and verified. This is a visual/readability limit, not permission to send the file downstream.

Hybrid PDFs follow existing per-page extraction routes: native pages use glyph redaction and OCR pages use raster replacement. Native pages containing image content flag those images as unverified; this phase does not introduce same-page image OCR or change the extraction policy. Scanned pages with unverified crop/resolution geometry fail closed. Output page dimensions and page count are preserved.

All artifacts use random `review_<uuid>` filenames in the existing `.private_artifacts/` area with Engine 5's private-directory guards/ACLs and atomic replacement. Originals are not overwritten.

## D. Verification Logic

The common result retains Phase 7 names and adds the requested aliases:

```python
artifact.format
artifact.output_path                 # alias of path; internal only
artifact.redaction_completed
artifact.verification_completed
artifact.reopened
artifact.supported_content_verified
artifact.mapping_issue_count         # alias of mapping_failures
artifact.verification_failure_count  # alias of verification_failures
```

Office verification still reopens with python-docx/python-pptx, independently extracts supported structures, checks the expected mapped text/tags and compares normalized XML structure and unchanged ZIP members. DOCX editing was not redesigned.

PDF verification reopens the generated PDF, extracts selectable text, checks native mapped regions for removed original values and applicable tags, rerenders all pages and compares page render digests/dimensions against generation evidence. Scanned pages must contain a single expected edited raster whose decoded pixel bytes/dimensions match the sanitized image evidence. This verifies actual pixel replacement and prevents reuse of the original image payload. The retained transcription must appear in the mapped region; slightly overlapping neighboring OCR rectangles can contribute extra neighboring labels, so exact raster payload verification is performed separately. Optional labels are checked only when written.

Each unmappable span contributes a verification failure. Altered image payloads, altered page renders, surviving mapped native values, missing expected retained transcription/tags or changed page geometry also fail verification. An overlay-only implementation does not pass the native text-removal tests. Generated files can remain usable partial review copies, but `supported_content_verified` is false if any required mapping/check fails.

The broader existing `artifact_verified` gate remains stricter and false on the real documents because known review findings, unsupported structures or potential residual matches remain. `supported_content_verified=True` means the supported confirmed mappings were successfully applied and checked; it is not coverage approval. **`safe_for_llm`, `coverage_verified` and `downstream_export_permitted` are always false.**

A rendered crop containing only a replacement tag was visually inspected at enlarged scale. Every real PDF page was additionally rerendered automatically during verification. No full unredacted pages or candidate inventories were printed into terminal logs.

## E. Reviewer Feedback Regeneration

`DocumentPipeline.apply_feedback()` continues delegating all three actions to Engine 5. Effective detections drive a fresh artifact created from the byte-identical original; the previous redacted artifact is never edited or used to restore a false positive. Source extraction and automated detection snapshots remain unchanged. Source coordinate lookup/raster rendering are part of artifact generation, not another Engine 2/OCR or Presidio run.

Tests verify FALSE_POSITIVE restores original native PDF content, CONFIRM_PII applies removal and MISSED_PII redacts a validated manual source span. New paths are created for every generation. Office feedback regressions also remain covered. Missing/changed source fingerprints block generation.

New extraction/audit results store PDF source fingerprints and OCR DPI. Older PDF audit snapshots without this additive metadata remain loadable by Engine 5, but pipeline artifact generation fails closed until trusted metadata is supplied. The real-document diagnostic explicitly attaches the known 150-dpi metadata to the trusted cache in memory after checking source and detection-policy fingerprints; cache files are not rewritten.

## F. DOCX Regression Validation

The real training DOCX still has 2,610 logical paragraph segments, 424 candidates, 29 confirmed, 85 rejected and 310 REVIEW. All 29 selected replacements are applied, with zero mapping or verification failures. Tables, nested tables, headers and footers remain accessible; the output reopens and supported-content verification passes.

DOCX segment count is a logical location convention, **not physical pagination**. Longer tags may change wrapping. No Word/PowerPoint rendering guarantee was added; existing unsupported structures and coverage limits remain.

## G. Real Cadence Validation

The supplied documents were discovered locally. PDF extraction/detection reused the trusted source-matched cache; neither full OCR nor PDF Presidio was repeated. Office documents ran through real extraction/Presidio. Both sources and generated evidence remain private and gitignored.

| Metric | Policy PDF | Training DOCX | Organizational PPTX |
| --- | ---: | ---: | ---: |
| Source locations | 35 pages | 2,610 logical segments | 9 slides |
| Raw candidates | 1,418 | 424 | 59 |
| Confirmed | 578 | 29 | 25 |
| Rejected | 668 | 85 | 19 |
| REVIEW findings | 172 | 310 | 15 |
| Engine 4 selected replacements | 577 | 29 | 25 |
| Artifact replacements | 577 | 29 | 25 |
| Mapping failures | 0 | 0 | 0 |
| Verification failures | 0 | 0 | 0 |
| Reopens | Yes | Yes | Yes |
| Page/slide/logical-segment count preserved | Yes | Yes | Yes |
| Supported-content verification passed | Yes | Yes | Yes |
| Original bytes unchanged | Yes | Yes | Yes |
| Output bytes | 24,333,760 | 4,813,711 | 68,330 |
| Measured pipeline seconds | 12.087934 | 14.694389 | 1.047623 |
| Coverage verified / export permitted | No / No | No / No | No / No |

The PDF's one superseded overlap accounts for 578 confirmed detections versus 577 selected replacements. All candidate dispositions remain consistent. The deck's previous two issues are both resolved; all 25 confirmed findings now map and verify. The DOCX's previously passing behavior remains intact.

Potential residual confirmed-string occurrences in supported output: PDF 8, DOCX 33, PPTX 1. These are repeated matching strings, not individually labeled missed-PII findings. The PPTX has 34 separate employee-ID/email/SSN diagnostic pattern matches; other Office pattern counts are zero. PDF raster content outside patched regions is **not** independently OCR-scanned again, so PDF residual-string counts apply only to output selectable text. They are not a whole-image residual PII assessment.

Office unsupported inventories remain as reported in Phase 7: DOCX includes text boxes, controls, fields, annotations, metadata, alternative text, external relationships, 41 media parts without OCR and 80 unmapped text nodes. PPTX retains unverified master/layout/field/metadata/alternative content, one media part and 16 unmapped text nodes. The PDF flags source document properties as unverified. Review queues remain 172/310/15 respectively; no real-document human corrections were applied merely to improve metrics.

Private locations: `.private_artifacts/phase8_summary.json` contains aggregate metrics. `.private_artifacts/phase8_diagnostic_internal.json` links source fingerprints and randomized outputs and retains sensitive coordinate/transcription evidence. `.private_artifacts/phase8_mapped_region.png` is the tag-only visual check. These files are excluded by root/local gitignore rules and protected by the existing private-directory ACLs.

Final PDF generation/verification times were 7.563962/3.990948 seconds. DOCX generation/verification were 0.513875/1.360597 seconds; PPTX 0.269801/0.211733 seconds. Cache wrapper timing is not PDF model inference time. Interpreter startup, imports and dependency installation are outside pipeline timing.

## H. Test Results

Exact final command:

```powershell
.venv/Scripts/python.exe -m pytest tests -q
```

**233 passed in 40.19s.** This includes the previous suite, 11 PDF cases and five PPTX boundary cases. Native/scanned/hybrid PDFs, destructive text removal, edited OCR image payloads, page counts, parser reopening, text re-extraction, invalid mappings, source integrity, all three feedback actions, original immutability, source-extraction/Presidio call counts and tampered output are covered. Existing Office and detector/audit regressions pass.

Real-document commands:

```powershell
.venv/Scripts/python.exe -u tools/validate_phase8_documents.py
.venv/Scripts/python.exe -u tools/validate_phase8_documents.py --format pdf
```

Targeted PDF reruns reused the same trusted cache and did not repeat OCR/detection. The initial PDF artifact diagnostic exposed four block-separator mappings and small/overlapping label checks; those generic cases were fixed without changing detection policy. The final retained metrics show zero required mapping/verification failures.

## I. Known Limitations

- No labeled ground truth, independent coverage verification or downstream clearance is implemented.
- OCR mappings are trusted block-level outputs, not independently verified character/image recognition. Patched block typography is reconstructed from OCR and can preserve OCR mistakes. Original raster/vector/editable content on scanned pages becomes a sanitized raster plus new transcription; annotations and interactive source features are not preserved on those rebuilt pages.
- Very small blocks can omit tags or require small fonts for retained punctuation. Native labels are also optional when they cannot fit. General visual layout usability in Word/PowerPoint was not independently rendered in this phase.
- Rotated native PDF text, mismatched extraction/glyph order, unknown DPI, unsupported crop geometry and unreliable boxes fail closed. Native pages with images do not establish image PII coverage. Shared/unverified image or metadata content elsewhere in a document is not globally sanitized by a mapped text operation.
- The raster payload/render checks prove that the supported mapped regions were replaced; they do not prove the OCR originally located every PII value correctly. Unknown/rejected/REVIEW PII can remain elsewhere in all three formats.
- Different PPTX shapes/cells, nonconsecutive paragraphs and unproven gaps remain unsupported cross-boundary cases. Structural separators are preserved rather than removed from the original file.
- Artifacts contain unverified content and local snapshots are not encrypted. Application-layer authorization, concurrency, upload limits and multi-user persistence remain outside this phase.

## J. Completion Status

**Phase 8 complete for the requested supported artifact paths.** The real DOCX continues to verify; the real PPTX resolves both previous mapping failures; the PDF now produces a usable 35-page destructive/raster redacted file with all 577 selected mappings checked. Reviewer feedback regenerates from the original across formats. Technical artifact success remains separate from detection recall, full-document safety and downstream readiness.
