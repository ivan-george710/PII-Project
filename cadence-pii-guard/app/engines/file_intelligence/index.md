# cadence-pii-guard/app/engines/file_intelligence

Existing MIME detection and PDF analysis; reference for the new inspection module.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Existing | Prototype package exports/marker. |
| `detector.py` | Existing | Content-based MIME detection. |
| `engine.py` | Existing | Prototype engine implementation or empty placeholder; see current source. |
| `models.py` | Existing | Prototype data contracts; audit models are currently empty. |
| `pdf_analyzer.py` | Existing | PDF page analysis and extraction strategy selection. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
