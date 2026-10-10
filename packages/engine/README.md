# PII Guard engine

The production package currently provides validated contracts, content inspection,
native document extraction, OCR, built-in text detection, custom rules, policy
evaluation, permanent text/image/supported-PDF/DOCX/PPTX redaction, conservative
metadata sanitization and independent internal output verification. The public
sanitize pipeline is not implemented.

## Setup and verification

From `packages/engine/`, use Python 3.11 or newer:

```powershell
python -m pip install -e ".[test]"
python -m pytest
python -m compileall src
```

Real OCR is optional. Ordinary tests use injected providers and never initialize
OCR models. To verify recognition of the checked-in synthetic `scan.png`:

```powershell
python -m pip install -e ".[test,ocr]"
$env:PII_GUARD_REAL_OCR = "1"
python -m pytest tests/test_ocr.py -m integration -v
```

RapidOCR 1.2.3 includes its default ONNX weights in the installed distribution;
the test uses these local models and performs no model download. Model accuracy
depends on content: this single-word test does not establish coverage or language
support. The fixture generator requires local Arial; test execution does not.

## Extraction and locations

Call `extract_pdf`, `extract_docx`, `extract_pptx` or `extract_image` from
`pii_guard.extraction` with a trusted source path, artifact UUID, basename and
an OCR provider (`RapidOCREngine` from `pii_guard.ocr` for real recognition).
No public request/result fields from Issue 1 have changed.

- Native PDF text is page-local. OCR-required pages are rendered at 144 DPI,
  including mixed pages, inline images, forms, vector outlines and annotations.
  Full-page OCR is used even when embedded image bytes are available so clipping,
  placement and rotation are preserved. Native and OCR text can duplicate visible
  text on mixed pages; they remain distinct source blocks.
- PDF OCR boxes are normalized against the displayed crop box after page rotation,
  with top-left origin. `pdf:page:N:rendered:ocr:K` identifies this coordinate
  frame. Re-rendering the same original page reconstructs the transform; callers
  must account for its crop box and rotation before using raw PDF user coordinates.
- DOCX text includes nested tables, text boxes and reachable Word XML parts
  (headers, footers, comments, footnotes/endnotes). Images retain their owning part
  and relationship ID. DOCX has no reliable page layout without a Word renderer:
  page numbers are null and OCR boxes are image-local, identified by `source_ref`.
- PPTX slide/notes text has slide numbers; tables and grouped text are traversed.
  Layout/master and other ancillary text use part-local references with null slide
  numbers. Ordinary picture OCR boxes map to slide coordinates including scaling,
  cropping and rotation. Ancillary part images use image-local coordinates and
  null slide numbers. Grouped, flipped, off-slide and unsupported image-fill
  placements fail explicitly rather than returning misleading coordinates.
- Spans are Unicode codepoint offsets into each block (start zero, end exclusive).
  Internal extraction validation checks artifact identity, method/location kind,
  unique source references, exact spans and OCR coordinates. `full_text` is a
  convenience concatenation, not a coordinate frame for finding offsets.

## Failure safeguards and limitations

Encrypted/malformed/unsupported inputs and required OCR failures raise
`ProcessingError`. No partial extracted artifact is returned. OCR temporary files
are closed before provider access and removed on success or failure. Safe public
messages omit source content; exception causes are private diagnostic information
and must not be logged/serialized to public events.

Demo defaults are 25 MiB per file, 100 PDF pages/PPTX slides. Inspection accepts
size limit overrides; PDF/PPTX extractors accept page/slide overrides. OpenXML
expanded bytes are limited to 100 MiB (configurable during inspection) to prevent
small compressed inputs allocating unbounded memory. PDF rendering rejects pages
exceeding 4096 pixels on either axis at 144 DPI (`max_render_edge` override),
rather than silently reducing resolution. Pillow's decompression-bomb safeguard
also applies. Multi-frame images and external Office images/embedded package
objects fail explicitly. These are bounds, not a total CPU/memory/time guarantee.

OCR can miss or misrecognize text. Native PDF text with unusual fonts can have
unreliable character mappings. PDF rendering only inspects visible content; hidden
payloads and metadata require the sanitizing writers described below; extraction
alone does not sanitize them. Office extraction enumerates reachable parts, not arbitrary orphan ZIP
members. DOCX lacks page geometry and arbitrary Office drawing rendering remains
unsupported. No face processing or public `sanitize()` is provided here.
The internal verification layer below checks supported outputs. Supported image/PDF redaction
and its explicit unsupported-structure checks are described below.

