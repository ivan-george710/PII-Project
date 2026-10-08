# packages/engine/model_assets

Model manifests, licenses, acquisition instructions, and configuration. Downloaded model weights belong outside Git.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `manifest.json` | Planned | Model identifiers, versions, licenses, checksums, and download locations. |
| `README.md` | Planned | Acquisition/cache instructions; model weights remain outside Git. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
