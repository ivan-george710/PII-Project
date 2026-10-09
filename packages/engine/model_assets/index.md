# packages/engine/model_assets

Model manifests, licenses, acquisition instructions, and configuration. Downloaded model weights belong outside Git.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `manifest.json` | Planned | Model identifiers, versions, licenses, checksums, and download locations. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |
| `README.md` | Planned | Acquisition/cache instructions; model weights remain outside Git. Owner: [issue 1](../../../docs/issues/01-privacy-engine.md). |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](../../../docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/ivan-george710/PII-Project/issues/1)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
