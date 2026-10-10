# packages/engine/src/pii_guard

Inspection, extraction, OCR, detection, rules, redaction, and audit events. models.py defines engine contracts; pipeline.py provides the main sanitization entry point.

Internal extraction models validate block-local Unicode spans, artifact identity,
source-reference uniqueness and OCR coordinates. Public Issue 1 model fields remain
unchanged; extraction frame conventions are documented in ../../README.md.
Public exports include TextDetector, DetectionConfig, CustomRuleEvaluator,
validate_custom_rule and PolicyEvaluator. Detection returns private candidates
without actions; policy evaluation creates findings and internal enabled targets.
The redaction package renders message/block text from enabled policy targets,
preserving original source references and findings; invalid targets/sources use
REDACTION_FAILED. Image/PDF redaction now permanently rewrites supported rasters
and PDF content, with strict source/structure checks and no whole-page rasterization.
Office rewriting supports ordinary Word paragraphs/tables/inline pictures and
PowerPoint shapes/notes/untransformed pictures, with strict stock ancillary checks.
Shared metadata classification removes supported properties/previews and fails
closed for unsupported hidden structures; images and PDFs are freshly encoded.
Face detection and the sanitize pipeline remain pending.
The internal verification package captures private original/source fingerprints
and independently rereads output text, pixels, packages and PDF objects before
future staging publication; it returns no public success payload.
Missing text components use the
existing EXTRACTION_FAILED code. Invalid rules/policies and custom execution
timeouts use INVALID_POLICY and PROCESSING_TIMEOUT respectively.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Public engine exports. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |
| `models.py` | Existing | Input/output, source locations, findings/actions, policy, and artifact contracts. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |
| `pipeline.py` | Planned | Complete inspection-to-sanitization workflow accepting supplied company policy. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |
| `errors.py` | Existing | Explicit processing, unsupported-content, and policy errors. Owner: [issue 1](../../../../docs/issues/01-privacy-engine.md). |

## Subdirectories

- [audit/](audit/index.md): see its exact file manifest.
- [detection/](detection/index.md): see its exact file manifest.
- [extraction/](extraction/index.md): see its exact file manifest.
- [inspection/](inspection/index.md): see its exact file manifest.
- [ocr/](ocr/index.md): see its exact file manifest.
- [redaction/](redaction/index.md): see its exact file manifest.
- [rules/](rules/index.md): see its exact file manifest.
- [verification/](verification/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Runtime validation

Use Pydantic v2 BaseModel contracts with forbidden extra fields, strict booleans/integers, constrained values, and explicit boundary validation. Follow the exact models/API shapes in docs/issues. Python types and dataclasses alone do not validate external inputs.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](../../../../docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/ivan-george710/PII-Project/issues/1)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.

## PR 18 integration

`pipeline.py` implements staged inspect/extract/detect/evaluate/redact/verify/publish with all-or-nothing artifact output. `model_assets/` holds the checksum-pinned YuNet model and license. The pipeline returns internal safe artifact text for the chat adapter; it is excluded from serialization.
