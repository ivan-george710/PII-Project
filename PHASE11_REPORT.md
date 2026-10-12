# Phase 11 — Face detection and biometric privacy redaction

Evaluation date: 2026-10-12. Local Windows CPU implementation. No commit or push.

Supported mapped faces now enter the existing Cadence pipeline as anonymous
`FACE` / `BIOMETRIC` findings, receive actual pixel blur, and have that transformation
checked in the serialized review artifact. This establishes supported transformation
integration, not complete face discovery or document privacy coverage.
`safe_for_llm`, `coverage_verified`, and `downstream_export_permitted` remain **false**.

## A. Source Face Detector Review

Directly inspected the private `ivan-george710/PII-Project` source at commit
`63a416b70cf452527f42cbb1a3d9a4f80f94271f` before adapting it:

- `packages/engine/src/pii_guard/detection/faces.py`
- `packages/engine/src/pii_guard/redaction/image.py`
- `packages/engine/src/pii_guard/model_assets/index.md`
- `packages/engine/src/pii_guard/model_assets/YUNET_LICENSE.txt`

Preserved CPU YuNet, model checksum, four rotation passes, overlapping tiles,
bounded inference frames, overlap deduplication, normalized padded boxes, locking,
and sanitized failure behavior. The reference image redactor used black fill;
Cadence implements pixel blur. No foreign DetectionCandidate, SourceLocation,
policy, pipeline, database, authentication, or API contracts were copied.

Development retrieval used authenticated GitHub CLI contents requests pinned to
the commit, for example:

```powershell
gh api "repos/ivan-george710/PII-Project/contents/packages/engine/src/pii_guard/detection/faces.py?ref=63a416b70cf452527f42cbb1a3d9a4f80f94271f"
gh api "repos/ivan-george710/PII-Project/contents/packages/engine/src/pii_guard/model_assets/face_detection_yunet_2023mar.onnx?ref=63a416b70cf452527f42cbb1a3d9a4f80f94271f"
```

The binary raw-response attempt failed with `transform: short source buffer`.
The contents API's base64 response was decoded locally and its checksum verified.
Private development copies are in gitignored `.private_phase11/source/`.

## B. Adapted Architecture

Small modules under `app/engines/visual_detection/` provide canonical image decoding,
YuNet inference, media inventory/mapping, visual models, and audit rows.
`ExtractionResult.visual` carries the source-bound inspection into the existing
DocumentPipeline and AuditEngine. The face stage follows extraction and remains
separate from text detection. Cadence's current effective decision/revision mechanism
handles visual feedback. No second pipeline, review store, or database was introduced.

The existing artifact engines delegate source-image preparation and verification to
`app/engines/redaction/visual_artifacts.py`. Regeneration reads the original source
plus current text and visual decisions; it never edits an earlier blurred artifact.

## C. YuNet Model Integrity

Vendored licensed asset: `app/engines/visual_detection/assets/face_detection_yunet_2023mar.onnx`.
Size: **232,589 bytes**. Expected SHA-256:

```text
8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4
```

Origin: OpenCV Zoo YuNet; source index pins upstream commit
`47534e27c9851bb1128ccc0102f1145e27f23f98`, `models/face_detection_yunet`.
MIT license, copyright 2020 Shiqi Yu, preserved verbatim in `YUNET_LICENSE.txt`.
`ATTRIBUTION.md` records both source commits, paths, and model checksum.
Existing OpenCV supports FaceDetectorYN; measured loaded version is **4.10.0**.
No new dependency, runtime model download, cloud API, GPU claim, or generative
inference was added. Missing model, hash mismatch, missing OpenCV, and inference
failure stop the visual stage with a sanitized error. Unsupported/undecodable
media is inventoried and prevents successful visual verification.

## D. Visual-Media Extraction

PNG/JPEG single-frame rasters are bounded to 25 MiB and 16,777,216 pixels.
Media are traced by source hashes, dimensions, canonical pixel hashes, part/xref,
relationship/XML path, and document locations. Cache is per inspection run and
keyed by image hash/frame. Reused media is inferred once and retains all placements.

Office media parts and package thumbnails are inspected. DOCX locations are
logical extraction segments, not rendered Word page numbers. PPTX locations are
slide numbers; deterministic picture/group geometry remains in original XML.
Thumbnails and unplaced media receive truthful package labels, not invented pages.

Unsupported formats, malformed images, external/missing media, unsupported drawings,
charts/vector constructs, embedded objects, unexpected raster package parts,
unmapped placements, PDF annotations, and unsafe PDF image mappings are inventoried.

## E. Face Detection