Issue 1 does not specify the crop/rotation frame of normalized PDF coordinates,
DOCX pagination/rendering, or which unsupported Office drawings must render versus
fail. The above conventions preserve the existing nullable-location contract;
expanded-package/render bounds are defensive limits demonstrated in tests.

## Built-in text detection

Presidio Analyzer (MIT) and its existing spaCy/phonenumbers dependencies provide
the production text detectors. Install the local English spaCy model explicitly:

```powershell
python -m spacy download en_core_web_sm
python -m pytest tests/test_detection.py -m presidio -v
```

For spaCy 3.8, use `en_core_web_sm` 3.8.0 (MIT, published by Explosion). If GitHub
release downloads are unavailable, the same model is available from conda-forge:

```powershell
conda install -y --no-deps --override-channels -c conda-forge https://conda.anaconda.org/conda-forge/noarch/spacy-model-en_core_web_sm-3.8.0-pyhd8ed1ab_0.conda
```

Model weights remain outside Git. Detection never downloads a model at runtime;
missing dependencies, missing recognizers, NLP models without NER, or detector
failures raise safe `ProcessingError(EXTRACTION_FAILED)` with submission/artifact
IDs where available. Issue 1 has no text-detection-specific error code; its public
enum is unchanged. The named model is configurable; English is currently the
only configured language. Model selection and language expansion require new
coverage tests, not just a different score threshold.

```python
from pii_guard import DetectionConfig, TextDetector

detector = TextDetector(DetectionConfig())
batch = detector.detect(text="Employee EMP-12345", blocks=extracted.blocks)
# batch.accepted and batch.rejected are private processing data, not events.
```

`extracted` is an `ExtractedArtifact` produced by one of the extraction functions.
Use `detect_message(text)` or `detect_block(block)` for individual content units.
No policy argument or enable-state filtering exists: all 12 built-in text rules
run for every content unit. FACE detection is not implemented. Custom rules run
separately through the evaluator described below.

| Rule ID | Recognizer |
|---|---|
| PERSON | SpacyRecognizer, trained English NER |
| EMAIL_ADDRESS | EmailRecognizer |
| PHONE_NUMBER | PhoneRecognizer, US-default phonenumbers validation |
| EMPLOYEE_ID | CadenceEmployeeIdRecognizer, uppercase EMP-[0-9]{5} |
| US_SSN | UsSsnRecognizer |
| US_PASSPORT | UsPassportRecognizer |
| US_DRIVER_LICENSE | UsLicenseRecognizer, upstream supported patterns only |
| US_ITIN | UsItinRecognizer |
| US_BANK_NUMBER | UsBankRecognizer |
| IBAN_CODE | IbanRecognizer |
| CREDIT_CARD | CreditCardRecognizer |
| MEDICAL_LICENSE | MedicalLicenseRecognizer, US DEA certificate format/checksum |

Default acceptance thresholds are employee ID 0.90, email/phone 0.70, person
0.75 and government/financial/professional identifiers 0.80. `DetectionConfig`
exposes the complete threshold map. Format checks, token boundaries and Presidio's
checksum/invalidity validators apply before acceptance. Canonical placeholder
SSNs rejected by Presidio remain rejected. Employee IDs require uppercase ASCII
digits; adjacent Unicode word characters, underscores and hyphens are rejected.

Passport, driver-license, bank, ITIN and SSN numbers require a specific nearby
label (up to 80 codepoints before / 40 after the match, in the same content unit).
Format-valid candidates with that evidence receive a configurable heuristic
confidence floor of 0.85 (`context_validated_score`); valid phone numbers can
receive that floor with phone/contact context, but do not require such context if
their original confidence meets the threshold. A zero score is never promoted.
This compensates for Presidio's low base scores for ambiguous numeric patterns.
Original recognizer scores are retained alongside effective confidence. Neither
score is a calibrated probability, and scores are not comparable across entity
types; the heuristic and thresholds do not guarantee coverage. Numeric IDs without
labels can be missed. MEDICAL_LICENSE does not cover arbitrary state/foreign
professional licenses; driver-license validation is not a complete state registry.

No blocks are concatenated, normalized or case-folded. Candidate spans are exact
Unicode codepoint slices of the original message/block, end exclusive. Artifact
identity, page/slide identity, source_ref and the original bbox are preserved.
OCR matches retain the whole OCR-block box, not an invented per-character box;
native PDF matches still have no glyph geometry. Redaction must resolve these
existing source frames later. Repeated text in different source references stays
distinct; cross-block phrases/entities are not detected by joining content.

