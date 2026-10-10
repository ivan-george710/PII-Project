# packages/engine/tests

Engine tests covering extraction, OCR, text and face detection, company/custom rules, redaction, and the complete engine pipeline.

Implemented extraction checks include PDF rendering/rotation/crop fallback,
ancillary Office text/images, safe failures, resource bounds and cleanup. Ordinary
OCR tests use injected providers; the integration marker plus PII_GUARD_REAL_OCR=1
enables local RapidOCR recognition of fixtures/scan.png.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `conftest.py` | Existing | Shared engine fixtures and helper configuration. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_inspection.py` | Existing | MIME validation and mixed-content classification. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_extraction.py` | Existing | Native and embedded content extraction in every format. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_ocr.py` | Existing | Scan recognition and coordinate mapping. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_detection.py` | Existing | Every text rule's positive/negative examples, thresholds, offsets, overlaps, private serialization and failure behavior; real Presidio/spaCy integration uses the presidio marker. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_faces.py` | Planned | Portrait/group/crop detection, duplicate suppression, and mapping. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_rules.py` | Existing | Contract validation, literal/regex offsets, deterministic and real timeout checks, submission limits, immutable policy, overlaps, disabled events, source preservation, conflicting sources/geometry, rule/source-kind validation and safe serialization. Real bounded-regex tests use the integration marker; mocked late replies and partial timeout results are tested separately. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_redaction.py` | Existing | Text/provenance and Presidio integration; actual raster/PDF/Word/PowerPoint rewrites, decoded pixel/XML leak checks, split runs, tables, notes, shared pictures, overlaps, disabled events, strict source/package failures and publication cleanup. Opt-in real OCR rerecognizes sanitized image/PDF/Office media. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_pipeline.py` | Planned | Complete standalone engine processing and failure behavior. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_metadata.py` | Existing | Actual raster/PDF/Office metadata stripping, ZIP/object/stream leak-marker searches, reopening, hidden-content and malformed-payload rejection, template classification, all-off event preservation and publication cleanup. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `test_verification.py` | Existing | Actual output verification and deliberate text/pixel/metadata/relationship/notes/hidden-content regressions, source identity and original fingerprints, safe failures, duplicate values, private evidence and independence from redactors. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |

## Subdirectories

- [fixtures/](fixtures/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](../../../docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/ivan-george710/PII-Project/issues/1)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