Policy `face-1.0`: YuNet candidate threshold **0.35**. All emitted candidates are
retained; mapped confidence **>=0.85** is automatically `CONFIRM`, while lower
confidence or uncertain placement is `REVIEW`. Automatic confirmation is explicitly
policy resolution, not a human review. The model emits no candidates below its
threshold; that cutoff and probabilistic detection limit coverage claims.

Four rotations and, for large images, nine overlapping tiles supplement the
full-frame pass. Inference frames are capped at 1280 pixels; boxes are deduplicated
and padded 8% horizontally and 12% vertically. Findings contain stable V identifiers,
confidence, YuNet recognizer, normalized padded region, source reference, format,
and occurrence locations. They contain no identity or demographic predictions.

## F. Blur Transformation

Each confirmed region is converted to bounded source pixels. Heavy BOX downsampling
to approximately one pixel per 24 source pixels discards detail, followed by
bilinear expansion and Gaussian blur with radius `max(12, 0.22 * max(region dimensions))`.
Actual pixels are composited into a fresh raster; unchanged regions fail verification.
Fresh PNG/JPEG encoding strips EXIF previews, orientation metadata, and profiles.
Office EXIF orientation is baked before processing; PDF uses intrinsic pixel frames.
Alpha is flattened onto white to prevent hidden RGB/alpha facial detail surviving.

The synthetic downloaded portrait was visually inspected: facial detail is strongly
obscured. This is not a proof of anonymity, inability to infer identity from other
content, or total biometric removal.

## G. PDF Integration

OCR pages reuse the established page raster/dpi mapping without rerunning OCR.
Face blur precedes existing OCR text masking, and a fresh image-only PDF page
replaces the original payload. Native pages preserve text; accessible unmasked
embedded image xrefs are replaced using source pixel/placement evidence.
Inline, masked, singular, cropped-raster, or otherwise unsafe mappings are blocked
or inventoried rather than guessed. Hybrid documents use these per-page paths.
Original source files remain unchanged. Synthetic native and scanned PDFs reopen,
preserve page count, retain text redaction, and prove changed face pixels.

## H. DOCX Integration

Fresh blurred bytes replace the corresponding image media part inside the original
package. Surrounding paragraphs, tables, styles, relationships, image placement,
and dimensions remain under existing structure verification. All uses of a shared
part receive the same replacement. Unsupported drawings are not represented as
sanitized. Synthetic Word fixtures retain their structure and text redaction.

## I. PPTX Integration

The same media replacement preserves slide/shape XML, text, geometry, and relationships.
The synthetic portrait is reused on two slides, including a grouped picture:
one image-level face finding has two traceable placements. Both uses are blurred;
the downloaded presentation reopens with two slides and the original image dimensions.

## J. Artifact Verification

Verification independently reopens generated files, retrieves active output media,
recomputes the expected original-derived transformation, and checks encoded/pixel
evidence, dimensions, region changes, placement/structure, and source integrity.
Native PDF verification checks each mapped occurrence's active pixels and placement
transform, including later pages sharing one image xref. Removing a later occurrence
fails visual verification even when the first protected occurrence remains intact.
Office checks that original targeted unblurred payloads are not retained elsewhere.
PDF checks active image payloads and sanitized raster output; OCR text masks are
independently composed over expected blur. Existing PDF rendering/text and Office
structure checks remain required. Serialized-media tampering fails closed and clears
protected counts. No post-blur detector result is used as privacy proof.

`face_transformations_verified` describes requested supported transformations only.
With zero confirmed faces, it may be true for zero requested transformations even
when face candidates need review. UI explicitly says no blur was scheduled; it does
not claim those pending faces were cleared. Unsupported visual items make this flag false.

## K. Audit / Review Integration

Visual rows enter immutable baseline/current effective decisions and existing
feedback replay, revision checks, persistence, and tamper validation. Rejecting and
reconfirming a face regenerate from original bytes without rerunning either detector.
Restored synthetic artifacts are byte-equivalent to fresh regeneration.
Protected status is derived from verified artifact face IDs, not policy decisions.
Low-confidence faces and unsupported inventory enter the existing review queue.
Public text candidate/disposition counts remain textual; visual totals are separate.
Metadata-only feedback export includes visual events without images/crops.
Text-offset MISSED_PII cannot invent face boxes and rejects FACE additions.

## L. UI Integration

Targeted additions to existing React views:

- Separate Visual Privacy detected/protected/review and inspected-media counts.
- Story: Extract Content & Media; Presidio text / YuNet faces; Privacy Transformation.
- Distribution map shows textual findings and separate face occurrence counts.
- FACE details show YuNet, confidence, location, policy/effective action, and bounded
  trusted-local BEFORE / actual verified blurred AFTER crops.
