# packages/engine

Independent Python privacy engine. Accept content plus company policy; return sanitized text/files and detection/action events. No user authentication or database ownership belongs here.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `pyproject.toml` | Planned | Installable engine dependencies, supported Python version, and test configuration. |
| `README.md` | Planned | Standalone usage, supported inputs, policy examples, and limitations. |

## Subdirectories

- [model_assets/](model_assets/index.md): see its exact file manifest.
- [src/](src/index.md): see its exact file manifest.
- [tests/](tests/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
