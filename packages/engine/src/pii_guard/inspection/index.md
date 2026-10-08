# packages/engine/src/pii_guard/inspection

Content-based file detection and PDF page analysis to select processing strategies.

This is a file plan. **Existing** files are present; **Planned** files must be implemented in the owning issue. This documentation does not create application code.

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `index.md` | Existing | Directory file manifest and responsibilities; keep it synchronized with changes. |
| `__init__.py` | Planned | Package marker and relevant public exports. |
| `file_type.py` | Planned | Detect real file format and reject unsupported inputs. |
| `pdf_analysis.py` | Planned | Classify native text, scans, mixed content, and blank PDF pages. |

Generated caches, dependencies, runtime uploads, and `.git/` are excluded from directory manifests.