Presidio's AnalyzerEngine supplies the real NLP engine and recognizer registry.
Recognizer patterns run independently before the usual analyzer containment
pruning: distinct overlapping rules and contained accepted spans survive. Exact
same-rule/same-source/same-span duplicates collapse to the highest score (with a
stable recognizer-name tie break). No redaction-region merging or action assignment
occurs. Matched text is a Pydantic PrivateAttr, omitted from candidate dumps/repr;
rejected candidates remain processing-only. Public Finding fields are unchanged.

Tests without the `presidio` marker use injected provider results or actual
individual recognizers to exercise validation. Tests marked `presidio` use the
actual trained spaCy model, Presidio registry, native PDF extraction and OCR-source
blocks. They skip when the local model is absent; ordinary tests do not download
models. Synthetic examples prove those cases only, not comprehensive PII coverage.

## Custom rules and policy evaluation

`regex` is now a direct dependency because bounded matching uses it; this is the
same library already used by Presidio and the prototype, not a new regex engine.
`CustomRuleEvaluator` matches every rule, including disabled rules, independently
against the original message and each extracted block. Literal rules escape
metacharacters. Unicode full case-insensitive matching operates on the original
string, so even case-fold expansions retain original codepoint offsets. Overlapping
occurrences are retained; phrases are never joined across block boundaries.

Regex syntax currently follows Python's `re` grammar, executed by `regex.VERSION1`.
Regex-only extensions such as recursion, fuzzy matching and Unicode property
escapes are not accepted. A conservative minimum-consumed-width check rejects
patterns that could produce zero-length matches, including conditional zero-width
lookarounds. This can also reject patterns with an impossible zero-width branch.
Inline case flags may not contradict `case_sensitive`. Issue 1 does not specify
a regex dialect or these edge cases; these restrictions are explicit rather than
silently changing flags. The parser is isolated in the worker but uses Python's
private `re._parser` API, so Python upgrades require regression tests.

All custom pattern parsing and compilation run in a killable spawned worker.
Each validation/matching request has a 100ms parent watchdog, and `finditer` also
receives `timeout=0.100`. Timeout raises `PROCESSING_TIMEOUT`; malformed patterns,
empty-matching patterns and excessive matches raise `INVALID_POLICY`. No partial
evaluation is returned. Worker startup has a separate five-second bound; startup,
IPC, scheduling and termination overhead mean total call latency is not a hard
100ms real-time guarantee. Scope standalone evaluators with a context manager to
clean up their worker. Spawned-process examples must use the main guard on Windows.
`validate_custom_rule` exposes the same bounded checks for later save/preview
adapters; those adapters are outside this package phase.

```python
from uuid import uuid4
from pii_guard import CustomRule, PolicyEvaluator, PolicySnapshot, TextDetector
from pii_guard.rules.builtins import BUILTIN_RULE_IDS


def main():
    policy = PolicySnapshot(
        organization_id=uuid4(), version=1,
        builtins={rule_id: True for rule_id in BUILTIN_RULE_IDS},
        custom_rules=[CustomRule(
            id=uuid4(), name="Project phrase", kind="exact", pattern="Project [X]",
            case_sensitive=False, enabled=False,
        )],
    )
    text = "EMP-12345 works on Project [X]"
    detected = TextDetector().detect(text=text)
    result = PolicyEvaluator(policy).evaluate(detected.accepted, text=text)
    print(result.model_dump_json())  # Findings only; no matched text or targets.


if __name__ == "__main__":
    main()
```

Pass all accepted detector candidates and all message/blocks for one submission to
one `evaluate` call. The evaluator copies/revalidates the policy once and stores
an immutable serialized snapshot; caller mutations cannot change the run. It is
one-shot to prevent accidental resetting of the submission budget. Standalone
custom callers can share `MatchBudget` across calls. The 10,000-match cap counts
distinct accepted built-in and custom rule/source/span matches, including disabled
matches; genuine duplicates do not consume additional budget. Conflicting geometry
for a duplicate source span fails rather than choosing an arbitrary location.
Repeated extraction blocks must also agree on original text and location, even
when they have no matches. Identical repeated blocks are evaluated once. Candidate
rule/source-kind mismatches fail with `INVALID_POLICY`. Synthetic face candidates
are distinguished by their boxes; this policy support does not implement a face
detector.

