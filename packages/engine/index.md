# packages/engine

Independent Python privacy engine. Accept content plus company policy; return sanitized text/files and detection/action events. No user authentication or database ownership belongs here.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `pyproject.toml` | Planned | Installable engine dependencies, supported Python version, and test configuration. Owner: [issue 1](../../docs/issues/01-privacy-engine.md). |
| `README.md` | Planned | Standalone usage, supported inputs, policy examples, and limitations. Owner: [issue 1](../../docs/issues/01-privacy-engine.md). |

## Subdirectories

- [model_assets/](model_assets/index.md): see its exact file manifest.
- [src/](src/index.md): see its exact file manifest.
- [tests/](tests/index.md): see its exact file manifest.

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.

## Approved issue scope

- [Issue 1: Build the complete document and image privacy engine](../../docs/issues/01-privacy-engine.md) — [GitHub #1](https://github.com/ivan-george710/PII-Project/issues/1)

Each issue includes its own tests and sample/setup helpers. Implement the listed files; deferred entries are outside the approved scope.