- Existing confirm/reject feedback, audit trail, artifact verification, and direct download.
- Coverage remains NOT ESTABLISHED and Downstream AI remains BLOCKED.

Crop endpoints are revision-bound, capped to 512 pixels, no-store, and return only
the relevant face region. There is no whole-image endpoint. Legacy audits without
visual inspection display that state truthfully. Mobile layout remains supported.

## M. Performance

Measured real-document stages (seconds, CPU; one shared detector instance):

| Format | Text detection | Face inspection | Artifact generation | Artifact verification | Pipeline runtime |
|---|---:|---:|---:|---:|---:|
| PDF | cached, 0.000006 | 24.072 | 7.264 | 7.181 | 39.094 |
| DOCX | 12.802 | 11.443 | 0.522 | 1.348 | 27.174 |
| PPTX | 1.519 | 0.058 | 0.249 | 0.180 | 2.683 |

Total diagnostic elapsed: **69.384 s**, including setup/serialization. PDF OCR and
text detection were reused from trusted source-hash/policy-checked private caches.
No full-document OCR or text detection was repeated for that PDF. Shared-image cache
behavior is tested separately; real documents recorded zero cache hits.

## N. Synthetic Test Results

Fixture `tests/fixtures/visual/synthetic-face.png` is a newly generated fictional
portrait, not a real employee or scraped photograph. Its README records origin.
`tools/create_phase11_fixtures.py` builds fictional PDF/DOCX/PPTX samples locally.
Real YuNet tests cover single/multiple/rotated faces, tiles/dedup, normalization,
no face, corrupt/unsupported images, missing model/OpenCV, hash mismatch, inference
failure, blur strength, metadata removal, reused media/cache, all four format paths,
artifact tampering, review regeneration, audit replay, and bounded API crops.

The scanned integration fixture supplies known synthetic OCR blocks at 72 dpi to
exercise raster/text composition without another OCR run. Native/Office integrations
use their real extractors. Browser acceptance uses real default engines on a synthetic
PPTX. The downloaded media's face-region gradient ratio after/before is **0.04148**
(about 4.15% of original local detail), in addition to pixel hashes/reopen checks and
visual inspection. The same source media has two placements, both protected.

## O. Real Cadence Visual Diagnostic

Aggregate evidence: `phase11_visual_diagnostic.json`. Private source-bound extraction,
audit details, and generated review artifacts remain under restricted, gitignored
`.private_phase11/real-documents/`. No real crops, page images, candidate inventories,
or identities are included here or printed by the diagnostic tool.

| Format | Inspected visual units | Faces | Confirmed | REVIEW | Protected | Mapping failures | Unsupported visual items |
|---|---:|---:|---:|---:|---:|---:|---:|
| PDF | 35 page rasters | 2 | 0 | 2 | 0 | 0 | 0 |
| DOCX | 35 decoded assets | 0 | 0 | 0 | 0 | 0 | 12 |
| PPTX | 1 decoded asset | 0 | 0 | 0 | 0 | 0 | 3 |

DOCX: six unsupported image formats and six uninspected visual constructs.
PPTX: three uninspected visual constructs, zero unsupported image formats.
These are inventory item counts, not deduplicated physical object counts.
PDF two candidates remain unadjudicated; no face finding was forced to improve metrics.
Their accuracy cannot be established without private human labeling.

All three originals remain unchanged and all generated artifacts reopen. Supported
text checks pass with 576/29/25 applied redactions, respectively. Existing residual
diagnostics still report 8/33/1 confirmed-value occurrences and 0/0/34 sensitive
pattern matches; these do not establish labeled misses or precision. Global artifact
verification remains false for all three. PDF has zero requested confirmed face
transformations and two pending faces; DOCX/PPTX visual proof is blocked by unsupported
content. No complete visual/text recall, face precision, or privacy clearance is claimed.

## P. Full Regression Results

Final sequential checks:

| Check | Result |
|---|---|
| Full Python suite | **302 passed**, 87.78 s after final per-occurrence verification change; one existing Starlette/httpx deprecation warning |
| Frontend Vitest | **40 passed**, 11.48 s |
| JavaScript utility tests | **4 passed** |
| ESLint | Passed, zero warnings |
| TypeScript + Vite production build | Passed |
| Real Chromium synthetic face PPTX | Passed: one face, two placements, downloaded blur verified, file reopens |
| Real Chromium synthetic DOCX workflow | Passed: confirm, MISSED_PII, reject, revision 3 save/reload, download, mobile |
| Real Chromium synthetic PDF workflow | Passed: confirm/reject, revision 2 queue complete, latest download reopens, mobile |
| Real Chromium PDF preview + feedback | Passed: embedded PDF preview, MISSED_PII, rejection, saved revision 3 reload |
| Final real-media inventory recheck | All three formats match saved diagnostics; zero OCR/inference runs |
| Phase 10A text policy fingerprint check | Unchanged against saved hardened evaluation fingerprints |