Each distinct rule match becomes a `Finding`: enabled matches use `redacted`,
disabled matches use `allowed_disabled`, even when an enabled match overlaps them.
Only enabled events produce internal `RedactionTarget` objects, linked by finding
UUID and original source location. Targets are excluded from result serialization,
contain no matched text, and remain unmerged for the later renderer. Thus enabled
coverage takes precedence without discarding disabled events. These actions plan
later rendering; nothing is actually rewritten or redacted in this phase.
`PolicyEvaluation` retains organization ID and policy version around the events.
Existing built-in confidence/category/recognizer fields are preserved. Custom
matches use category `custom`, confidence `1.0` (deterministic pattern match, not a
PII probability), and `CustomExactRecognizer`/`CustomRegexRecognizer`; Issue 1 does
not prescribe custom category names or confidence values. Raw matched text remains
private processing memory, never public findings or error messages.

Real bounded-regex integration tests and the optional real component checks:

```powershell
python -m pytest tests/test_rules.py -m integration -v
$env:PII_GUARD_REAL_OCR = "1"
python -m pytest
```

The rule suite separately tests a mocked watchdog wait and an injected regex call
to verify timeout wiring; the integration-marked tests execute actual adversarial
regexes in spawned workers. No face detector, renderer, output verification or
public `sanitize()` implementation is supplied by policy evaluation.

## Text redaction

`pii_guard.redaction.redact_text(original_text, enabled_targets)` renders one
message. Pass `PolicyEvaluation.redaction_targets`, not its public findings.
Disabled findings produce no targets, so they cannot cause replacement or reduce
enabled coverage. Public events, their actions and their original locations remain
unchanged. Targets are sorted by original start/end offsets; overlapping, contained,
duplicate and adjacent spans merge into one region, replaced with exactly
`[REDACTED]`. Unrelated Unicode codepoints, whitespace, punctuation and newlines are
copied verbatim. No case folding, normalization or grapheme expansion occurs here.

```python
from pii_guard.redaction import redact_text, redact_block

# evaluation comes from PolicyEvaluator using this same original message.
sanitized_message = redact_text(original_message, evaluation.redaction_targets)

# For an extracted block, supply only targets belonging to that block.
rendered_block = redact_block(original_block, block_targets)
sanitized_block_text = rendered_block.sanitized_text
original_source = rendered_block.original_location
```

These are per-source helpers: a later orchestrator must partition submission targets
by artifact ID, kind, page, slide and source_ref before calling them. Passing a
target from another source fails rather than silently ignoring it. The original
block bbox must also agree, following the current detector/policy convention of
retaining block-level coordinates. Face targets are rejected by this text renderer.

`redact_text` also accepts `source=original_block.location` for artifact text. The
source must cover the entire original text, starting at zero. Every target is
revalidated, must have strict integer offsets, and must satisfy
`0 <= start < end <= len(original_text)`. All targets are checked before output is
created. Malformed sources, spans or target iterators raise a safe
`REDACTION_FAILED` with available submission/artifact context; input values and
underlying exception messages are not logged or included in the error message.
An empty message with no targets returns an empty string.

`redact_block` returns an internal Pydantic `RedactedTextBlock`, with sanitized text,
original location, extraction method and confidence. Its original location describes
the input offset frame, not positions in the shorter or longer rendered string.
It is deliberately not another `ExtractedTextBlock`; inputs and findings are never
rebased or mutated. The result retains no original text. Existing extraction models
do not represent empty text blocks; this phase does not change that contract.

Rendering relies on receiving the same original text used during detection. Source
identity and lengths cannot detect replacement by different text of the same length;
public contracts contain no content fingerprint; private verification evidence
can now bind originals and expected outputs. Reusing original targets on
already rendered text is unsupported. Disabled or undetected content is preserved.
OCR block text can be rendered as a string, but the text helpers do not erase pixels
in its source image. Use the image/PDF helpers below for permanent pixel removal.

## Permanent image and PDF redaction

The `pii_guard.redaction` package also exports `redact_image`, `redact_pdf` and
`redact_pdf_file`. Supply only enabled `PolicyEvaluation.redaction_targets` from
the same original artifact. Findings/actions are never modified. Unknown sources,
bad spans/boxes, unsupported structures and rewrite failures raise safe
`REDACTION_FAILED`; no original document content is included in errors or logs.

