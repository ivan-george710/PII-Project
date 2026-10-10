# packages/engine/src/pii_guard/detection

Text PII detection, face detection, and candidate validation. Face detection should cover standalone and embedded images, including overlapping crop passes.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Export TextDetector and DetectionConfig. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `text.py` | Existing | Run all built-in Presidio text recognizers and employee IDs per message/block; preserve sources, fail on missing models/components. Custom rules remain pending. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `faces.py` | Planned | Backend-compatible whole-image/crop face detection and duplicate suppression. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |
| `validation.py` | Existing | Private validated candidates/rejections, configurable thresholds, format/context checks and exact deduplication without overlap pruning. Owner: [issue 1](../../../../../docs/issues/01-privacy-engine.md). |

## Subdirectories

- [recognizers/](recognizers/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](../../../../../docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/ivan-george710/PII-Project/issues/1)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