Browser scenarios recorded zero runtime/security errors and preserve explicit coverage
and downstream blocking. Face API tests also exercise reject/reconfirm, saved audit
replay, stale crop rejection, and source-based regeneration. The first full-suite attempt
ran alongside two Chromium tasks and the isolated model-loaded app, exhausting host
memory: eight failures and one setup error included MemoryError and subprocess/thread
startup failures. Those test jobs were stopped; only the Phase 11 test server was
temporarily stopped to release memory. The complete suite then passed sequentially,
and all browser scenarios passed after restarting the isolated server. No production
safety check was weakened to obtain these results.

Reproducible commands, from project root unless noted:

```powershell
.venv\Scripts\python.exe tools/create_phase11_fixtures.py
.venv\Scripts\python.exe -m pytest tests -q
npm.cmd --prefix frontend test
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
node --test tests/frontend/core.test.mjs
.venv\Scripts\python.exe .phase10b/serve_phase11.py
node tests/frontend/phase11_browser.mjs
$env:CADENCE_UI_URL='http://127.0.0.1:8767'
$env:CADENCE_UI_SYNTHETIC='1'
$env:CADENCE_UI_FIXTURE="$PWD/.private_review_app/phase10b-fixtures/synthetic.docx"
node tests/frontend/phase10b_browser.mjs
$env:CADENCE_UI_FIXTURE="$PWD/.private_review_app/phase10b-fixtures/synthetic.pdf"
node tests/frontend/phase10b_browser.mjs
$env:CADENCE_UI_COMPLETE='1'
node tests/frontend/phase10b1_browser.mjs
.venv\Scripts\python.exe tools/validate_phase11_documents.py
.venv\Scripts\python.exe tools/check_phase11_inventory.py
```

The real diagnostic refuses to overwrite existing private evidence. Inventory recheck
performs no inference/OCR. Browser evidence stays private. The isolated Phase 11
test app uses localhost:8767; preexisting app sessions on 8765/8766 were not restarted.
The private test-server helper simply runs `create_app(work_dir=Path('.private_phase11/browser-app'))`
under uvicorn on port 8767 with access logs disabled. Normal product startup remains
`.venv\Scripts\python.exe run.py` on port 8765. The prior-phase synthetic text fixtures
can be recreated with `tools/create_phase10b_fixtures.py`.
An operator must save pending reviews and restart an existing application process to
load the new Python modules. The frontend build is already generated.

## Q. Known Limitations

- Probabilistic detector, no labeled real-document face ground truth or comprehensive
  visual benchmark. No claim that every face was found, or that blur proves anonymity.
- PNG/JPEG only; vectors, charts, OLE, unusual drawings, masks, inline PDF images,
  unsafe placements, and alternate visual constructs remain unsupported/inventoried.
- Full Office source media replacement affects every reuse, including cropped or hidden
  portions; surrounding document geometry is preserved. Flattening alpha may introduce
  white within a formerly transparent image. EXIF orientation is baked into replacement.
- DOCX logical locations are not physical Word pages. Package previews have package labels.
- Legacy saved audits are not automatically reinspected or retroactively cleared.
- Manual missed-face region annotation is not implemented; existing text MISSED_PII remains.
- Text inside photos/media is not comprehensively OCR-covered by this phase. Existing
  residual text/property/annotation risks and unsupported inventory remain visible.
- Missing model/inference errors stop processing; unknown media blocks visual verification.
  A partially generated private artifact is never presented as verified biometric protection.
- Multiple large validation processes compete for host memory. Run full regression and
  Chromium acceptance sequentially on this workstation.

## R. Completion Status

Supported synthetic PDF, DOCX, and PPTX demonstrate local detection, traceability,
original preservation, actual strong blur, continued text redaction, reopen checks,
independent serialized transformation proof, and existing UI/audit integration.
Complete privacy coverage and downstream clearance remain explicitly unverified.
Phase 11 supported-format integration is complete with the passing checks in section P.
Real Cadence artifacts still require review and contain unresolved/unsupported content;
they are private review artifacts, not cleared downstream inputs.

| Assessment | Conclusion |
|---|---|
| Technical integration | Verified on supported synthetic PDF/DOCX/PPTX paths, including text plus face transformations |
| Detection accuracy | Synthetic functional checks pass; real candidate correctness is unadjudicated, no precision/recall claim |
| Verified PII coverage | Not established for text or visual content |
| Downstream LLM readiness | Blocked; all clearance flags remain false |