`redact_image(original_bytes, targets, artifact_id=..., sources=...)` returns an
internal `ImageRedactionResult`. `sources` are original OCR block locations or
trusted future FACE locations. The source ref must be `image:ocr:<index>` for
standalone OCR or `image` for standalone FACE; `image_ref` can name an embedded
image whose locations are image-local. Page/slide-frame locations are rejected:
their document renderer must explicitly invert its coordinate transform first.
This does not yet implement Office image replacement.

Normalized boxes map to pixels with floor for top/left and ceil for bottom/right,
clipped only for numerical rounding at valid image edges. Painting the exact union
of opaque black rectangles handles duplicate, adjacent and overlapping targets
without enlarging an L-shaped union into an unrelated rectangular area. Fresh
rasters discard original payloads, EXIF thumbnails and other copied metadata.
EXIF orientation is baked into the output. `coordinate_frame="raw"` applies masks
before that transform, matching stored raster dimensions; `"display"` expects
boxes already expressed after EXIF transpose. Callers must use the detector's
actual frame; the current source contract does not record it. PNG preserves
unrelated decoded pixels; JPEG is freshly encoded and incurs recompression.
Optional `output_format="PNG"` produces lossless output from a JPEG and sets
`format_changed=True` plus a safe warning for the later integration layer.
Multi-frame images, unsupported encodings and images over 16,777,216 pixels fail.

