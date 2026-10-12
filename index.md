# PII Guard repository

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `.gitignore` | Existing | Existing project asset or configuration; preserve its behavior unless explicitly changed. |
| `DESIGN.md` | Existing | Approved interface theme and interaction rules. |
| `PRODUCT.md` | Existing | Current confirmed product requirements. |
| `README.md` | Existing | Engine behavior, setup and supported limits. |
| `createfile.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `requirements.txt` | Existing | Existing project asset or configuration; preserve its behavior unless explicitly changed. |
| `run.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `scratch_docling.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `scratch_extraction.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `scratch_hybrid.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `scratch_ocr_pdf.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `scratch_paddle.py` | Existing | Existing application module; preserve its behavior unless explicitly changed. |

Subdirectories contain their own manifests when touched. Engine implementation and phase evidence remain authoritative.

| `vercel.json` | Implemented | Same-origin manager-only frontend/API service deployment configuration for hosted demo. |
| `.vercelignore` | Implemented | Exclude local engines, employee files, credentials and test/runtime artifacts from hosted upload. |
| `.github/workflows/test.yml` | Implemented | Continuous integration running pytest, frontend vitest, both Vite builds, and manager service isolation. |
| `requirements-local.txt` | Implemented | Mac/Linux local runtime dependencies, excluding Windows-only packages; verified with pytest suite. |
| `scripts/run-demo.py` | Implemented | Start local engine and separate manager UI; open both; safely stop owned child processes. |
| `scripts/setup-local.sh` | Implemented | Install system/Python/frontend dependencies and default spaCy model. |