PDF rewriting uses `pymupdf>=1.26.7,<1.28`, because the existing `pypdf` extractor
and PDFium renderer do not provide the required content-redaction API.
[PyMuPDF licensing](https://pymupdf.io/licensing) offers AGPL and commercial terms;
deployment must use a compatible license. The existing extraction libraries remain
unchanged. No face detector, Swift code or public pipeline is added.

`redact_pdf(original_bytes, targets, artifact_id=..., blocks=...)` returns complete
rewritten PDF bytes. Original `ExtractedTextBlock` objects bind targets to artifact,
page and source_ref, including exact OCR block bbox and span bounds. Native refs
must be `pdf:page:<n>:native_text`; OCR refs must be
`pdf:page:<n>:rendered:ocr:<index>`. Future FACE locations are supplied separately
as `region_sources`, with ref `pdf:page:<n>:rendered` and a displayed-page bbox.

Native text is re-extracted with pypdf and must exactly match the original block.
Non-whitespace codepoints are aligned in order with actual PyMuPDF character boxes;
any discrepancy, missing glyph or whitespace-only target fails rather than inventing
geometry. Whitespace/newlines inserted by extraction are not treated as glyphs.
OCR/FACE normalized boxes use the rotated cropped page display frame, then the
page's derotation matrix converts them to content coordinates. Native glyph boxes
already use unrotated crop-relative coordinates. Whole OCR block boxes are covered
even when a custom rule matches only part of the recognized text, because the
existing OCR contract has no per-character boxes.
Content redactions are applied temporarily in an unrotated full-media frame,
with translated rectangles; the original crop and rotation are then restored.
This avoids crop-dependent offsets in the library's opaque fill placement.

Every page/target/image placement is validated before mutation. Every embedded
image is decoded and freshly encoded as PNG; target intersections are painted
into its actual source pixels with conservative rounding. Native text and vector
content are genuinely removed by `apply_redactions`, with opaque black coverage;
these are not removable overlays hiding original text/pixels. Pages are not
rasterized. Saving is fresh/nonincremental with cleaning, compression and garbage
collection. Scalar PDF Info, supported document/page XMP and original identifiers
are discarded; unsupported hidden structures are rejected. A PDF remains a
PDF (`format_changed=False`); embedded-image reencoding is not page rasterization.

`redact_pdf_file(original_path, new_output_path, targets, ...)` adds publication and
returns the existing `SanitizedArtifact` contract, including size and SHA-256.
Paths must come from trusted storage/output adapters. It never overwrites the
source or an existing destination. After the whole in-memory rewrite succeeds, a
temporary file is flushed and linked exclusively into place, then cleaned up.
Filesystems without atomic hard-link publication fail explicitly. A later pipeline
must stage all submission artifacts before publishing any of them.

Supported PDFs are deliberately restricted to ordinary visible Base-14 Type1 text,
opaque 8-bit RGB/gray images with supported filters, and ordinary vector drawing.
Reject annotations/widgets, attachments/actions, optional layers, marked content,
Form XObjects, embedded/custom fonts, masks/transparency, unknown resource data,
invisible/shifted text, nonzero media-box origins, rotated/skewed image placements, shared or unused image
resources, content outside the visible crop, repaired/encrypted PDFs, and unknown
catalog/page structures. Standard page rotations and crops with content inside the
visible crop are supported. These restrictions can reject many real PDFs; they
prevent unsafe success while richer object handling remains a future phase.
Native text mapping also rejects differences between extractor reading orders.

Renderers rely on the same original content used during extraction/detection; the
current source contract has no content fingerprint for OCR images. Disabled and
undetected content remains. Tests reopen rewritten PDFs, inspect content streams
and every remaining image object, check visible pixels, and rerun real OCR on
sanitized image/PDF rasters when `PII_GUARD_REAL_OCR=1`. These are focused tests,
not the future production output-verification pipeline. Face detection, Swift
integration and public orchestration remain outside scope.

### Permanent Word and PowerPoint rewriting

`redact_docx(data, targets, artifact_id=..., blocks=...)` and `redact_pptx(...)`
return complete rewritten package bytes. Their `_file` variants accept original
and fresh output paths and return the existing `SanitizedArtifact` contract.
They share PDF publication's exclusive hard-link/temporary-file cleanup behavior;
originals and existing outputs are never overwritten. No public models or findings
are modified. Full submission staging and `sanitize()` remain pending.

Native targets require their original `ExtractedTextBlock`. Artifact, part,
paragraph index, slide/notes ownership, bbox and end-exclusive codepoint bounds
must match. Full native paragraph text is reread from XML and compared exactly.
References follow extraction: `docx:part:/word/document.xml:paragraph:<index>` or
`pptx:part:/ppt/slides/slide<n>.xml:paragraph:<index>`; notes use their own part name
and originating slide number. Paragraph indices count nonempty extraction units,
including table cells; XML text remains in original Unicode without normalization.
Targets cannot span different paragraph units: each paragraph needs its own match.

Overlapping/adjacent enabled spans merge for rendering. Replacement text is placed
in the first affected run; sensitive codepoints are removed from every affected
run, including tabs/line breaks. Unrelated run text and formatting are retained;
empty runs may remain as formatting containers. `[REDACTED]` inherits the first
text run's formatting; a replacement starting at a DrawingML line break receives
an ordinary new run. Disabled events remain public and contribute no targets.

Word pictures use `docx:part:<part>:image:<relationship_id>:ocr:<index>` and
image-local boxes. PowerPoint uses
`pptx:slide:<n>:shape:<id>:image:ocr:<index>` and slide-normalized boxes. Uncropped,
unrotated picture placements are inverted by translation and scale before using
the existing image renderer. The entire accepted OCR block region is blackened,
because extraction has no character-level geometry. Shared media receives the
union of enabled regions from every occurrence, then replaces the original media
part once. Consequently, other occurrences of the same image also receive those
redactions, including disabled occurrences. Placement, dimensions and relationships
are preserved; images retain PNG/JPEG encoding (JPEG is recompressed).

Every image is freshly encoded, without old thumbnails/EXIF payloads; nontrivial
Office-image EXIF orientation is rejected to preserve placement geometry. OCR
text/boxes are trusted extraction inputs: the current contract does not fingerprint
original image bytes, so callers must retain the same original through processing.
Unknown sources and mutated native text fail with safe `REDACTION_FAILED` errors.
Office FACE targets currently fail explicitly; binding future face sources to
Office image occurrences belongs to the detector integration, not this phase.

Support is deliberately conservative: ordinary Word paragraphs/tables/inline
pictures and ordinary PowerPoint text shapes, notes and PNG/JPEG pictures on the
installed libraries' stock templates. Ancillary parts (styles, settings, masters,
layouts, themes and the empty stock bibliography) must match pristine template
bytes. Document properties, previews, printer settings and shape descriptions are
removed independently of rule enable states. Headers/footers, comments, revisions, fields,
custom XML, embedded objects/macros, external relationships, grouped shapes,
charts/tables in PowerPoint, floating Word images, cropped/rotated/flipped pictures,
hidden/off-slide content, unplaced media and unknown package content fail closed.
Even all-off/no-target rendering performs these checks. Many real Office files
will therefore be rejected until richer supported structures are implemented.
Unknown ancillary content fails closed; documents/slides are not rasterized.

The private shared `redaction/office.py` implements bounded ZIP inspection (25 MiB
input, 100 MiB expanded, 2,000 entries), fresh deterministic ZIP encoding, strict
XML/relationship checks and reusable run/media publication. `lxml>=4.9` is now a
direct dependency because the renderer uses parent-aware XML editing and an
explicit [XML parser](https://lxml.de/api/lxml.etree.XMLParser-class.html) with entity
resolution/network access disabled. It was already installed through the Office
libraries. DTDs, XML comments/processing instructions, duplicate ZIP entries,
archive comments/trailing payloads and unknown XML features are rejected.

Tests create real synthetic packages, reopen them with standard Office libraries,
inspect XML/media for known leaks, verify unrelated formatting/pixels and shared
placements, and exercise safe failures and cleanup. With `PII_GUARD_REAL_OCR=1`,
Office media is recognized before rewriting and rerecognized afterward. These
checks validate this component; the independent verifier below adds read-back checks.

### Metadata and hidden-content handling

Private `redaction/metadata.py` uses four classifications: supported and sanitized,
safe structural content, stripped, or unsupported (fail closed). Metadata removal
is unconditional, including when every detection rule is disabled. It does not
alter public finding events or their original locations. Fixed warning categories
contain no original values, filenames or URLs. Images expose these through their
existing internal result; the private Office/PDF reports are available for future
pipeline aggregation, without changing the current bytes/artifact APIs.

| Format | Removed or sanitized | Rejected ancillary content |
|---|---|---|
| PNG/JPEG | Fresh pixel encoding removes EXIF, XMP, ICC, textual chunks, comments and previews; EXIF orientation is baked into pixels; RGB beneath zero alpha is cleared. Encoded PNG chunks/JPEG segments are checked. | Existing multi-frame/unsupported raster and geometry restrictions remain. |
| PDF | Scalar Info properties, document/page XMP, original trailer identifiers and obsolete unreachable objects are removed by a fresh garbage-collected save. Output is reopened with both PDF libraries. | Annotations/widgets, attachments, JavaScript/actions, layers/forms, hidden or alternate content and unsupported objects/resources. |
| DOCX | Core/app/custom properties and previews, with their relationships/content-type overrides; picture names and descriptions; freshly encoded media. | Comments, revisions, headers/footers, footnotes/endnotes, document variables, fields, custom XML beyond pristine empty stock bibliography, OLE/packages, macros, external links, hidden text and alternate content. |
| PPTX | Core/app/custom properties, previews and unreferenced printer data, with package references; shape names/descriptions; freshly encoded media. Ordinary speaker-note text remains source-bound and redacted by enabled targets. | Comments/authors, unsupported notes structures, hidden slides, custom XML, embedded objects/macros, external relationships, alternate content, transitions/actions/links and unknown parts. |

Only recognized metadata parts are deleted. Their original XML, relationships and
content types are validated before editing; references from rendered content fail
rather than being broken. Stable shape IDs and paragraph indices remain unchanged.
Styles/settings/fonts/numbering/layouts/masters/themes are accepted only when
byte-identical to the installed libraries' pristine templates. Tests classify
every retained template part and reject its mutation; this is a narrow structural
allowlist, not support for arbitrary user-edited ancillary XML.

Supported PDF XMP is well-formed XML in an unfiltered or singly Flate-compressed
metadata stream, limited to 1 MiB after decoding. DTDs, unsupported filters,
malformed properties and metadata-owned payloads fail with safe `REDACTION_FAILED`
errors. Catalog version/layout/mode fields must be valid structural names, and
optional font names must agree with their resource name; private payloads in those
fields are rejected. The reopened output must have no active Info or document/page XMP.

Tests inspect every OOXML ZIP member and relationship, decoded media metadata,
PDF objects and decoded streams for synthetic private markers, then reopen actual
rewritten files. Failure tests check unchanged originals, absent output/temporary
files and safe messages. Publication remains exclusive and atomic; failure to
clean a published temporary file triggers rollback of the newly owned output.
An operating-system refusal to remove files cannot be made recoverable by Python.

These checks cover demonstrated fixtures and supported structures, not arbitrary
steganography or comprehensive PII detection. ICC removal can change color fidelity.
Many real PDFs/Office documents remain unsupported. Submission-wide staging,
warning aggregation and public `sanitize()` remain pending. Original-content
fingerprints are private verification evidence, not new extraction model fields.

## Independent output verification

Internal `pii_guard.verification` exposes `prepare_verification` and
`verify_artifact`, plus `prepare_text_verification`/`verify_text` for message or
block text. Preparation receives the original bytes, artifact UUID, original MIME,
enabled targets and original blocks/region sources. It must run against the trusted
original before rewriting. Optional `output_mime` permits PNG/JPEG conversion;
document conversion is unsupported. It never consumes a writer success flag.

```python
from pii_guard.verification import prepare_verification, verify_artifact

evidence = prepare_verification(
    original_path.read_bytes(), artifact_id=artifact_id, mime_type=mime_type,
    targets=evaluation.redaction_targets, blocks=extracted.blocks,
)
# Write into private staging with the appropriate existing renderer.
verify_artifact(
    staged_path, evidence, artifact_id=artifact_id, mime_type=mime_type,
    original_path=original_path,
)
```

Success returns `None`. Any mismatch raises safe `REDACTION_FAILED` without chained
raw validation errors. No verification temporaries are created, originals are
read-only, and failed outputs are not deleted: their staging owner must discard
them. Existing `_file` writers still publish independently; this phase does not
retrofit submission staging or claim those calls invoke verification. A future
pipeline must verify every staged artifact before publishing any and prevent
mutation between verification and publication (or recheck its byte fingerprint).

Evidence is a Pydantic internal object with only private state; dumps, nested dumps
and repr contain no fingerprints, original text or file bytes. SHA-256 fingerprints
bind text to artifact/kind/page/slide/source/bbox identity and original offsets.
Whole expected text units detect both surviving PII and unintended text changes,
while allowing duplicate sensitive values in other valid, untargeted units. Pixel
evidence is distinct: original region hashes, dimensions, placements and expected
opaque regions. The original file SHA-256 is rechecked when `original_path` is
supplied. Hashes are private evidence, not anonymization; the trusted pipeline must
capture/bind the original before extraction and retain that binding throughout.

| Output | Independent read-back checks |
|---|---|
| Message/block text | Separate coverage-event sweep determines expected `[REDACTED]` replacements; complete source-bound expected digest and original source identity must match. |
| PNG/JPEG | Pillow decoding, dimensions/orientation, actual opaque black coverage, metadata-free encoded structures and no RGB beneath zero alpha. JPEG permits boundary ringing up to channel value 64, but fully covered 8x8 interiors must be exactly black; regions without such an interior fail closed. |
| PDF | pypdf extraction and serialized-object policy; MuPDF reopening, unchanged pages/crop/rotation, removed native glyph content, rendered black coverage and decoded underlying image pixels. Forbidden objects/metadata, unused image resources and unreachable obsolete objects are rejected. Only a separately generated, byte-identical library RGB ICC profile is accepted. |
| DOCX/PPTX | Standard-library XML paragraph/table/shape/notes rereading, expected unit digests, unchanged native inventory, serialized picture mappings, decoded media coverage, metadata absence, fixed ancillary/relationship fingerprints and standard Office-library reopening. Shared media is checked once with the union of enabled regions. |

The verifier never calls any redactor. Text expectation, paragraph inventory and
serialized picture coordinates are independent implementations. Strict ZIP/XML/
relationship/feature guards and encoded-image metadata policy are deliberately
shared to keep supported-structure rules consistent. PDF glyph geometry and page
rendering necessarily reuse MuPDF, alongside independent pypdf text/object checks;
Office reopening uses the same standard libraries as writing, alongside separate
XML and fingerprint checks. A shared parser/library defect remains a limitation.

Optional `verification_markers` capture only SHA-256 and lengths of known synthetic
fixture values, then scan written bytes, OOXML members and decoded PDF objects/
streams. They do not assert global absence for ordinary target values. Marker scans
are bounded to two million windows; up to 16 markers of 4..512 bytes are accepted.
Original inputs remain limited to 25 MiB, outputs to 100 MiB, blocks to one million
codepoints, PDF streams to 64 MiB decoded/100 MiB aggregate, and coverage renders
to 4096 pixels per edge at 144 DPI. Exceeding verification bounds fails closed.

`tests/test_verification.py` verifies actual files and deliberately reinserts text,
notes, original media, metadata, hidden parts, actions/attachments and obsolete PDF
objects. Tests also exercise visible overlays over unchanged source pixels, MIME/
identity failures, Unicode/overlaps/duplicates, orientation, all-off handling,
private serialization, original-file mutation and independence from redactors.
These checks establish required redaction behavior for the supported subset, not
comprehensive PII discovery, arbitrary steganography detection or Office layout
rendering. OCR/face detector integration and submission orchestration remain separate.
